from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import category_names
from app.constants import PROFILE_FILTER_OPTIONS, PROFILES, TYPE_FILTER_OPTIONS
from app.database import get_db
from app.finance import filter_transactions, fmt_eur, month_groups
from app.models import Account, Transaction, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


def build_tx_rows(transactions, A, show_profile=True):
    rows = []
    for t in transactions:
        signed = t.amount if t.type == "income" else -t.amount
        row = {
            "id": t.id, "category": t.category, "note": t.note, "date": t.date,
            "amount_label": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
            "color": A("#3FA65C" if t.type == "income" else "#E2574C"),
            "signed": signed, "has_receipt": bool(t.attachment_name), "place_name": t.place_name or "",
        }
        if show_profile:
            row["profile_name"] = PROFILES[t.profile]["name"]
            row["profile_color"] = A(PROFILES[t.profile]["color"])
            row["profile_tint"] = PROFILES[t.profile]["color"] + "22"
        rows.append(row)
    return rows


@router.get("/transactions")
def transactions_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "transactions")
    A = ctx["A"]
    q = request.query_params
    search, profile, type_ = q.get("search", ""), q.get("profile", "all"), q.get("type", "all")

    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = filter_transactions(transactions, search=search, profile=profile, type_=type_)
    groups = month_groups(build_tx_rows(filtered, A, show_profile=True))

    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    return templates.TemplateResponse(request, "transactions.html", {
        **ctx, "groups": groups, "all_categories": category_names(db, user.id),
        "accounts": [{"id": a.id, "name": a.name} for a in accounts],
        "filters": {"search": search, "profile": profile, "type": type_},
        "profile_filter_options": PROFILE_FILTER_OPTIONS, "type_filter_options": TYPE_FILTER_OPTIONS,
    })


def _selected_ids(form):
    return [int(v) for v in form.getlist("tx_id")]


def _back(request: Request) -> str:
    # Vuelve a la página desde la que se lanzó la acción (Movimientos o Buscar).
    ref = request.headers.get("referer")
    return ref if ref else "/transactions"


@router.post("/transactions/bulk-delete")
async def bulk_delete(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ids = _selected_ids(await request.form())
    if ids:
        db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).delete(synchronize_session=False)
        db.commit()
    return RedirectResponse(_back(request), status_code=303)


@router.post("/transactions/bulk-category")
async def bulk_category(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ids, category = _selected_ids(form), form.get("category")
    if ids and category:
        db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).update(
            {"category": category}, synchronize_session=False)
        db.commit()
    return RedirectResponse(_back(request), status_code=303)


@router.post("/transactions/bulk-account")
async def bulk_account(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ids, account_id = _selected_ids(form), form.get("account_id")
    if ids and account_id:
        acc = db.query(Account).filter(Account.id == int(account_id), Account.user_id == user.id).first()
        if acc:
            db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).update(
                {"account_id": acc.id}, synchronize_session=False)
            db.commit()
    return RedirectResponse(_back(request), status_code=303)


@router.get("/search")
def search_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "search")
    A = ctx["A"]
    q = request.query_params
    filters = {
        "search": q.get("search", ""), "profile": q.get("profile", "all"),
        "account_id": q.get("account_id", "all"), "type": q.get("type", "all"),
        "date_from": q.get("date_from", ""), "date_to": q.get("date_to", ""),
    }
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = filter_transactions(
        transactions, search=filters["search"], profile=filters["profile"], type_=filters["type"],
        account_id=filters["account_id"], date_from=filters["date_from"], date_to=filters["date_to"],
    )
    groups = month_groups(build_tx_rows(filtered, A, show_profile=True))
    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    account_options = [{"id": "all", "name": "Todas las cuentas"}] + [{"id": a.id, "name": a.name} for a in accounts]
    return templates.TemplateResponse(request, "search.html", {
        **ctx, "groups": groups, "result_count": len(filtered),
        "all_categories": category_names(db, user.id),
        "accounts": [{"id": a.id, "name": a.name} for a in accounts],
        "account_options": account_options, "filters": filters,
        "profile_filter_options": PROFILE_FILTER_OPTIONS, "type_filter_options": TYPE_FILTER_OPTIONS,
    })
