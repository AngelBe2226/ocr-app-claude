import calendar
import random
from datetime import date

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.constants import PROFILE_IDS, PROFILES
from app.finance import hash_color, last_n_months
from app.models import (
    Account, Bill, Budget, Category, Goal, Loan, Profile, Settings, Subcategory, Transaction, User,
)

DEFAULT_EMAIL = "angelgbct@gmail.com"
DEFAULT_PASSWORD = "finanzas123"


# Tasas de ahorro/impuestos por defecto por perfil (savings_rate, tax_rate) en %.
# Meliá (ingreso fijo, impuestos ya retenidos): 30% ahorro. Real Estate: 25% impuestos
# anuales (IRPF/SS) + 15% ahorro = 40%. El resto: 40% ahorro.
SAVINGS_DEFAULTS = {
    "melia": (30.0, 0.0),
    "realestate": (15.0, 25.0),
}


def _rates_for(slug: str) -> tuple[float, float]:
    return SAVINGS_DEFAULTS.get(slug, (40.0, 0.0))


def ensure_profiles(db: Session) -> None:
    """Migración idempotente: crea los 4 perfiles por defecto en BD (a partir de las
    constantes) para cualquier usuario que aún no los tenga. Los slugs coinciden con
    los que ya usan las transacciones/categorías, así que el histórico sigue coherente."""
    for user in db.query(User).all():
        if db.query(Profile).filter(Profile.user_id == user.id).first():
            continue
        for pos, pid in enumerate(PROFILE_IDS):
            conf = PROFILES[pid]
            sr, tr = _rates_for(pid)
            db.add(Profile(user_id=user.id, slug=pid, name=conf["name"], color=conf["color"],
                           position=pos, savings_rate=sr, tax_rate=tr))
    db.commit()


GLOBAL_SAVINGS_NAME = "Ahorro Global"


def get_or_create_global_savings(db: Session, user_id: int) -> Account:
    """Cuenta única donde se acumulan las reservas de ahorro de todos los perfiles."""
    acc = (db.query(Account)
           .filter(Account.user_id == user_id, Account.name == GLOBAL_SAVINGS_NAME).first())
    if not acc:
        acc = Account(user_id=user_id, name=GLOBAL_SAVINGS_NAME, type="savings",
                      currency="EUR", balance=0, color="#3FA65C", icon="piggy-bank")
        db.add(acc)
        db.flush()
    return acc


def ensure_global_savings_account(db: Session) -> None:
    for u in db.query(User).all():
        get_or_create_global_savings(db, u.id)
    db.commit()


def ensure_savings_defaults(db: Session) -> None:
    """Backfill: aplica las tasas de ahorro/impuestos sugeridas a perfiles que siguen
    con los valores por defecto de columna (40/0), sin pisar ajustes ya personalizados."""
    changed = False
    for p in db.query(Profile).all():
        sr, tr = _rates_for(p.slug)
        if (sr, tr) != (40.0, 0.0) and abs((p.savings_rate or 0) - 40.0) < 1e-9 and abs((p.tax_rate or 0)) < 1e-9:
            p.savings_rate, p.tax_rate = sr, tr
            changed = True
    if changed:
        db.commit()


DEFAULT_CATEGORY_ICONS = {
    "transporte": "bus", "comidas": "utensils", "uniforme": "shirt", "otros": "circle",
    "marketing": "megaphone", "gasolina": "fuel", "materiales": "wrench", "comisión colaborador": "users",
    "software/licencias": "laptop", "equipo": "laptop", "subcontratación": "briefcase",
    "compras": "shopping-bag", "ocio": "film", "salud": "heart", "hogar": "home", "suscripciones": "bolt",
    "salario base": "wallet", "horas extra": "wallet", "bono": "gift", "propinas": "cash",
    "comisión venta": "briefcase", "comisión alquiler": "home", "bono de cierre": "gift",
    "proyecto branding": "palette", "proyecto web": "laptop", "ilustración": "palette", "retainer": "briefcase",
    "ingreso extra": "cash", "regalo": "gift", "reembolso": "receipt", "sin categoría": "circle",
}
# Palabras clave para categorías nuevas creadas por el usuario.
ICON_KEYWORDS = [
    ("transp", "bus"), ("comid", "utensils"), ("restaur", "utensils"), ("café", "coffee"), ("gasolin", "fuel"),
    ("combust", "fuel"), ("coche", "car"), ("mercado", "shopping-bag"), ("compra", "shopping-bag"),
    ("ropa", "shirt"), ("ocio", "film"), ("salud", "heart"), ("farmac", "pill"), ("gimnas", "dumbbell"),
    ("hogar", "home"), ("alquil", "home"), ("luz", "bolt"), ("suscri", "bolt"), ("stream", "film"),
    ("music", "music"), ("viaje", "plane"), ("regalo", "gift"), ("salari", "wallet"), ("nómina", "wallet"),
    ("nomina", "wallet"), ("software", "laptop"), ("web", "laptop"), ("marketing", "megaphone"),
    ("diseñ", "palette"), ("brand", "palette"), ("educ", "graduation"), ("mascot", "paw"),
]


def icon_for_category(name: str) -> str:
    key = (name or "").strip().lower()
    if key in DEFAULT_CATEGORY_ICONS:
        return DEFAULT_CATEGORY_ICONS[key]
    for kw, ico in ICON_KEYWORDS:
        if kw in key:
            return ico
    return ""


def ensure_category_icons(db: Session) -> None:
    """Backfill: asigna un icono por defecto a las categorías que no tengan ninguno."""
    changed = False
    for c in db.query(Category).filter(Category.icon == "").all():
        ico = icon_for_category(c.name)
        if ico:
            c.icon = ico
            changed = True
    if changed:
        db.commit()


# ── Taxonomía real de categorías (GLOBAL, compartida por todos los perfiles) ──
# Cada entrada: (categoría, icono, [subcategorías]).
EXPENSE_TAXONOMY = [
    ("Finance", "chart", ["Deudas", "FOREX", "STR Rheinmetall", "STR S&P500", "STR NVIDIA", "Vantage", "FundedNext", "Comisiones"]),
    ("Health", "heart", ["Health", "Yoga", "Hospital", "Medicine", "Tea", "Water", "Gym", "Digestivas", "Protein"]),
    ("Education", "graduation", ["Schooling", "Textbooks", "School supplies", "Academy", "Impresión", "Book", "Autoescuela"]),
    ("Leisure", "gamepad", ["Bebidas", "Galletas", "Chocolate", "Dulces", "Confitura", "Café", "Casino", "Entretenimiento", "Tabaco", "Outing", "Gaming", "Energy Drink"]),
    ("Business", "briefcase", ["Taller"]),
    ("Transport", "bus", ["Bus", "Subway", "Taxi", "Car", "Autoescuela", "Flight"]),
    ("Culture", "palette", ["Books", "Movie", "Music", "Apps"]),
    ("Household", "home", ["Appliances", "Furniture", "Kitchen", "Toiletries", "Chandlery", "Bolsa", "Lavandería", "Limpieza"]),
    ("Apparel", "shirt", ["Clothing", "Fashion", "Shoes", "Laundry", "Bags", "Fixing"]),
    ("Beauty", "star", ["Cosmetics", "Makeup", "Accessories", "Beauty", "Bath", "Corte de Pelo"]),
    ("Suscription", "bolt", ["iCloud", "Apple Music", "App buying", "Etsy", "Figma", "Lovable", "GoDaddy", "Claude"]),
    ("Tattoo", "wrench", ["Piel Sintética"]),
    ("Services", "home", ["Renta", "Electricidad", "Teléfono"]),
    ("Social Life", "users", ["Friend", "Fellowship", "Alumni", "Dues", "Tips", "Help", "Recarga", "Outing", "Remesa", "Combo comida"]),
    ("Utilities", "wrench", ["Lavandería", "Limpieza", "Fregado", "Herramientas", "Bolsa", "Electricidad"]),
    ("Food", "utensils", ["Lunch", "Dinner", "Eating out", "Beverages", "Especias", "Eggs", "Embutidos", "Tomate", "Pan", "Vianda", "Cereales", "Frijoles/Lentejas", "Azúcar/sal", "Pimiento", "Frutas", "Yogurt", "Vegetales", "Frutos secos", "Aceite/Vinagre", "Zumo", "Leche", "Spaghetti", "Arroz", "Harina", "Salsas", "Champiñones", "Miel", "Procesados", "Queso", "Aceitunas", "Home", "Snacks"]),
    ("Gift", "gift", []),
    ("Other", "circle", []),
    ("Procedures", "briefcase", []),
    ("Tech", "laptop", []),
    ("Office", "briefcase", []),
]
INCOME_TAXONOMY = [
    ("Freelancer", "laptop", []),
    ("Salary", "wallet", []),
    ("Petty cash", "cash", []),
    ("Bonus", "gift", []),
    ("Other", "circle", []),
    ("Savings", "piggy-bank", []),
    ("Family", "users", []),
    ("Descuentos", "tag", ["Lidl", "SPAR"]),
    ("Reembolso", "receipt", []),
    ("Bingx", "chart", []),
    ("Venta", "shopping-bag", []),
    ("Bolsa", "chart", []),
]


def _seed_taxonomy(db: Session, user_id: int) -> None:
    """Crea la taxonomía global completa (gastos + ingresos) para un usuario."""
    from app.categories import GLOBAL, UNCATEGORIZED_NAME
    for kind, tax in (("expense", EXPENSE_TAXONOMY), ("income", INCOME_TAXONOMY)):
        for pos, (name, icon, subs) in enumerate(tax):
            cat = Category(user_id=user_id, profile=GLOBAL, kind=kind, name=name,
                           icon=icon, color=hash_color(name))
            db.add(cat)
            db.flush()
            for s in subs:
                db.add(Subcategory(category_id=cat.id, name=s, icon=""))
    for kind in ("expense", "income"):
        db.add(Category(user_id=user_id, profile=GLOBAL, kind=kind,
                        name=UNCATEGORIZED_NAME, color="#A39C90", is_system=True))


def ensure_categories(db: Session) -> None:
    """Siembra la taxonomía global para usuarios que aún no tengan categorías."""
    for user in db.query(User).all():
        if db.query(Category).filter(Category.user_id == user.id).first():
            continue
        _seed_taxonomy(db, user.id)
    db.commit()


def migrate_categories_to_global(db: Session) -> None:
    """Convierte el modelo antiguo (categorías por perfil) al nuevo (globales):
    si un usuario tiene categorías pero ninguna global, borra las viejas y siembra
    la taxonomía real. Sus transacciones conservan el nombre de categoría (se resuelve
    icono/color por nombre; si no existe, degrada con color por hash)."""
    from app.categories import GLOBAL
    changed = False
    for user in db.query(User).all():
        has_any = db.query(Category).filter(Category.user_id == user.id).first()
        has_global = (db.query(Category)
                      .filter(Category.user_id == user.id, Category.profile == GLOBAL).first())
        if has_any and not has_global:
            # Borra subcategorías y categorías viejas del usuario.
            old = db.query(Category).filter(Category.user_id == user.id).all()
            for c in old:
                db.query(Subcategory).filter(Subcategory.category_id == c.id).delete(synchronize_session=False)
            db.query(Category).filter(Category.user_id == user.id).delete(synchronize_session=False)
            db.flush()
            _seed_taxonomy(db, user.id)
            changed = True
    if changed:
        db.commit()


def days_in_month(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def gen_transactions() -> list[dict]:
    txs: list[dict] = []
    months = last_n_months(12)
    for m in months:
        y, mo = m.year, m.month
        dim = days_in_month(y, mo)

        txs.append({"profile": "melia", "type": "income", "category": "Salario base",
                    "amount": 1450 + random.randint(-20, 60), "date": date(y, mo, 5), "note": "Nómina mensual", "account_id": 2})
        if random.random() < 0.55:
            txs.append({"profile": "melia", "type": "income", "category": "Horas extra",
                        "amount": random.randint(50, 180), "date": date(y, mo, random.randint(6, 25)), "note": "Turnos extra", "account_id": 2})
        txs.append({"profile": "melia", "type": "expense", "category": "Transporte",
                    "amount": random.randint(35, 60), "date": date(y, mo, 10), "note": "Abono transporte", "account_id": 2})
        if random.random() < 0.3:
            txs.append({"profile": "melia", "type": "expense", "category": "Comidas",
                        "amount": random.randint(15, 35), "date": date(y, mo, random.randint(1, dim)), "note": "Comida turno", "account_id": 1})

        n_sales = random.randint(0, 2)
        for _ in range(n_sales):
            txs.append({"profile": "realestate", "type": "income", "category": "Comisión venta",
                        "amount": random.randint(1400, 3200), "date": date(y, mo, random.randint(1, dim)), "note": "Cierre de venta", "account_id": 2})
        if random.random() < 0.5:
            txs.append({"profile": "realestate", "type": "expense", "category": "Marketing",
                        "amount": random.randint(60, 220), "date": date(y, mo, random.randint(1, dim)), "note": "Anuncios portal", "account_id": 2})
        txs.append({"profile": "realestate", "type": "expense", "category": "Gasolina",
                    "amount": random.randint(45, 95), "date": date(y, mo, random.randint(1, dim)), "note": "Visitas a propiedades", "account_id": 2})

        if random.random() < 0.5:
            txs.append({"profile": "freelance", "type": "income", "category": "Proyecto branding",
                        "amount": random.randint(500, 1600), "date": date(y, mo, random.randint(1, dim)), "note": "Identidad de marca", "account_id": 2})
        if random.random() < 0.4:
            txs.append({"profile": "freelance", "type": "income", "category": "Proyecto web",
                        "amount": random.randint(700, 2200), "date": date(y, mo, random.randint(1, dim)), "note": "Diseño web cliente", "account_id": 2})
        txs.append({"profile": "freelance", "type": "expense", "category": "Software/Licencias",
                    "amount": random.randint(30, 55), "date": date(y, mo, 3), "note": "Suscripciones creativas", "account_id": 2})
        if random.random() < 0.2:
            txs.append({"profile": "freelance", "type": "expense", "category": "Equipo",
                        "amount": random.randint(80, 400), "date": date(y, mo, random.randint(1, dim)), "note": "Material/equipo", "account_id": 2})

        if random.random() < 0.5:
            txs.append({"profile": "personal", "type": "expense", "category": "Compras",
                        "amount": random.randint(40, 180), "date": date(y, mo, random.randint(1, dim)), "note": "Compras varias", "account_id": 1})
        if random.random() < 0.4:
            txs.append({"profile": "personal", "type": "expense", "category": "Ocio",
                        "amount": random.randint(20, 90), "date": date(y, mo, random.randint(1, dim)), "note": "Salidas", "account_id": 1})
        txs.append({"profile": "personal", "type": "expense", "category": "Suscripciones",
                    "amount": random.randint(15, 25), "date": date(y, mo, 18), "note": "Streaming", "account_id": 2})
        if random.random() < 0.15:
            txs.append({"profile": "personal", "type": "income", "category": "Regalo",
                        "amount": random.randint(50, 150), "date": date(y, mo, random.randint(1, dim)), "note": "Regalo familiar", "account_id": 1})
    return txs


def add_months(d: date, delta: int) -> date:
    y = d.year + (d.month - 1 + delta) // 12
    m = (d.month - 1 + delta) % 12 + 1
    return date(y, m, min(d.day, days_in_month(y, m)))


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return

    user = User(email=DEFAULT_EMAIL, password_hash=bcrypt.hash(DEFAULT_PASSWORD))
    db.add(user)
    db.flush()

    db.add(Settings(user_id=user.id, theme="light", accent_key="teal"))

    accounts = [
        Account(user_id=user.id, name="Efectivo", type="cash", currency="EUR", balance=180, color="#7A756C"),
        Account(user_id=user.id, name="Cuenta corriente", type="bank", currency="EUR", balance=3200, color="#12898F"),
        Account(user_id=user.id, name="Cuenta ahorro", type="savings", currency="EUR", balance=9800, color="#3FA65C"),
        Account(user_id=user.id, name="PayPal", type="bank", currency="USD", balance=220, color="#4A79D9"),
        Account(user_id=user.id, name="Tarjeta Visa", type="card", currency="EUR", balance=-450, color="#C2555B",
                 cycle_end=date.today().replace(day=min(28, days_in_month(date.today().year, date.today().month))),
                 due_date=add_months(date.today().replace(day=10), 1)),
    ]
    db.add_all(accounts)
    db.flush()

    today = date.today()
    loans = [
        Loan(user_id=user.id, name="Préstamo coche", principal=12000, balance=7180, rate=6.5, payment=245),
        Loan(user_id=user.id, name="Tarjeta de crédito", principal=3000, balance=2850, rate=24, payment=50),
        Loan(user_id=user.id, name="Préstamo personal", principal=5000, balance=3100, rate=9.9, payment=180),
    ]
    db.add_all(loans)

    bills = [
        Bill(user_id=user.id, name="Alquiler", amount=650, due_day=1, paid=650),
        Bill(user_id=user.id, name="Internet y móvil", amount=45, due_day=5, paid=45),
        Bill(user_id=user.id, name="Seguro coche", amount=38, due_day=12, paid=0),
        Bill(user_id=user.id, name="Streaming", amount=19, due_day=18, paid=0),
    ]
    db.add_all(bills)

    goals = [
        Goal(user_id=user.id, name="Traer a mi pareja a España", target=3000, current=1200,
             target_date=date(today.year + 1, 3, 1), color="#12898F"),
        Goal(user_id=user.id, name="Fondo de emergencia", target=6000, current=4100,
             target_date=date(today.year, 12, 1), color="#3FA65C"),
        Goal(user_id=user.id, name="Vacaciones juntos", target=1200, current=300,
             target_date=date(today.year, 11, 1), color="#D9932E"),
    ]
    db.add_all(goals)

    budgets_def = {
        "melia": [("Transporte", 60), ("Comidas", 80), ("Uniforme", 40), ("Otros", 30)],
        "realestate": [("Marketing", 200), ("Gasolina", 90), ("Materiales", 60), ("Comisión colaborador", 150)],
        "freelance": [("Software/Licencias", 60), ("Equipo", 100), ("Marketing", 80), ("Subcontratación", 150)],
        "personal": [("Compras", 250), ("Ocio", 150), ("Salud", 80), ("Hogar", 120), ("Suscripciones", 45)],
    }
    for profile, cats in budgets_def.items():
        for cat, allocated in cats:
            db.add(Budget(user_id=user.id, profile=profile, category=cat, allocated=allocated, rollover=False))

    for tx in gen_transactions():
        db.add(Transaction(user_id=user.id, **tx))

    db.commit()
