from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import category_index, category_names
from app.constants import TYPE_FILTER_OPTIONS
from app.database import get_db
from app.finance import (
    export_csv_bytes, fmt_date_es, filter_transactions, fmt_eur, hash_color, month_groups,
    parse_anchor, resolve_period, totals_for,
)
from app.models import Account, Transaction, User
from app.pdf import build_transactions_pdf
from app.profiles import pcolor, pname, profile_filter_options, profiles_map
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/transactions/{tx_id}/json")
def transaction_json(tx_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user.id).first()
    if not t:
        raise HTTPException(status_code=404)
    return JSONResponse({
        "id": t.id, "profile": t.profile, "type": t.type, "category": t.category,
        "subcategory": t.subcategory or "", "store": t.store or "", "quantity": t.quantity or "-",
        "account_id": t.account_id, "amount": t.amount, "date": t.date.isoformat(), "note": t.note or "",
    })


@router.post("/transactions/{tx_id}/edit")
def edit_transaction(
    tx_id: int, request: Request,
    type: str = Form(...), profile: str = Form(...), category: str = Form(...),
    account_id: int = Form(...), amount: float = Form(...), date: str = Form(...), note: str = Form(""),
    subcategory: str = Form(""), store: str = Form(""), quantity: str = Form("-"),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    t = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user.id).first()
    if t and profile in profiles_map(db, user.id) and amount and amount > 0:
        t.type = "income" if type == "income" else "expense"
        t.profile = profile
        t.category = category
        t.subcategory = (subcategory or "").strip()
        t.store = (store or "").strip()
        t.quantity = (quantity or "-").strip() or "-"
        t.account_id = account_id
        t.amount = round(amount, 2)
        t.date = datetime.strptime(date, "%Y-%m-%d").date()
        t.note = note or ""
        db.commit()
    ref = request.headers.get("referer")
    return RedirectResponse(ref if ref else "/transactions", status_code=303)


def build_tx_rows(transactions, A, pmap, show_profile=True, cat_index=None):
    cat_index = cat_index or {}
    rows = []
    for t in transactions:
        signed = t.amount if t.type == "income" else -t.amount
        cat = cat_index.get((t.type, t.category)) or cat_index.get(t.category)
        cat_raw_color = cat.color if cat else hash_color(t.category or "?")
        row = {
            "id": t.id, "category": t.category, "note": t.note, "date": t.date,
            "amount_label": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
            "color": A("#3FA65C" if t.type == "income" else "#E2574C"),
            "signed": signed, "has_receipt": bool(t.attachment_name), "place_name": t.place_name or "",
            "subcategory": t.subcategory or "", "store": t.store or "", "quantity": getattr(t, "quantity", "") or "",
            "account_name": (t.account.name if t.account else ""),
            "cat_icon": (cat.icon if cat else ""), "cat_color": A(cat_raw_color), "cat_raw_color": cat_raw_color,
            "initial": (t.category[0].upper() if t.category else "?"),
        }
        if show_profile:
            row["profile_name"] = pname(pmap, t.profile)
            row["profile_color"] = A(pcolor(pmap, t.profile))
            row["profile_tint"] = pcolor(pmap, t.profile) + "22"
        rows.append(row)
    return rows


TX_PERIOD_OPTIONS = [("all", "Todo"), ("day", "Día"), ("week", "Semana"), ("month", "Mes"), ("year", "Año")]


def _apply_query(transactions, q) -> list:
    """Aplica a la lista de transacciones todos los filtros de la query: periodo
    (día/semana/mes/año/todo), búsqueda, perfil, tipo, categoría, subcategoría y tienda."""
    per = resolve_period(q.get("period", "all"), parse_anchor(q.get("anchor", "")))
    date_from = "" if per.get("is_all") else per["start"].isoformat()
    date_to = "" if per.get("is_all") else per["end"].isoformat()
    return filter_transactions(
        transactions, search=q.get("search", ""), profile=q.get("profile", "all"), type_=q.get("type", "all"),
        date_from=date_from, date_to=date_to, category=q.get("category", "all"),
        subcategory=q.get("subcategory", "all"), store=q.get("store", "all"))


@router.get("/transactions")
def transactions_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "transactions")
    A = ctx["A"]
    q = request.query_params
    search, profile, type_ = q.get("search", ""), q.get("profile", "all"), q.get("type", "all")
    category, subcategory, store = q.get("category", "all"), q.get("subcategory", "all"), q.get("store", "all")
    per = resolve_period(q.get("period", "all"), parse_anchor(q.get("anchor", "")))
    date_from = "" if per.get("is_all") else per["start"].isoformat()
    date_to = "" if per.get("is_all") else per["end"].isoformat()

    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = filter_transactions(transactions, search=search, profile=profile, type_=type_,
                                   date_from=date_from, date_to=date_to,
                                   category=category, subcategory=subcategory, store=store)
    totals = totals_for(filtered)
    groups = month_groups(build_tx_rows(filtered, A, profiles_map(db, user.id), show_profile=True,
                                        cat_index=category_index(db, user.id)))

    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    subcats = sorted({(t.subcategory or "").strip() for t in transactions if (t.subcategory or "").strip()})
    stores = sorted({(t.store or "").strip() for t in transactions if (t.store or "").strip()})
    nav_extra = "".join(
        f"&{k}={quote(v)}" for k, v in [("search", search), ("profile", profile), ("type", type_),
                                        ("category", category), ("subcategory", subcategory), ("store", store)]
        if v and v != "all")
    return templates.TemplateResponse(request, "transactions.html", {
        **ctx, "groups": groups, "all_categories": category_names(db, user.id),
        "accounts": [{"id": a.id, "name": a.name} for a in accounts],
        "filters": {"search": search, "profile": profile, "type": type_,
                    "category": category, "subcategory": subcategory, "store": store},
        "subcats": subcats, "stores": stores,
        "profile_filter_options": profile_filter_options(db, user.id), "type_filter_options": TYPE_FILTER_OPTIONS,
        "per": per, "period_options": TX_PERIOD_OPTIONS, "nav_base": "/transactions", "nav_extra": nav_extra,
        "sum_income": fmt_eur(totals["income"]), "sum_expense": fmt_eur(totals["expense"]),
        "sum_net": fmt_eur(totals["net"]), "net_positive": totals["net"] >= 0, "tx_count": len(filtered),
    })


def _export_rows(filtered, pmap):
    return [{
        "date": fmt_date_es(t.date), "profile": pname(pmap, t.profile), "category": t.category,
        "note": t.note or "", "amount": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
    } for t in filtered]


@router.get("/transactions/export.pdf")
def export_transactions_pdf(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = request.query_params
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = _apply_query(transactions, q)
    totals = totals_for(filtered)
    pdf = build_transactions_pdf("Todos los Movimientos", _export_rows(filtered, profiles_map(db, user.id)), fmt_eur(totals["net"]))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=movimientos.pdf"})


@router.get("/transactions/export.csv")
def export_transactions_csv(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = request.query_params
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = _apply_query(transactions, q)
    return Response(content=export_csv_bytes(filtered), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=movimientos.csv"})


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
    groups = month_groups(build_tx_rows(filtered, A, profiles_map(db, user.id), show_profile=True,
                                        cat_index=category_index(db, user.id)))
    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    account_options = [{"id": "all", "name": "Todas las cuentas"}] + [{"id": a.id, "name": a.name} for a in accounts]
    return templates.TemplateResponse(request, "search.html", {
        **ctx, "groups": groups, "result_count": len(filtered),
        "all_categories": category_names(db, user.id),
        "accounts": [{"id": a.id, "name": a.name} for a in accounts],
        "account_options": account_options, "filters": filters,
        "profile_filter_options": profile_filter_options(db, user.id), "type_filter_options": TYPE_FILTER_OPTIONS,
    })
