from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import list_categories
from app.constants import PROFILE_IDS, PROFILES
from app.database import get_db
from app.finance import fmt_eur, period_bounds, spent_in_period
from app.models import Budget, Category, SpendingLimit, Transaction, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()

PERIOD_LABEL = {"monthly": "mensual", "annual": "anual"}


def _category_lookup(db: Session, user_id: int) -> dict:
    return {(c.profile, c.name): c for c in list_categories(db, user_id)}


def _budget_card(b: Budget, transactions, cat_lookup, A, today: date) -> dict:
    pb = period_bounds(today, b.period)
    spent = spent_in_period(transactions, b.profile, b.category, pb["start"], pb["end"])
    remaining = b.allocated - spent
    pct = min(1.0, spent / b.allocated) if b.allocated else 0
    daily = remaining / max(1, pb["days_remaining"]) if remaining > 0 else 0
    cat = cat_lookup.get((b.profile, b.category))
    color = A(cat.color) if cat else A("#12898F")
    return {
        "id": b.id, "profile": b.profile, "profile_name": PROFILES[b.profile]["name"],
        "category": b.category, "icon": (cat.icon if cat and cat.icon else b.category[0].upper()),
        "color": color, "raw_color": cat.color if cat else "#12898F",
        "allocated": b.allocated, "allocated_label": fmt_eur(b.allocated),
        "spent_label": fmt_eur(spent), "remaining_label": fmt_eur(remaining),
        "pct": pct, "pct_label": f"{round(pct * 100)}%", "pct_width": f"{round(pct * 100)}%",
        "remaining_pct_label": f"{max(0, 100 - round(pct * 100))}%",
        "over": spent > b.allocated, "on_budget": spent <= b.allocated,
        "bar_color": "#E2574C" if spent > b.allocated else color,
        "days_remaining": pb["days_remaining"], "daily_label": fmt_eur(daily),
        "period": b.period, "period_label": pb["label"],
    }


@router.get("/budgets")
def budgets_page(request: Request, period: str = "monthly",
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if period not in ("monthly", "annual"):
        period = "monthly"
    ctx = base_context(db, user, "budgets")
    A = ctx["A"]
    today = date.today()

    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    cat_lookup = _category_lookup(db, user.id)
    budgets = (db.query(Budget).filter(Budget.user_id == user.id, Budget.period == period)
               .order_by(Budget.profile, Budget.category).all())
    cards = [_budget_card(b, transactions, cat_lookup, A, today) for b in budgets]

    total_alloc = sum(c["allocated"] for c in cards)
    total_spent = sum(spent_in_period(transactions, b.profile, b.category,
                                       period_bounds(today, b.period)["start"],
                                       period_bounds(today, b.period)["end"]) for b in budgets)

    # Opciones "Perfil — Categoría" de gasto para el formulario de alta.
    cat_options = []
    for pid in PROFILE_IDS:
        for c in list_categories(db, user.id, profile=pid, kind="expense"):
            cat_options.append({"value": f"{pid}|{c.name}", "label": f"{PROFILES[pid]['name']} — {c.name}"})

    limits = _limits_context(db, user.id, transactions, today, A)

    return templates.TemplateResponse(request, "budgets.html", {
        **ctx, "period": period, "period_label": PERIOD_LABEL[period], "cards": cards,
        "total_alloc": fmt_eur(total_alloc), "total_spent": fmt_eur(total_spent),
        "total_remaining": fmt_eur(total_alloc - total_spent),
        "cat_options": cat_options, "limits": limits,
    })


@router.get("/budgets/{budget_id}")
def budget_detail(budget_id: int, request: Request,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    if not b:
        raise HTTPException(status_code=404)
    ctx = base_context(db, user, "budgets")
    A = ctx["A"]
    today = date.today()
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    cat_lookup = _category_lookup(db, user.id)
    card = _budget_card(b, transactions, cat_lookup, A, today)
    pb = period_bounds(today, b.period)
    card["start_label"] = pb["start"]
    card["end_label"] = pb["end"]
    return templates.TemplateResponse(request, "budget_detail.html", {**ctx, "b": card})


@router.post("/budgets")
def add_budget(profile_category: str = Form(...), allocated: float = Form(...), period: str = Form("monthly"),
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if period not in ("monthly", "annual") or "|" not in profile_category or not allocated or allocated <= 0:
        return RedirectResponse(f"/budgets?period={period}", status_code=303)
    profile, category = profile_category.split("|", 1)
    if profile in PROFILES:
        existing = (db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == profile,
                                            Budget.category == category, Budget.period == period).first())
        if existing:
            existing.allocated = round(allocated, 2)
        else:
            db.add(Budget(user_id=user.id, profile=profile, category=category,
                          allocated=round(allocated, 2), period=period))
        db.commit()
    return RedirectResponse(f"/budgets?period={period}", status_code=303)


@router.post("/budgets/{budget_id}/edit")
def edit_budget(budget_id: int, allocated: float = Form(...),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    period = b.period if b else "monthly"
    if b and allocated and allocated > 0:
        b.allocated = round(allocated, 2)
        db.commit()
    return RedirectResponse(f"/budgets?period={period}", status_code=303)


@router.post("/budgets/{budget_id}/delete")
def delete_budget(budget_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    period = b.period if b else "monthly"
    if b:
        db.delete(b)
        db.commit()
    return RedirectResponse(f"/budgets?period={period}", status_code=303)


def _limits_context(db: Session, user_id: int, transactions, today: date, A) -> dict:
    pb = period_bounds(today, "monthly")
    rows = []
    scopes = [(None, "Global")] + [(p, PROFILES[p]["name"]) for p in PROFILE_IDS]
    limits_by_scope = {lim.profile: lim for lim in db.query(SpendingLimit).filter(SpendingLimit.user_id == user_id).all()}
    for scope, label in scopes:
        lim = limits_by_scope.get(scope)
        spent_today = sum(t.amount for t in transactions
                          if t.type == "expense" and t.date == today and (scope is None or t.profile == scope))
        spent_month = sum(t.amount for t in transactions
                          if t.type == "expense" and pb["start"] <= t.date <= pb["end"] and (scope is None or t.profile == scope))
        daily = lim.daily if lim else None
        monthly = lim.monthly if lim else None
        rows.append({
            "scope": scope or "", "label": label,
            "daily": daily, "daily_value": daily if daily is not None else "",
            "monthly": monthly, "monthly_value": monthly if monthly is not None else "",
            "daily_remaining": fmt_eur(daily - spent_today) if daily is not None else None,
            "monthly_remaining": fmt_eur(monthly - spent_month) if monthly is not None else None,
            "spent_today_label": fmt_eur(spent_today), "spent_month_label": fmt_eur(spent_month),
        })
    return {"rows": rows}


@router.post("/limits")
def set_limit(scope: str = Form(""), daily: str = Form(""), monthly: str = Form(""),
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = scope if scope in PROFILES else None
    daily_val = float(daily) if daily.strip() else None
    monthly_val = float(monthly) if monthly.strip() else None
    lim = db.query(SpendingLimit).filter(SpendingLimit.user_id == user.id, SpendingLimit.profile == profile).first()
    if daily_val is None and monthly_val is None:
        if lim:
            db.delete(lim)  # limpiar límite
    else:
        if not lim:
            lim = SpendingLimit(user_id=user.id, profile=profile)
            db.add(lim)
        lim.daily = daily_val
        lim.monthly = monthly_val
    db.commit()
    return RedirectResponse("/budgets", status_code=303)
