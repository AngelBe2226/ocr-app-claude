from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import category_names
from app.constants import PROFILE_IDS, PROFILES
from app.database import get_db
from app.finance import (
    budget_rows, donut_segments, fmt_eur, last_n_months, month_short_label, monthly_series,
    filter_transactions, totals_for,
)
from app.models import Account, Budget, Transaction, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


def _profile_or_404(profile_id: str):
    if profile_id not in PROFILE_IDS:
        raise HTTPException(status_code=404)
    return PROFILES[profile_id]


@router.get("/{profile_id}")
def profile_page(
    profile_id: str, request: Request, search: str = "", type: str = "all",
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if profile_id not in PROFILE_IDS:
        raise HTTPException(status_code=404)
    conf = PROFILES[profile_id]
    ctx = base_context(db, user, profile_id)
    A = ctx["A"]

    list_tx = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.profile == profile_id).all()
    totals = totals_for(list_tx)

    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()

    form_type = request.query_params.get("form_type", "income")
    categories = category_names(db, user.id, profile=profile_id, kind=form_type)
    bulk_categories = category_names(db, user.id, profile=profile_id)

    expense_by_cat: dict[str, float] = {}
    for t in list_tx:
        if t.type == "expense":
            expense_by_cat[t.category] = expense_by_cat.get(t.category, 0) + t.amount
    donut_segs = donut_segments(expense_by_cat)

    months6 = last_n_months(6)
    series = monthly_series(list_tx, months6)
    net_vals = [s["net"] for s in series]
    min_net, max_net = min([0] + net_vals), max([1] + net_vals)
    rng = (max_net - min_net) or 1
    n = len(series)
    line_dots = []
    for i, s in enumerate(series):
        x = (i / (n - 1 if n > 1 else 1)) * 560 + 20
        y = 140 - ((s["net"] - min_net) / rng) * 120
        line_dots.append({"x": round(x, 1), "y": round(y, 1), "label": s["label"]})
    line_points = " ".join(f"{d['x']},{d['y']}" for d in line_dots)

    cur_key = date.today().strftime("%Y-%m")
    months3_keys = [m.strftime("%Y-%m") for m in last_n_months(3)]
    budgets = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id).order_by(Budget.id).all()
    b_rows = budget_rows(profile_id, budgets, list_tx, cur_key, months3_keys)
    for row in b_rows:
        row["spent_label"] = fmt_eur(row["spent"])
        row["allocated_label"] = fmt_eur(row["allocated"])
        row["suggestion_label"] = fmt_eur(row["suggestion"])
        row["bar_color"] = "#E2574C" if row["over"] else A(conf["color"])

    filtered = filter_transactions(list_tx, search=search, type_=type)
    history_rows = [{
        "id": t.id, "category": t.category, "note": t.note, "date_label": t.date,
        "amount_label": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
        "color": A("#3FA65C" if t.type == "income" else "#E2574C"),
        "has_receipt": bool(t.attachment_name), "place_name": t.place_name or "",
    } for t in filtered]

    profile_ctx = {
        "id": profile_id, "name": conf["name"], "color": A(conf["color"]),
        "income": fmt_eur(totals["income"]), "expense": fmt_eur(totals["expense"]), "net": fmt_eur(totals["net"]),
        "categories": categories, "bulk_categories": bulk_categories, "form_type": form_type,
        "donut_segs": donut_segs, "has_expenses": len(donut_segs) > 0,
        "line_points": line_points, "line_dots": line_dots,
        "budgets": b_rows,
        "history": history_rows,
    }

    return templates.TemplateResponse(request, "profile.html", {
        **ctx, "profile": profile_ctx, "accounts": accounts,
        "search": search, "type_filter": type, "today_iso": date.today().isoformat(),
        "rebalance_from": (b_rows[0]["category"] if b_rows else ""),
        "rebalance_to": (b_rows[1]["category"] if len(b_rows) > 1 else ""),
    })


@router.post("/{profile_id}/transactions")
def add_transaction(
    profile_id: str, request: Request,
    type: str = Form(...), category: str = Form(...), account_id: int = Form(...),
    amount: float = Form(...), date_: str = Form(..., alias="date"), note: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if profile_id not in PROFILE_IDS:
        raise HTTPException(status_code=404)
    if amount and amount > 0:
        tx = Transaction(
            user_id=user.id, profile=profile_id, type=type, category=category,
            amount=round(amount, 2), date=datetime.strptime(date_, "%Y-%m-%d").date(),
            note=note, account_id=account_id, attachment_name="",
        )
        db.add(tx)
        db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/transactions/{tx_id}/delete")
def delete_transaction(profile_id: str, tx_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user.id).first()
    if tx:
        db.delete(tx)
        db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/transactions/bulk-delete")
async def bulk_delete(profile_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("tx_id")]
    if ids:
        db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).delete(synchronize_session=False)
        db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/transactions/bulk-category")
async def bulk_category(profile_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("tx_id")]
    category = form.get("category")
    if ids and category:
        db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).update(
            {"category": category}, synchronize_session=False
        )
        db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/budgets/{category}/topup")
def topup_budget(profile_id: str, category: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == category).first()
    if b:
        b.allocated = round(b.allocated + 10, 2)
        db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/budgets/{category}/apply-suggestion")
def apply_suggestion(profile_id: str, category: str, suggestion: float = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == category).first()
    if b:
        b.allocated = round(suggestion)
        db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/budgets/rebalance")
def rebalance(
    profile_id: str, from_category: str = Form(...), to_category: str = Form(...), amount: float = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if from_category != to_category and amount and amount > 0:
        b_from = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == from_category).first()
        b_to = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == to_category).first()
        if b_from and b_to:
            b_from.allocated = max(0, round(b_from.allocated - amount, 2))
            b_to.allocated = round(b_to.allocated + amount, 2)
            db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)
