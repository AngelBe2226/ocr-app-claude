from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.constants import PROFILE_FILTER_OPTIONS, PROFILES, TYPE_FILTER_OPTIONS
from app.database import get_db
from app.finance import export_csv_bytes, filter_transactions, fmt_eur, totals_for
from app.models import Transaction, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


def _filters_from_request(request: Request) -> dict:
    q = request.query_params
    return {
        "search": q.get("search", ""), "profile": q.get("profile", "all"), "type_": q.get("type", "all"),
        "date_from": q.get("date_from", ""), "date_to": q.get("date_to", ""),
    }


@router.get("/reports")
def reports_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    filters = _filters_from_request(request)
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = filter_transactions(transactions, **filters)
    totals = totals_for(filtered)

    kpis = [
        {"label": "Ingresos (filtro)", "value": fmt_eur(totals["income"]), "color": A("#3FA65C")},
        {"label": "Gastos (filtro)", "value": fmt_eur(totals["expense"]), "color": A("#E2574C")},
        {"label": "Neto (filtro)", "value": fmt_eur(totals["net"]), "color": ctx["accent_hex"]},
    ]
    rows = []
    for t in filtered[:60]:
        rows.append({
            "date_label": t.date, "category": t.category,
            "amount_label": ("+ " if t.type == "income" else "- ") + fmt_eur(t.amount),
            "color": A("#3FA65C" if t.type == "income" else "#E2574C"),
            "profile_name": PROFILES[t.profile]["name"], "profile_color": A(PROFILES[t.profile]["color"]),
            "profile_tint": PROFILES[t.profile]["color"] + "22",
        })

    return templates.TemplateResponse(request, "reports.html", {
        **ctx, "kpis": kpis, "rows": rows, "empty": len(filtered) == 0,
        "filters": {**filters, "type": filters["type_"]},
        "profile_filter_options": PROFILE_FILTER_OPTIONS, "type_filter_options": TYPE_FILTER_OPTIONS,
    })


@router.get("/reports/export.csv")
def export_csv(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    filters = _filters_from_request(request)
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    filtered = filter_transactions(transactions, **filters)
    data = export_csv_bytes(filtered)
    return Response(content=data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=movimientos.csv"})
