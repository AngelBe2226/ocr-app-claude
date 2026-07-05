from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.finance import fmt_eur, fmt_money, hash_color, net_worth_eur
from app.constants import FX_RATES
from app.models import Account, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/accounts")
def accounts_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "accounts")
    A = ctx["A"]
    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    rows = []
    for a in accounts:
        is_card = a.type == "card"
        rows.append({
            "id": a.id, "name": a.name, "initial": a.name[0].upper(), "color": A(a.color),
            "tint": "rgba(255,255,255,0.08)" if ctx["is_dark"] else a.color + "22",
            "balance_label": fmt_money(a.balance, a.currency), "show_eur": a.currency != "EUR",
            "eur_label": fmt_eur(a.balance * FX_RATES.get(a.currency, 1)),
            "is_card": is_card, "cycle_end": a.cycle_end, "due_date": a.due_date,
        })
    return templates.TemplateResponse(request, "accounts.html", {**ctx, "accounts": rows})


@router.post("/accounts")
def add_account(
    name: str = Form(...), type: str = Form(...), currency: str = Form(...), balance: float = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    db.add(Account(user_id=user.id, name=name, type=type, currency=currency, balance=balance, color=hash_color(name)))
    db.commit()
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}/delete")
def delete_account(account_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if acc:
        db.delete(acc)
        db.commit()
    return RedirectResponse("/accounts", status_code=303)
