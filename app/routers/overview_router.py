import random
from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.finance import fmt_eur, hash_color, net_worth_eur, period_bounds, ring_dash
from app.models import Account, Budget, Goal, Loan, SpendingLimit, Transaction, User
from app.profiles import pname, profiles_map
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/")
def overview(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "overview")
    A = ctx["A"]

    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()

    cur_key = date.today().strftime("%Y-%m")
    net_worth = net_worth_eur(accounts, loans)
    pmap = profiles_map(db, user.id)

    profile_rings = []
    for pid, prof in pmap.items():
        budgets = db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == pid,
                                          Budget.period == "monthly").all()
        total_budget = sum(b.allocated for b in budgets) or 1
        spent = sum(
            t.amount for t in transactions
            if t.profile == pid and t.type == "expense" and t.date.strftime("%Y-%m") == cur_key
        )
        pct = min(1.0, spent / total_budget)
        profile_rings.append({
            "id": pid, "name": prof.name, "color": A(prof.color),
            "dash": ring_dash(pct), "pct_label": f"{round(pct * 100)}%",
            "spent": fmt_eur(spent), "budget": fmt_eur(total_budget),
        })

    recent = sorted(transactions, key=lambda t: t.date, reverse=True)[:7]
    recent_rows = []
    for t in recent:
        col = hash_color(t.category)
        recent_rows.append({
            "category": t.category, "date_label": t.date,
            "amount_label": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
            "color": A("#3FA65C" if t.type == "income" else "#E2574C"),
            "profile_name": pname(pmap, t.profile), "initial": t.category[0].upper() if t.category else "?",
            "icon_bg": "rgba(255,255,255,0.08)" if ctx["is_dark"] else col + "22", "icon_color": A(col),
        })

    top_goals = []
    for g in goals[:2]:
        pct = min(1.0, g.current / g.target) if g.target else 0
        top_goals.append({"name": g.name, "pct_label": f"{round(pct * 100)}%", "pct_width": f"{round(pct * 100)}%", "color": A(g.color)})

    total_debt = sum(l.balance for l in loans)

    # Límite de gasto global (patrón "Daily Limit"): cuánto queda hoy y este mes.
    today = date.today()
    pb = period_bounds(today, "monthly")
    glimit = db.query(SpendingLimit).filter(SpendingLimit.user_id == user.id, SpendingLimit.profile.is_(None)).first()
    spent_today = sum(t.amount for t in transactions if t.type == "expense" and t.date == today)
    spent_month = sum(t.amount for t in transactions if t.type == "expense" and pb["start"] <= t.date <= pb["end"])
    spend_limit = None
    if glimit and (glimit.daily is not None or glimit.monthly is not None):
        daily_rem = (glimit.daily - spent_today) if glimit.daily is not None else None
        monthly_rem = (glimit.monthly - spent_month) if glimit.monthly is not None else None
        spend_limit = {
            "has_daily": glimit.daily is not None,
            "daily_remaining": fmt_eur(daily_rem) if daily_rem is not None else None,
            "daily_over": (daily_rem is not None and daily_rem < 0),
            "daily_limit": fmt_eur(glimit.daily) if glimit.daily is not None else None,
            "spent_today": fmt_eur(spent_today),
            "has_monthly": glimit.monthly is not None,
            "monthly_remaining": fmt_eur(monthly_rem) if monthly_rem is not None else None,
            "monthly_over": (monthly_rem is not None and monthly_rem < 0),
            "monthly_limit": fmt_eur(glimit.monthly) if glimit.monthly is not None else None,
            "spent_month": fmt_eur(spent_month),
        }

    tips = [
        {"title": "Consejo del día", "body": f"Este mes tus gastos en {recent_rows[0]['category'] if recent_rows else 'ocio'} van por buen camino. Sigue así."},
        {"title": "Redondeo de ahorro", "body": f"Si redondeas cada gasto al euro, podrías ahorrar ~{fmt_eur(random.randint(8, 22))} extra este mes."},
    ]
    tip = tips[date.today().day % len(tips)]

    overview_ctx = {
        "net_worth": fmt_eur(net_worth),
        "net_worth_sub": "Vas bien — sigue así" if net_worth >= 0 else "Cuidado con el saldo negativo",
        "tip": tip,
        "profile_rings": profile_rings,
        "recent": recent_rows,
        "total_debt": fmt_eur(total_debt),
        "goals_count": len(goals),
        "top_goals": top_goals,
    }

    return templates.TemplateResponse(request, "overview.html", {**ctx, "overview": overview_ctx, "spend_limit": spend_limit})
