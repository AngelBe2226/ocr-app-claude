"""Sincronización de transacciones bancarias.

En producción, un agregador Open Banking (Tink / GoCardless / TrueLayer) llamaría
al webhook con las transacciones reales. Aquí incluimos un generador "demo" que
produce transacciones de ejemplo y las importa por la MISMA ruta que usaría el
webhook, para poder probar el resto del flujo sin claves de API.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Account, BankConnection, Transaction

# Comercios de ejemplo: (descripción, categoría, tipo, importe_min, importe_max)
DEMO_MERCHANTS = [
    ("Mercadona", "Compras", "expense", 15, 90),
    ("Amazon", "Compras", "expense", 8, 140),
    ("Iberdrola", "Hogar", "expense", 40, 95),
    ("Netflix", "Suscripciones", "expense", 13, 18),
    ("Spotify", "Suscripciones", "expense", 10, 12),
    ("Farmacia", "Salud", "expense", 5, 35),
    ("Restaurante La Plaza", "Ocio", "expense", 15, 70),
    ("Repsol", "Hogar", "expense", 40, 85),
    ("Zara", "Compras", "expense", 20, 120),
    ("Glovo", "Ocio", "expense", 10, 45),
    ("Bizum recibido", "Reembolso", "income", 10, 120),
    ("Transferencia nómina", "Ingreso extra", "income", 1200, 1800),
]

PROFILE = "personal"  # las transacciones bancarias demo se asignan al perfil Personal


def generate_demo_transactions(n: int | None = None) -> list[dict]:
    """Genera una tanda de transacciones normalizadas (formato de webhook)."""
    if n is None:
        n = random.randint(10, 15)
    today = datetime.today().date()
    out = []
    for _ in range(n):
        desc, category, kind, lo, hi = random.choice(DEMO_MERCHANTS)
        amount = round(random.uniform(lo, hi), 2)
        signed = amount if kind == "income" else -amount
        d = today - timedelta(days=random.randint(0, 25))
        out.append({"date": d.isoformat(), "description": desc, "amount": signed, "category": category})
    return out


def import_bank_transactions(db: Session, connection: BankConnection, payload_txs: list[dict]) -> int:
    """Importa transacciones normalizadas a la cuenta ligada a la conexión.
    Formato de cada item: {date, description, amount (con signo), category?}.
    Es la ruta compartida por el webhook real y el modo demo."""
    account = db.get(Account, connection.account_id) if connection.account_id else None
    imported = 0
    net = 0.0
    for t in payload_txs:
        try:
            amount = float(t["amount"])
            tx_date = datetime.strptime(t["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError, TypeError):
            continue
        kind = "income" if amount >= 0 else "expense"
        db.add(Transaction(
            user_id=connection.user_id, profile=PROFILE, type=kind,
            category=t.get("category") or "Sin categoría", amount=round(abs(amount), 2),
            date=tx_date, note=t.get("description", ""),
            account_id=connection.account_id, attachment_name="",
        ))
        net += amount
        imported += 1
    if account:
        account.balance = round(account.balance + net, 2)
    connection.synced_count = (connection.synced_count or 0) + imported
    connection.last_sync = datetime.utcnow()
    db.commit()
    return imported
