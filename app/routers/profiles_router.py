from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import category_index, category_names
from app.database import get_db
from app.finance import (
    budget_rows, donut_segments, fmt_eur, hash_color, last_n_months, month_groups, monthly_series,
    filter_transactions, resolve_period, savings_breakdown, totals_for,
)
from app.models import Account, Budget, Category, Profile, SavingsReserve, Transaction, User
from app.profiles import list_profiles, slugify
from app.seed import icon_for_category
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()

RESERVED_SLUGS = {"profiles", "accounts", "connect", "categories", "budgets", "goals", "debts",
                  "reports", "transactions", "search", "settings", "login", "logout", "add",
                  "webhooks", "receipt", "static"}


@router.get("/profiles")
def profiles_hub(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "profiles")
    A = ctx["A"]
    profiles = list_profiles(db, user.id)
    rows = []
    for p in profiles:
        totals = totals_for(db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.profile == p.slug).all())
        rows.append({"slug": p.slug, "name": p.name, "color": A(p.color), "raw_color": p.color,
                     "icon": p.icon, "net": fmt_eur(totals["net"]),
                     "savings_rate": round(p.savings_rate or 0), "tax_rate": round(p.tax_rate or 0),
                     "reserve_rate": round((p.savings_rate or 0) + (p.tax_rate or 0))})
    return templates.TemplateResponse(request, "profiles.html", {**ctx, "profiles": rows})


@router.post("/profiles")
def add_profile(name: str = Form(...), color: str = Form("#12898F"), icon: str = Form(""),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = name.strip()
    if name:
        existing = {p.slug for p in list_profiles(db, user.id)} | RESERVED_SLUGS
        slug = slugify(name, existing)
        pos = db.query(Profile).filter(Profile.user_id == user.id).count()
        db.add(Profile(user_id=user.id, slug=slug, name=name, color=color or "#12898F", icon=icon.strip(), position=pos))
        # Categorías iniciales para que el perfil sea usable de inmediato.
        for kind, names in (("income", ["Ingreso", "Otros ingresos"]), ("expense", ["Compras", "Otros"])):
            for cname in names:
                db.add(Category(user_id=user.id, profile=slug, kind=kind, name=cname,
                                color=hash_color(cname), icon=icon_for_category(cname)))
        db.commit()
    return RedirectResponse("/profiles", status_code=303)


@router.post("/profiles/{slug}/edit")
def edit_profile(slug: str, name: str = Form(...), color: str = Form(...), icon: str = Form(""),
                 savings_rate: str = Form(""), tax_rate: str = Form(""),
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.query(Profile).filter(Profile.slug == slug, Profile.user_id == user.id).first()
    if p and name.strip():
        p.name = name.strip()
        p.color = color or p.color
        p.icon = icon.strip()
        # Tasas de ahorro/impuestos (0–100). Se ignoran valores no numéricos o fuera de rango.
        for field, raw in (("savings_rate", savings_rate), ("tax_rate", tax_rate)):
            try:
                v = float(raw)
                if 0 <= v <= 100:
                    setattr(p, field, v)
            except (ValueError, TypeError):
                pass
        db.commit()
    return RedirectResponse("/profiles", status_code=303)


@router.post("/profiles/{slug}/rename")
def rename_profile(slug: str, name: str = Form(...),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Renombra SOLO el nombre del perfil (botón de la cabecera del perfil)."""
    p = db.query(Profile).filter(Profile.slug == slug, Profile.user_id == user.id).first()
    if p and name.strip():
        p.name = name.strip()
        db.commit()
    return RedirectResponse(f"/{slug}", status_code=303)


@router.post("/profiles/{slug}/delete")
def delete_profile(slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profiles = list_profiles(db, user.id)
    if len(profiles) <= 1:
        return RedirectResponse("/profiles", status_code=303)  # debe quedar al menos uno
    p = next((x for x in profiles if x.slug == slug), None)
    if p:
        # Reasigna las transacciones al primer perfil restante y borra categorías/presupuestos propios.
        fallback = next(x for x in profiles if x.slug != slug)
        db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.profile == slug).update(
            {"profile": fallback.slug}, synchronize_session=False)
        db.query(Category).filter(Category.user_id == user.id, Category.profile == slug).delete(synchronize_session=False)
        db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == slug).delete(synchronize_session=False)
        db.delete(p)
        db.commit()
    return RedirectResponse("/profiles", status_code=303)


@router.get("/{profile_id}")
def profile_page(
    profile_id: str, request: Request, search: str = "", type: str = "all",
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    profile_obj = db.query(Profile).filter(Profile.slug == profile_id, Profile.user_id == user.id).first()
    if not profile_obj:
        raise HTTPException(status_code=404)
    conf = {"name": profile_obj.name, "color": profile_obj.color}
    ctx = base_context(db, user, profile_id)
    A = ctx["A"]

    list_tx = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.profile == profile_id).all()
    totals = totals_for(list_tx)

    accounts = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()

    form_type = request.query_params.get("form_type", "income")
    categories = category_names(db, user.id, kind=form_type)
    bulk_categories = category_names(db, user.id)

    expense_by_cat: dict[str, float] = {}
    for t in list_tx:
        if t.type == "expense":
            expense_by_cat[t.category] = expense_by_cat.get(t.category, 0) + t.amount
    donut_segs = donut_segments(expense_by_cat)

    months6 = last_n_months(6)
    series = monthly_series(list_tx, months6)
    net_vals = [s["net"] for s in series]
    exp_vals = [s["expense"] for s in series]
    inc_vals = [s["income"] for s in series]
    # Eje compartido para neto, ingresos y gastos.
    lo = min([0] + net_vals)
    hi = max([1] + net_vals + exp_vals + inc_vals)
    rng = (hi - lo) or 1
    n = len(series)

    def _y(v):
        return round(140 - ((v - lo) / rng) * 120, 1)

    def _x(i):
        return round((i / (n - 1 if n > 1 else 1)) * 560 + 20, 1)

    line_dots = [{"x": _x(i), "y": _y(s["net"]), "label": s["label"]} for i, s in enumerate(series)]
    line_points = " ".join(f"{d['x']},{d['y']}" for d in line_dots)
    expense_points = " ".join(f"{_x(i)},{_y(v)}" for i, v in enumerate(exp_vals))
    income_points = " ".join(f"{_x(i)},{_y(v)}" for i, v in enumerate(inc_vals))

    # Segunda línea: gasto acumulado (running total) del mes en curso.
    cur_key = date.today().strftime("%Y-%m")
    month_exp = sorted([t for t in list_tx if t.type == "expense" and t.date.strftime("%Y-%m") == cur_key],
                       key=lambda t: t.date)
    cumulative_points = ""
    if len(month_exp) >= 2:
        running, cum_vals = 0.0, []
        for t in month_exp:
            running += t.amount
            cum_vals.append(running)
        cmax = max(cum_vals) or 1
        cn = len(cum_vals)
        pts = []
        for i, v in enumerate(cum_vals):
            x = (i / (cn - 1)) * 560 + 20
            y = 140 - (v / cmax) * 120
            pts.append(f"{round(x, 1)},{round(y, 1)}")
        cumulative_points = " ".join(pts)

    months3_keys = [m.strftime("%Y-%m") for m in last_n_months(3)]
    budgets = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id,
                                      Budget.period == "monthly").order_by(Budget.id).all()
    b_rows = budget_rows(profile_id, budgets, list_tx, cur_key, months3_keys)
    for row in b_rows:
        row["spent_label"] = fmt_eur(row["spent"])
        row["allocated_label"] = fmt_eur(row["allocated"])
        row["suggestion_label"] = fmt_eur(row["suggestion"])
        row["bar_color"] = "#E2574C" if row["over"] else A(conf["color"])

    filtered = filter_transactions(list_tx, search=search, type_=type)
    cat_idx = category_index(db, user.id)
    history_rows = []
    for t in filtered:
        cat = cat_idx.get((t.type, t.category)) or cat_idx.get(t.category)
        cat_raw = cat.color if cat else hash_color(t.category or "?")
        history_rows.append({
            "id": t.id, "category": t.category, "note": t.note, "date": t.date,
            "amount_label": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
            "color": A("#3FA65C" if t.type == "income" else "#E2574C"),
            "signed": t.amount if t.type == "income" else -t.amount,
            "has_receipt": bool(t.attachment_name), "place_name": t.place_name or "",
            "subcategory": t.subcategory or "", "store": t.store or "", "quantity": t.quantity or "",
            "account_name": (t.account.name if t.account else ""),
            "cat_icon": (cat.icon if cat else ""), "cat_color": A(cat_raw), "cat_raw_color": cat_raw,
            "initial": (t.category[0].upper() if t.category else "?"),
        })
    history_groups = month_groups(history_rows)

    # Reserva de ahorro/impuestos de este perfil, mes en curso (impuestos y ahorro por separado).
    per = resolve_period("month")
    cats_all = db.query(Category).filter(Category.user_id == user.id).all()
    txs_month = [t for t in list_tx if per["start"] <= t.date <= per["end"]]
    sav_bd = savings_breakdown([profile_obj], cats_all, txs_month, per["start"], per["end"])
    sav_row = sav_bd["rows"][0] if sav_bd["rows"] else None
    reserved_month = sum(r.amount for r in db.query(SavingsReserve).filter(
        SavingsReserve.user_id == user.id, SavingsReserve.profile == profile_id,
        SavingsReserve.period_key == per["key"]).all())
    savings_ctx = None
    if sav_row:
        pending = max(0.0, sav_row["total"] - reserved_month)
        savings_ctx = {
            "income": sav_row["income_label"], "tax": sav_row["tax_label"], "savings": sav_row["savings_label"],
            "tax_rate": round(sav_row["tax_rate"]), "savings_rate": round(sav_row["savings_rate"]),
            "total": sav_row["total_label"], "reserved": fmt_eur(reserved_month),
            "pending": fmt_eur(pending), "has_pending": pending > 0.005,
            "has_income": sav_row["income"] > 0.005,
        }

    profile_ctx = {
        "id": profile_id, "name": conf["name"], "color": A(conf["color"]),
        "income": fmt_eur(totals["income"]), "expense": fmt_eur(totals["expense"]), "net": fmt_eur(totals["net"]),
        "categories": categories, "bulk_categories": bulk_categories, "form_type": form_type,
        "donut_segs": donut_segs, "has_expenses": len(donut_segs) > 0,
        "line_points": line_points, "line_dots": line_dots, "cumulative_points": cumulative_points,
        "expense_points": expense_points, "income_points": income_points,
        "budgets": b_rows, "savings": savings_ctx,
        "history_groups": history_groups, "history_count": len(history_rows),
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
    if not db.query(Profile).filter(Profile.slug == profile_id, Profile.user_id == user.id).first():
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


@router.post("/{profile_id}/transactions/bulk-account")
async def bulk_account(profile_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("tx_id")]
    account_id = form.get("account_id")
    if ids and account_id:
        acc = db.query(Account).filter(Account.id == int(account_id), Account.user_id == user.id).first()
        if acc:
            db.query(Transaction).filter(Transaction.id.in_(ids), Transaction.user_id == user.id).update(
                {"account_id": acc.id}, synchronize_session=False
            )
            db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/budgets/{category}/topup")
def topup_budget(profile_id: str, category: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == category, Budget.period == 'monthly').first()
    if b:
        b.allocated = round(b.allocated + 10, 2)
        db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)


@router.post("/{profile_id}/budgets/{category}/apply-suggestion")
def apply_suggestion(profile_id: str, category: str, suggestion: float = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == category, Budget.period == 'monthly').first()
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
        b_from = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == from_category, Budget.period == 'monthly').first()
        b_to = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile_id, Budget.category == to_category, Budget.period == 'monthly').first()
        if b_from and b_to:
            b_from.allocated = max(0, round(b_from.allocated - amount, 2))
            b_to.allocated = round(b_to.allocated + amount, 2)
            db.commit()
    return RedirectResponse(f"/{profile_id}", status_code=303)
