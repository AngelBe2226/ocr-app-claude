from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.constants import FX_RATES
from app.database import get_db
from app.finance import fmt_eur, fmt_money, hash_color, net_worth_eur
from app.models import Account, Loan, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()

# Orden y etiqueta de cada grupo de cuentas en la vista de lista.
ACCOUNT_GROUPS = [
    ("card", "Tarjetas de crédito"),
    ("bank", "Bancos"),
    ("savings", "Ahorro"),
    ("cash", "Dinero"),
    ("other", "Otro"),
]


def _parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@router.get("/accounts")
def accounts_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "accounts")
    A = ctx["A"]
    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()

    # Agrupa las cuentas por tipo, cada grupo con su subtotal convertido a EUR.
    grouped: dict[str, dict] = {key: {"key": key, "label": label, "subtotal": 0.0, "accounts": []}
                                for key, label in ACCOUNT_GROUPS}
    for a in accounts:
        group_key = a.type if a.type in grouped else "other"
        eur = a.balance * FX_RATES.get(a.currency, 1)
        grouped[group_key]["subtotal"] += eur
        is_card = a.type == "card"
        grouped[group_key]["accounts"].append({
            "id": a.id, "name": a.name, "initial": a.name[0].upper() if a.name else "?", "icon": a.icon,
            "color": A(a.color), "raw_color": a.color,
            "tint": "rgba(255,255,255,0.08)" if ctx["is_dark"] else a.color + "22",
            "type": a.type, "currency": a.currency, "balance": a.balance,
            "balance_label": fmt_money(a.balance, a.currency), "show_eur": a.currency != "EUR",
            "eur_label": fmt_eur(eur),
            "is_card": is_card, "cycle_end": a.cycle_end, "due_date": a.due_date,
            "cycle_end_value": a.cycle_end.isoformat() if a.cycle_end else "",
            "due_date_value": a.due_date.isoformat() if a.due_date else "",
        })

    groups = [g for g in grouped.values() if g["accounts"]]
    for g in groups:
        g["subtotal_label"] = fmt_eur(g["subtotal"])

    net = net_worth_eur(accounts, loans)
    assets = sum(max(0.0, a.balance * FX_RATES.get(a.currency, 1)) for a in accounts)
    liabilities = sum(max(0.0, -(a.balance * FX_RATES.get(a.currency, 1))) for a in accounts) + sum(l.balance for l in loans)
    summary = {
        "net_worth": fmt_eur(net), "net_positive": net >= 0,
        "assets": fmt_eur(assets), "liabilities": fmt_eur(liabilities),
    }

    return templates.TemplateResponse(request, "accounts.html", {**ctx, "groups": groups, "summary": summary})


@router.post("/accounts")
def add_account(
    name: str = Form(...), type: str = Form(...), currency: str = Form(...), balance: float = Form(...),
    icon: str = Form(""), db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    db.add(Account(user_id=user.id, name=name, type=type, currency=currency, balance=balance,
                   color=hash_color(name), icon=icon.strip()))
    db.commit()
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}/edit")
def edit_account(
    account_id: int,
    name: str = Form(...), type: str = Form(...), currency: str = Form(...),
    balance: float = Form(...), color: str = Form(...), icon: str = Form(""),
    cycle_end: str = Form(""), due_date: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    acc = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if acc:
        acc.name = name.strip() or acc.name
        acc.type = type
        acc.currency = currency
        acc.balance = balance
        acc.color = color or acc.color
        acc.icon = icon.strip()
        if type == "card":
            acc.cycle_end = _parse_date(cycle_end)
            acc.due_date = _parse_date(due_date)
        else:
            acc.cycle_end = None
            acc.due_date = None
        db.commit()
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}/delete")
def delete_account(account_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if acc:
        db.delete(acc)
        db.commit()
    return RedirectResponse("/accounts", status_code=303)
