import calendar
import random
from datetime import date

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.constants import PROFILE_IDS, PROFILES
from app.finance import hash_color, last_n_months
from app.models import Account, Bill, Budget, Category, Goal, Loan, Profile, Settings, Transaction, User

DEFAULT_EMAIL = "angelgbct@gmail.com"
DEFAULT_PASSWORD = "finanzas123"


def ensure_profiles(db: Session) -> None:
    """Migración idempotente: crea los 4 perfiles por defecto en BD (a partir de las
    constantes) para cualquier usuario que aún no los tenga. Los slugs coinciden con
    los que ya usan las transacciones/categorías, así que el histórico sigue coherente."""
    for user in db.query(User).all():
        if db.query(Profile).filter(Profile.user_id == user.id).first():
            continue
        for pos, pid in enumerate(PROFILE_IDS):
            conf = PROFILES[pid]
            db.add(Profile(user_id=user.id, slug=pid, name=conf["name"], color=conf["color"], position=pos))
    db.commit()


def ensure_categories(db: Session) -> None:
    """Migración idempotente: crea las categorías en BD a partir de las constantes
    para cualquier usuario que aún no las tenga. Los nombres coinciden con los que
    ya usan las transacciones/presupuestos, así que el histórico sigue coherente."""
    for user in db.query(User).all():
        if db.query(Category).filter(Category.user_id == user.id).first():
            continue
        for pid, conf in PROFILES.items():
            for kind, key in (("income", "income_categories"), ("expense", "expense_categories")):
                for name in conf[key]:
                    db.add(Category(user_id=user.id, profile=pid, kind=kind,
                                    name=name, color=hash_color(name)))
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
