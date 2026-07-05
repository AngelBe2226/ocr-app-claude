from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_or_create_settings
from app.constants import ACCENT_OPTIONS
from app.database import get_db
from app.finance import export_backup_json, export_csv_bytes, fmt_eur, net_worth_eur
from app.models import Account, Bill, Budget, FamilyInvite, Goal, Loan, Settings, Transaction, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "settings")
    invites = db.query(FamilyInvite).filter(FamilyInvite.user_id == user.id).order_by(FamilyInvite.id).all()

    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    cur_key = date.today().strftime("%Y-%m")
    month_spend = sum(t.amount for t in transactions if t.type == "expense" and t.date.strftime("%Y-%m") == cur_key)

    return templates.TemplateResponse(request, "settings.html", {
        **ctx, "invites": invites,
        "net_worth": fmt_eur(net_worth_eur(accounts, loans)),
        "widget_month_spend": fmt_eur(month_spend),
    })


@router.post("/settings/theme")
def toggle_theme(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = get_or_create_settings(db, user)
    settings.theme = "light" if settings.theme == "dark" else "dark"
    db.commit()
    referer = request.headers.get("referer", "/settings")
    return RedirectResponse(referer, status_code=303)


@router.post("/settings/accent")
def set_accent(request: Request, key: str = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if key in {a["key"] for a in ACCENT_OPTIONS}:
        settings = get_or_create_settings(db, user)
        settings.accent_key = key
        db.commit()
    referer = request.headers.get("referer", "/settings")
    return RedirectResponse(referer, status_code=303)


@router.post("/settings/family/invite")
def add_invite(email: str = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    email = email.strip()
    if email:
        db.add(FamilyInvite(user_id=user.id, email=email))
        db.commit()
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/family/remove/{invite_id}")
def remove_invite(invite_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inv = db.query(FamilyInvite).filter(FamilyInvite.id == invite_id, FamilyInvite.user_id == user.id).first()
    if inv:
        db.delete(inv)
        db.commit()
    return RedirectResponse("/settings", status_code=303)


@router.get("/settings/backup.json")
def backup_json(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()
    bills = db.query(Bill).filter(Bill.user_id == user.id).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id).all()
    budgets = db.query(Budget).filter(Budget.user_id == user.id).all()
    data = export_backup_json(accounts, transactions, loans, bills, goals, budgets)
    return Response(content=data, media_type="application/json", headers={"Content-Disposition": "attachment; filename=backup-mis-finanzas.json"})


@router.get("/settings/export.csv")
def export_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    data = export_csv_bytes(transactions)
    return Response(content=data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=movimientos.csv"})
