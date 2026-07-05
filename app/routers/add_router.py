from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import list_categories
from app.constants import PROFILE_IDS, PROFILES
from app.database import get_db
from app.models import Account, Transaction, Transfer, User
from app.receipts import receipt_path, save_receipt

router = APIRouter()


def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return datetime.today().date()


@router.get("/add/options")
def add_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Datos para poblar el modal de 'Añadir' (perfiles, cuentas y categorías)."""
    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    cats = list_categories(db, user.id)
    return JSONResponse({
        "profiles": [{"id": p, "name": PROFILES[p]["name"]} for p in PROFILE_IDS],
        "accounts": [{"id": a.id, "name": a.name} for a in accounts],
        "categories": [{"profile": c.profile, "kind": c.kind, "name": c.name} for c in cats],
    })


def _add_transaction(db, user, kind, profile, category, account_id, amount, date_, note,
                     latitude=None, longitude=None, place_name="", attachment: UploadFile | None = None):
    if profile not in PROFILES or not amount or amount <= 0:
        return None
    tx = Transaction(
        user_id=user.id, profile=profile, type=kind, category=category,
        amount=round(amount, 2), date=_parse_date(date_), note=note or "",
        account_id=int(account_id), attachment_name=save_receipt(attachment),
        latitude=latitude, longitude=longitude, place_name=(place_name or "").strip(),
    )
    db.add(tx)
    db.commit()
    return tx


@router.post("/add/expense")
def add_expense(
    profile: str = Form(...), category: str = Form(...), account_id: int = Form(...),
    amount: float = Form(...), date: str = Form(...), note: str = Form(""),
    latitude: str = Form(""), longitude: str = Form(""), place_name: str = Form(""),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    lat = float(latitude) if latitude else None
    lng = float(longitude) if longitude else None
    _add_transaction(db, user, "expense", profile, category, account_id, amount, date, note,
                     lat, lng, place_name, attachment)
    return RedirectResponse(f"/{profile}", status_code=303)


@router.post("/add/income")
def add_income(
    profile: str = Form(...), category: str = Form(...), account_id: int = Form(...),
    amount: float = Form(...), date: str = Form(...), note: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _add_transaction(db, user, "income", profile, category, account_id, amount, date, note)
    return RedirectResponse(f"/{profile}", status_code=303)


@router.post("/add/transfer")
def add_transfer(
    from_account_id: int = Form(...), to_account_id: int = Form(...),
    amount: float = Form(...), date: str = Form(...), note: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if from_account_id != to_account_id and amount and amount > 0:
        src = db.query(Account).filter(Account.id == from_account_id, Account.user_id == user.id).first()
        dst = db.query(Account).filter(Account.id == to_account_id, Account.user_id == user.id).first()
        if src and dst:
            # Mueve el saldo entre cuentas. No crea transacciones, así que no aparece
            # como ingreso/gasto en los reportes por categoría.
            src.balance = round(src.balance - amount, 2)
            dst.balance = round(dst.balance + amount, 2)
            db.add(Transfer(user_id=user.id, from_account_id=from_account_id, to_account_id=to_account_id,
                            amount=round(amount, 2), date=_parse_date(date), note=note or ""))
            db.commit()
    return RedirectResponse("/accounts", status_code=303)


@router.get("/receipt/{tx_id}")
def get_receipt(tx_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user.id).first()
    if not tx or not tx.attachment_name:
        return RedirectResponse("/", status_code=303)
    path = receipt_path(tx.attachment_name)
    if not path:
        return RedirectResponse("/", status_code=303)
    return FileResponse(path)
