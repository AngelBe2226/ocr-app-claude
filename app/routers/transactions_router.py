from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import category_names
from app.constants import PROFILE_FILTER_OPTIONS, PROFILES, TYPE_FILTER_OPTIONS
from app.database import get_db
from app.finance import filter_transactions, fmt_eur
from app.models import Transaction, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/transactions")
def transactions_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "transactions")
    A = ctx["A"]
    q = request.query_params
    search, profile, type_ = q.get("search", ""), q.get("profile", "all"), q.get("type", "all")

    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = filter_transactions(transactions, search=search, profile=profile, type_=type_)

    all_categories = category_names(db, user.id)
    rows = []
    for t in filtered:
        rows.append({
            "id": t.id, "category": t.category, "note": t.note, "date_label": t.date,
            "amount_label": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
            "color": A("#3FA65C" if t.type == "income" else "#E2574C"),
            "profile_name": PROFILES[t.profile]["name"], "profile_color": A(PROFILES[t.profile]["color"]),
            "profile_tint": PROFILES[t.profile]["color"] + "22",
        })

    return templates.TemplateResponse(request, "transactions.html", {
        **ctx, "rows": rows, "empty": len(rows) == 0, "all_categories": all_categories,
        "filters": {"search": search, "profile": profile, "type": type_},
        "profile_filter_options": PROFILE_FILTER_OPTIONS, "type_filter_options": TYPE_FILTER_OPTIONS,
    })


@router.post("/transactions/bulk-delete")
async def bulk_delete(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("tx_id")]
    if ids:
        db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).delete(synchronize_session=False)
        db.commit()
    return RedirectResponse("/transactions", status_code=303)


@router.post("/transactions/bulk-category")
async def bulk_category(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("tx_id")]
    category = form.get("category")
    if ids and category:
        db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).update(
            {"category": category}, synchronize_session=False
        )
        db.commit()
    return RedirectResponse("/transactions", status_code=303)
