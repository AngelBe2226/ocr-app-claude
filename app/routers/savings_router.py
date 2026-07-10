"""Motor de ahorro: por cada ingreso que cuenta (excluye reventa/préstamos) se sugiere
apartar un % para impuestos (IRPF/SS) y otro % para ahorro, por perfil. El usuario
'reserva con un clic' y queda registrado en SavingsReserve (opcionalmente moviendo dinero
a una cuenta de ahorro mediante una transferencia)."""
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.finance import fmt_eur, in_period, parse_anchor, resolve_period, savings_breakdown, PERIOD_OPTIONS
from app.models import Account, Category, SavingsReserve, Transaction, Transfer, User
from app.profiles import list_profiles, profiles_map
from app.seed import get_or_create_global_savings
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


def _reserved_map(db: Session, user_id: int, period_key: str) -> dict:
    """{(profile, kind): amount_reservado} para el periodo dado."""
    out: dict = {}
    rows = db.query(SavingsReserve).filter(
        SavingsReserve.user_id == user_id, SavingsReserve.period_key == period_key
    ).all()
    for r in rows:
        out[(r.profile, r.kind)] = out.get((r.profile, r.kind), 0.0) + r.amount
    return out


@router.get("/savings")
def savings_page(request: Request, period: str = "month", anchor: str = "",
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "savings")
    A = ctx["A"]
    per = resolve_period(period, parse_anchor(anchor))

    profiles = list_profiles(db, user.id)
    categories = db.query(Category).filter(Category.user_id == user.id).all()
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    txs_p = in_period(txs, per["start"], per["end"])

    breakdown = savings_breakdown(profiles, categories, txs_p, per["start"], per["end"])
    reserved = _reserved_map(db, user.id, per["key"])

    rows = []
    tot_target = tot_reserved = tot_pending = 0.0
    for r in breakdown["rows"]:
        res_tax = reserved.get((r["slug"], "tax"), 0.0)
        res_sav = reserved.get((r["slug"], "savings"), 0.0)
        target = r["total"]
        res_total = res_tax + res_sav
        pending = max(0.0, target - res_total)
        tot_target += target
        tot_reserved += res_total
        tot_pending += pending
        rows.append({
            **r,
            "reserved": res_total, "reserved_label": fmt_eur(res_total),
            "pending": pending, "pending_label": fmt_eur(pending),
            "pct_reserved": round(min(1.0, res_total / target) * 100) if target > 0 else 0,
            "has_reserve": res_total > 0.005,
        })

    # Fondo único donde se acumulan todas las reservas + posibles cuentas origen.
    gs = get_or_create_global_savings(db, user.id)
    db.commit()
    all_accounts = db.query(Account).filter(Account.user_id == user.id).all()
    source_accounts = [a for a in all_accounts if a.id != gs.id]

    # Consejo financiero simple: tasa de ahorro efectiva del periodo.
    tot_income = breakdown["income"]
    eff_rate = round((breakdown["total"] / tot_income) * 100) if tot_income > 0 else 0

    return templates.TemplateResponse(request, "savings.html", {
        **ctx, "per": per, "period_options": PERIOD_OPTIONS, "nav_base": "/savings", "nav_extra": "",
        "rows": rows, "breakdown": breakdown,
        "tot_target_label": fmt_eur(tot_target), "tot_reserved_label": fmt_eur(tot_reserved),
        "tot_pending_label": fmt_eur(tot_pending), "tot_pending": tot_pending,
        "tax_total_label": breakdown["tax_label"], "savings_total_label": breakdown["savings_label"],
        "income_total_label": breakdown["income_label"],
        "excluded_names": breakdown["excluded_names"],
        "source_accounts": source_accounts, "eff_rate": eff_rate,
        "fund_name": gs.name, "fund_balance_label": fmt_eur(gs.balance),
        "accent_hex": ctx["accent_hex"],
    })


def _reserve_profile(db: Session, user: User, slug: str, per: dict,
                     fund_id: int, categories, txs_p) -> float:
    """Aparta el pendiente (objetivo - ya reservado) del perfil en el periodo, hacia el
    fondo de ahorro global. Devuelve el importe reservado."""
    profiles = [p for p in list_profiles(db, user.id) if p.slug == slug]
    if not profiles:
        return 0.0
    bd = savings_breakdown(profiles, categories, txs_p, per["start"], per["end"])
    if not bd["rows"]:
        return 0.0
    r = bd["rows"][0]
    reserved = _reserved_map(db, user.id, per["key"])
    pend_tax = max(0.0, r["tax"] - reserved.get((slug, "tax"), 0.0))
    pend_sav = max(0.0, r["savings"] - reserved.get((slug, "savings"), 0.0))
    added = 0.0
    if pend_tax > 0.005:
        db.add(SavingsReserve(user_id=user.id, profile=slug, period_key=per["key"],
                              kind="tax", amount=round(pend_tax, 2), account_id=fund_id))
        added += pend_tax
    if pend_sav > 0.005:
        db.add(SavingsReserve(user_id=user.id, profile=slug, period_key=per["key"],
                              kind="savings", amount=round(pend_sav, 2), account_id=fund_id))
        added += pend_sav
    return added


@router.post("/savings/reserve")
def reserve(profile: str = Form(...), period: str = Form("month"), anchor: str = Form(""),
            from_account_id: str = Form(""),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    per = resolve_period(period, parse_anchor(anchor))
    categories = db.query(Category).filter(Category.user_id == user.id).all()
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    txs_p = in_period(txs, per["start"], per["end"])

    # Destino SIEMPRE el fondo de ahorro global (un único fondo para todos los perfiles).
    fund = get_or_create_global_savings(db, user.id)

    pmap = profiles_map(db, user.id)
    targets = [profile] if profile != "__all__" else list(pmap.keys())
    total_added = 0.0
    for slug in targets:
        if slug in pmap:
            total_added += _reserve_profile(db, user, slug, per, fund.id, categories, txs_p)

    if total_added > 0.005:
        amt = round(total_added, 2)
        # El fondo global crece con lo reservado.
        fund.balance = round(fund.balance + amt, 2)
        # Si se eligió cuenta origen, se mueve el dinero de ahí (transferencia real).
        from_id = int(from_account_id) if from_account_id.strip().isdigit() else None
        if from_id and from_id != fund.id:
            src = db.get(Account, from_id)
            if src and src.user_id == user.id:
                src.balance = round(src.balance - amt, 2)
                db.add(Transfer(user_id=user.id, from_account_id=from_id, to_account_id=fund.id,
                                amount=amt, date=date.today(),
                                note=f"Reserva ahorro/impuestos {per['label']}"))

    db.commit()
    return RedirectResponse(f"/savings?period={per['period']}&anchor={per['anchor']}", status_code=303)


@router.post("/savings/clear")
def clear_reserve(profile: str = Form(...), period: str = Form("month"), anchor: str = Form(""),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    per = resolve_period(period, parse_anchor(anchor))
    q = db.query(SavingsReserve).filter(
        SavingsReserve.user_id == user.id, SavingsReserve.period_key == per["key"]
    )
    if profile != "__all__":
        q = q.filter(SavingsReserve.profile == profile)
    for r in q.all():
        db.delete(r)
    db.commit()
    return RedirectResponse(f"/savings?period={per['period']}&anchor={per['anchor']}", status_code=303)
