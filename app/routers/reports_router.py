from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import category_names
from app.database import get_db
from app.finance import (
    bar_chart, donut_segments, export_csv_bytes, filter_transactions, fmt_eur, hash_color,
    last_n_months, line_chart, month_short_label, monthly_series, net_worth_eur, net_worth_series,
    parse_anchor, resolve_period, savings_breakdown, totals_for,
)
from app.models import Account, Bill, Category, Loan, Transaction, User
from app.pdf import build_report_pdf
from app.profiles import list_profiles, profile_filter_options
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()

REPORT_PERIOD_OPTIONS = [("month", "Mes"), ("week", "Semana"), ("day", "Día"), ("year", "Año"), ("all", "Todo")]

REPORT_CARDS = [
    {"id": "net-worth", "icon": "📈", "title": "Mi Patrimonio Neto", "subtitle": "Tu progresión en el tiempo"},
    {"id": "category", "icon": "🔎", "title": "Análisis por Categoría", "subtitle": "Histórico completo de una categoría"},
    {"id": "top-categories", "icon": "🍩", "title": "Top Categorías", "subtitle": "Dónde gastas o ingresas más"},
    {"id": "subscriptions", "icon": "🔁", "title": "Análisis de Suscripciones", "subtitle": "Gasto en pagos recurrentes"},
    {"id": "projection", "icon": "🔮", "title": "Proyección Anual", "subtitle": "Predicción de tu patrimonio a fin de año"},
    {"id": "income-expense", "icon": "📊", "title": "Ingresos vs Gastos", "subtitle": "Comparativa mensual en barras"},
    {"id": "bills", "icon": "🧾", "title": "Facturas y Suscripciones", "subtitle": "Tus costes fijos mensuales"},
    {"id": "payees", "icon": "🏷️", "title": "Beneficiarios", "subtitle": "Agrupado por nota / a quién pagas"},
    {"id": "tags", "icon": "#", "title": "Etiquetas", "subtitle": "Próximamente"},
]


def _txs(db, user):
    return db.query(Transaction).filter(Transaction.user_id == user.id).all()


@router.get("/reports")
def reports_hub(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    return templates.TemplateResponse(request, "reports.html", {**ctx, "cards": REPORT_CARDS})


@router.get("/reports/analysis")
def report_analysis(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Análisis interactivo estilo Money Manager: navegador de periodo + filtros por
    perfil/categoría/subcategoría/tienda, desglose categoría→subcategoría, top tiendas,
    proyección de fin de periodo y consejos financieros."""
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    q = request.query_params
    focus = "income" if q.get("focus") == "income" else "expense"
    profile = q.get("profile", "all")
    category = q.get("category", "all")
    subcategory = q.get("subcategory", "all")
    store = q.get("store", "all")
    search = q.get("search", "")
    per = resolve_period(q.get("period", "month"), parse_anchor(q.get("anchor", "")))
    date_from = "" if per.get("is_all") else per["start"].isoformat()
    date_to = "" if per.get("is_all") else per["end"].isoformat()

    all_txs = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    # Ámbito: periodo + filtros (sin filtrar por tipo, para que el resumen muestre ambos).
    scope = filter_transactions(all_txs, search=search, profile=profile, type_="all",
                                date_from=date_from, date_to=date_to,
                                category=category, subcategory=subcategory, store=store)
    totals = totals_for(scope)
    focus_txs = [t for t in scope if t.type == focus]

    # Desglose por categoría (del tipo en foco) con subcategorías.
    by_cat: dict[str, float] = {}
    subs_by_cat: dict[str, dict] = {}
    for t in focus_txs:
        by_cat[t.category] = by_cat.get(t.category, 0.0) + t.amount
        sname = (t.subcategory or "").strip() or "· sin subcategoría"
        d = subs_by_cat.setdefault(t.category, {})
        d[sname] = d.get(sname, 0.0) + t.amount
    focus_total = sum(by_cat.values()) or 1
    segs = donut_segments(by_cat)
    for s in segs:
        s["color"] = A(s["color"])
    cat_rows = []
    for name, val in sorted(by_cat.items(), key=lambda e: -e[1]):
        subs = sorted(subs_by_cat.get(name, {}).items(), key=lambda e: -e[1])
        cat_rows.append({
            "name": name, "amount": fmt_eur(val), "raw": val,
            "pct": round(val / focus_total * 100), "pct_width": f"{round(val / focus_total * 100)}%",
            "color": A(hash_color(name)),
            "subs": [{"name": sn, "amount": fmt_eur(sv), "pct": round(sv / val * 100) if val else 0} for sn, sv in subs],
            "has_subs": len(subs) > 1 or (len(subs) == 1 and subs[0][0] != "· sin subcategoría"),
        })

    # Top tiendas (del tipo en foco).
    by_store: dict[str, float] = {}
    for t in focus_txs:
        s = (t.store or "").strip()
        if s:
            by_store[s] = by_store.get(s, 0.0) + t.amount
    store_rows = [{"name": n, "amount": fmt_eur(v), "pct": round(v / focus_total * 100),
                   "pct_width": f"{round(v / focus_total * 100)}%", "color": A(hash_color(n))}
                  for n, v in sorted(by_store.items(), key=lambda e: -e[1])[:8]]

    # Proyección de fin de periodo (solo con sentido en día/semana/mes/año en curso).
    today = date.today()
    is_current = (not per.get("is_all")) and per["start"] <= today <= per["end"]
    days_total = per["days_total"]
    days_elapsed = (today - per["start"]).days + 1 if is_current else days_total
    days_elapsed = max(1, min(days_elapsed, days_total))
    focus_sum = sum(by_cat.values())
    run_rate = focus_sum / days_elapsed
    projected = run_rate * days_total if is_current else focus_sum

    # Consejos de economía (conocimiento financiero).
    tips = _financial_tips(db, user, totals, by_cat, focus, per, run_rate, projected, is_current, days_total)

    kpis = [
        {"label": "Ingresos", "value": fmt_eur(totals["income"]), "color": A("#3FA65C")},
        {"label": "Gastos", "value": fmt_eur(totals["expense"]), "color": A("#E2574C")},
        {"label": "Balance", "value": fmt_eur(totals["net"]),
         "color": A("#3FA65C" if totals["net"] >= 0 else "#E2574C")},
    ]

    # Filtros/navegación: preservar estado.
    nav_extra = "".join(
        f"&{k}={quote(v)}" for k, v in [("focus", focus), ("profile", profile), ("category", category),
                                        ("subcategory", subcategory), ("store", store), ("search", search)]
        if v and v != "all")
    filt_qs = nav_extra + f"&period={per['period']}&anchor={per['anchor']}"

    subcats = sorted({(t.subcategory or "").strip() for t in all_txs if (t.subcategory or "").strip()})
    stores = sorted({(t.store or "").strip() for t in all_txs if (t.store or "").strip()})

    return templates.TemplateResponse(request, "report_analysis.html", {
        **ctx, "per": per, "period_options": REPORT_PERIOD_OPTIONS, "nav_base": "/reports/analysis",
        "nav_extra": nav_extra, "filt_qs": filt_qs, "focus": focus,
        "kpis": kpis, "segs": segs, "cat_rows": cat_rows, "store_rows": store_rows,
        "focus_total_label": fmt_eur(focus_sum), "has_data": bool(by_cat),
        "projected_label": fmt_eur(projected), "run_rate_label": fmt_eur(run_rate),
        "is_current": is_current, "days_elapsed": days_elapsed, "days_total": days_total,
        "tips": tips,
        "filters": {"profile": profile, "category": category, "subcategory": subcategory, "store": store, "search": search},
        "profile_filter_options": profile_filter_options(db, user.id),
        "all_categories": category_names(db, user.id), "subcats": subcats, "stores": stores,
        "accent_hex": ctx["accent_hex"],
    })


def _financial_tips(db, user, totals, by_cat, focus, per, run_rate, projected, is_current, days_total) -> list[dict]:
    tips = []
    income, expense, net = totals["income"], totals["expense"], totals["net"]
    # 1) Tasa de ahorro del periodo vs objetivo 20%.
    if income > 0:
        rate = net / income * 100
        if rate >= 20:
            tips.append({"icon": "🌱", "title": f"Tasa de ahorro {rate:.0f}%",
                         "body": "Por encima del 20% recomendado. Excelente base para tu fondo de emergencia e inversión."})
        elif rate >= 0:
            tips.append({"icon": "🎯", "title": f"Tasa de ahorro {rate:.0f}%",
                         "body": f"El objetivo saludable es 20%. Recorta {fmt_eur((0.20 * income) - net)} más para llegar."})
        else:
            tips.append({"icon": "⚠️", "title": "Gastas más de lo que ingresas",
                         "body": f"Balance negativo de {fmt_eur(net)} este periodo. Revisa tus mayores categorías de gasto."})
    # 2) Regla 50/30/20.
    if income > 0:
        needs = 0.50 * income
        tips.append({"icon": "📐", "title": "Regla 50/30/20",
                     "body": f"Con {fmt_eur(income)} de ingresos: ~{fmt_eur(needs)} necesidades, "
                             f"{fmt_eur(0.30 * income)} deseos y {fmt_eur(0.20 * income)} ahorro/deuda."})
    # 3) Mayor categoría de gasto.
    if by_cat and focus == "expense":
        top_name, top_val = max(by_cat.items(), key=lambda e: e[1])
        share = top_val / sum(by_cat.values()) * 100
        tips.append({"icon": "🔎", "title": f"Mayor gasto: {top_name} ({share:.0f}%)",
                     "body": f"{fmt_eur(top_val)} en {top_name}. Si concentras >35% en una categoría, "
                             "busca alternativas o negocia ese coste."})
    # 4) Proyección de gasto.
    if is_current and focus == "expense" and projected > 0:
        tips.append({"icon": "🔮", "title": f"Proyección: {fmt_eur(projected)}",
                     "body": f"A tu ritmo actual ({fmt_eur(run_rate)}/día) terminarás el periodo con ~{fmt_eur(projected)} de gasto."})
    return tips


@router.get("/reports/analysis/export.pdf")
def export_analysis_pdf(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = request.query_params
    focus = "income" if q.get("focus") == "income" else "expense"
    per = resolve_period(q.get("period", "month"), parse_anchor(q.get("anchor", "")))
    date_from = "" if per.get("is_all") else per["start"].isoformat()
    date_to = "" if per.get("is_all") else per["end"].isoformat()
    all_txs = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    scope = filter_transactions(all_txs, search=q.get("search", ""), profile=q.get("profile", "all"), type_="all",
                                date_from=date_from, date_to=date_to, category=q.get("category", "all"),
                                subcategory=q.get("subcategory", "all"), store=q.get("store", "all"))
    totals = totals_for(scope)
    by_cat: dict[str, float] = {}
    for t in scope:
        if t.type == focus:
            by_cat[t.category] = by_cat.get(t.category, 0.0) + t.amount
    total = sum(by_cat.values()) or 1
    ranked = sorted(by_cat.items(), key=lambda e: -e[1])
    pdf = build_report_pdf(
        f"Análisis · {per['label']}",
        f"{'Gastos' if focus == 'expense' else 'Ingresos'} por categoría",
        kpis=[{"label": "Ingresos", "value": fmt_eur(totals["income"])},
              {"label": "Gastos", "value": fmt_eur(totals["expense"])},
              {"label": "Balance", "value": fmt_eur(totals["net"])}],
        pie={"names": [n for n, _ in ranked[:8]], "values": [v for _, v in ranked[:8]]} if ranked else None,
        table={"columns": ["Categoría", "Importe", "%"],
               "rows": [[n, fmt_eur(v), f"{round(v / total * 100)}%"] for n, v in ranked],
               "right": [1, 2]} if ranked else None)
    return _pdf_response(pdf, f"analisis-{per['period']}.pdf")


@router.get("/reports/net-worth")
def report_net_worth(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()
    transactions = _txs(db, user)
    current = net_worth_eur(accounts, loans)
    months = last_n_months(12)
    series = net_worth_series(current, transactions, months)
    values = [s["value"] for s in series]
    chart = line_chart(values, [s["label"] for s in series])
    kpis = [
        {"label": "Patrimonio actual", "value": fmt_eur(current), "color": ctx["accent_hex"]},
        {"label": "Mínimo (12m)", "value": fmt_eur(min(values)), "color": A("#E2574C")},
        {"label": "Máximo (12m)", "value": fmt_eur(max(values)), "color": A("#3FA65C")},
    ]
    return templates.TemplateResponse(request, "report_line.html", {
        **ctx, "title": "Mi Patrimonio Neto", "subtitle": "Evolución de los últimos 12 meses",
        "kpis": kpis, "chart": chart, "line_color": ctx["accent_hex"], "fill": True,
        "export_href": "/reports/net-worth/export.pdf",
    })


@router.get("/reports/income-expense")
def report_income_expense(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    transactions = _txs(db, user)
    months = last_n_months(12)
    series = monthly_series(transactions, months)
    bars = bar_chart(series)
    tot_inc = sum(s["income"] for s in series)
    tot_exp = sum(s["expense"] for s in series)
    kpis = [
        {"label": "Ingresos (12m)", "value": fmt_eur(tot_inc), "color": A("#3FA65C")},
        {"label": "Gastos (12m)", "value": fmt_eur(tot_exp), "color": A("#E2574C")},
        {"label": "Neto (12m)", "value": fmt_eur(tot_inc - tot_exp), "color": ctx["accent_hex"]},
    ]
    return templates.TemplateResponse(request, "report_bars.html", {
        **ctx, "title": "Ingresos vs Gastos", "subtitle": "Comparativa mensual (12 meses)",
        "kpis": kpis, "bars": bars, "income_color": A("#3FA65C"), "expense_color": A("#E2574C"),
        "export_href": "/reports/income-expense/export.pdf",
    })


@router.get("/reports/top-categories")
def report_top_categories(request: Request, type: str = "expense",
                          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if type not in ("expense", "income"):
        type = "expense"
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    transactions = _txs(db, user)
    by_cat: dict[str, float] = {}
    for t in transactions:
        if t.type == type:
            by_cat[t.category] = by_cat.get(t.category, 0) + t.amount
    segs = donut_segments(by_cat)
    for s in segs:
        s["color"] = A(s["color"])
    total = sum(by_cat.values()) or 1
    ranked = sorted(by_cat.items(), key=lambda e: -e[1])
    rows = [{"name": n, "amount": fmt_eur(v), "pct": round(v / total * 100), "color": A(hash_color(n))}
            for n, v in ranked]
    return templates.TemplateResponse(request, "report_top.html", {
        **ctx, "title": "Top Categorías", "type": type, "segs": segs, "rows": rows,
        "total_label": fmt_eur(sum(by_cat.values())),
        "export_href": f"/reports/top-categories/export.pdf?type={type}",
    })


@router.get("/reports/category")
def report_category(request: Request, name: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    all_cats = category_names(db, user.id)
    if name not in all_cats and all_cats:
        name = all_cats[0]
    transactions = [t for t in _txs(db, user) if t.category == name]
    months = last_n_months(12)
    series = monthly_series(transactions, months)
    values = [s["expense"] + s["income"] for s in series]  # movimiento total del mes en esa categoría
    chart = line_chart(values, [s["label"] for s in series])
    total = sum(values)
    count = len(transactions)
    kpis = [
        {"label": "Total (12m)", "value": fmt_eur(total), "color": ctx["accent_hex"]},
        {"label": "Media mensual", "value": fmt_eur(total / 12), "color": A("#12898F")},
        {"label": "Movimientos", "value": str(count), "color": ctx["T"]["ink"]},
    ]
    return templates.TemplateResponse(request, "report_category.html", {
        **ctx, "title": "Análisis por Categoría", "categories": all_cats, "selected": name,
        "kpis": kpis, "chart": chart, "line_color": A(hash_color(name)) if name else ctx["accent_hex"],
        "export_href": f"/reports/category/export.pdf?name={quote(name)}",
    })


@router.get("/reports/projection")
def report_projection(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()
    transactions = _txs(db, user)
    current = net_worth_eur(accounts, loans)
    series6 = monthly_series(transactions, last_n_months(6))
    avg_net = sum(s["net"] for s in series6) / 6 if series6 else 0
    today = date.today()
    remaining = 12 - today.month
    projected = current + avg_net * remaining
    labels, values = [], []
    for i in range(remaining + 1):
        mm = today.month + i
        yy = today.year + (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        labels.append(month_short_label(date(yy, mm, 1)))
        values.append(current + avg_net * i)
    chart = line_chart(values, labels)
    kpis = [
        {"label": "Patrimonio actual", "value": fmt_eur(current), "color": ctx["accent_hex"]},
        {"label": "Flujo neto medio/mes", "value": fmt_eur(avg_net), "color": A("#3FA65C" if avg_net >= 0 else "#E2574C")},
        {"label": f"Proyección dic {today.year}", "value": fmt_eur(projected), "color": A("#3FA65C" if projected >= current else "#E2574C")},
    ]
    return templates.TemplateResponse(request, "report_line.html", {
        **ctx, "title": "Proyección Anual", "subtitle": f"Estimación de patrimonio a fin de {today.year}",
        "kpis": kpis, "chart": chart, "line_color": ctx["accent_hex"], "fill": True, "dashed": True,
        "export_href": "/reports/projection/export.pdf",
    })


@router.get("/reports/bills")
def report_bills(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    bills = db.query(Bill).filter(Bill.user_id == user.id).order_by(Bill.due_day).all()
    rows = [{"name": b.name, "amount": fmt_eur(b.amount), "due_day": b.due_day,
             "paid": b.paid >= b.amount} for b in bills]
    total = sum(b.amount for b in bills)
    kpis = [
        {"label": "Coste fijo mensual", "value": fmt_eur(total), "color": A("#D9932E")},
        {"label": "Coste anual", "value": fmt_eur(total * 12), "color": ctx["accent_hex"]},
        {"label": "Facturas", "value": str(len(bills)), "color": ctx["T"]["ink"]},
    ]
    return templates.TemplateResponse(request, "report_bills.html", {
        **ctx, "title": "Facturas y Suscripciones", "subtitle": "Costes fijos mensuales", "kpis": kpis, "rows": rows,
        "export_href": "/reports/bills/export.pdf",
    })


@router.get("/reports/subscriptions")
def report_subscriptions(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    bills = db.query(Bill).filter(Bill.user_id == user.id).order_by(Bill.due_day).all()
    transactions = _txs(db, user)
    # Gasto en categorías de tipo suscripción (nombre contiene "suscrip" o "streaming").
    sub_tx = [t for t in transactions if t.type == "expense" and
              any(k in t.category.lower() for k in ("suscrip", "streaming"))]
    sub_total = sum(t.amount for t in sub_tx)
    bill_total = sum(b.amount for b in bills)
    rows = [{"name": b.name, "amount": fmt_eur(b.amount), "due_day": b.due_day} for b in bills]
    kpis = [
        {"label": "Facturas recurrentes/mes", "value": fmt_eur(bill_total), "color": A("#D9932E")},
        {"label": "Gasto en suscripciones", "value": fmt_eur(sub_total), "color": A("#E2574C")},
        {"label": "Total anual estimado", "value": fmt_eur(bill_total * 12 + sub_total), "color": ctx["accent_hex"]},
    ]
    return templates.TemplateResponse(request, "report_bills.html", {
        **ctx, "title": "Análisis de Suscripciones", "subtitle": "Pagos recurrentes y suscripciones",
        "kpis": kpis, "rows": rows, "export_href": "/reports/subscriptions/export.pdf",
    })


@router.get("/reports/payees")
def report_payees(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    A = ctx["A"]
    transactions = _txs(db, user)
    by_payee: dict[str, dict] = {}
    for t in transactions:
        key = (t.note or "").strip() or "(sin nota)"
        d = by_payee.setdefault(key, {"total": 0.0, "count": 0})
        d["total"] += t.amount
        d["count"] += 1
    ranked = sorted(by_payee.items(), key=lambda e: -e[1]["total"])[:40]
    rows = [{"name": n, "amount": fmt_eur(v["total"]), "count": v["count"], "color": A(hash_color(n))}
            for n, v in ranked]
    return templates.TemplateResponse(request, "report_payees.html", {
        **ctx, "title": "Beneficiarios", "subtitle": "Transacciones agrupadas por nota / beneficiario", "rows": rows,
        "export_href": "/reports/payees/export.pdf",
    })


@router.get("/reports/tags")
def report_tags(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "reports")
    return templates.TemplateResponse(request, "report_tags.html", {
        **ctx, "title": "Etiquetas", "subtitle": "Sistema de etiquetas para transacciones",
    })


def _filters_from_request(request: Request) -> dict:
    q = request.query_params
    per = resolve_period(q.get("period", "all"), parse_anchor(q.get("anchor", "")))
    date_from = q.get("date_from", "") or ("" if per.get("is_all") else per["start"].isoformat())
    date_to = q.get("date_to", "") or ("" if per.get("is_all") else per["end"].isoformat())
    return {
        "search": q.get("search", ""), "profile": q.get("profile", "all"), "type_": q.get("type", "all"),
        "date_from": date_from, "date_to": date_to,
        "category": q.get("category", "all"), "subcategory": q.get("subcategory", "all"), "store": q.get("store", "all"),
    }


@router.get("/reports/export.csv")
def export_csv(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    filters = _filters_from_request(request)
    transactions = _txs(db, user)
    filtered = filter_transactions(transactions, **filters)
    data = export_csv_bytes(filtered)
    return Response(content=data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=movimientos.csv"})


def _pdf_response(data: bytes, filename: str) -> Response:
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/reports/{report_id}/export.pdf")
def export_report_pdf(report_id: str, type: str = "expense", name: str = "",
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()
    transactions = _txs(db, user)

    if report_id == "net-worth":
        current = net_worth_eur(accounts, loans)
        series = net_worth_series(current, transactions, last_n_months(12))
        vals = [s["value"] for s in series]
        pdf = build_report_pdf("Mi Patrimonio Neto", "Evolución de los últimos 12 meses",
                               kpis=[{"label": "Actual", "value": fmt_eur(current)},
                                     {"label": "Mínimo", "value": fmt_eur(min(vals))},
                                     {"label": "Máximo", "value": fmt_eur(max(vals))}],
                               line={"values": vals, "labels": [s["label"] for s in series]})
    elif report_id == "income-expense":
        series = monthly_series(transactions, last_n_months(12))
        ti, te = sum(s["income"] for s in series), sum(s["expense"] for s in series)
        pdf = build_report_pdf("Ingresos vs Gastos", "Comparativa mensual (12 meses)",
                               kpis=[{"label": "Ingresos", "value": fmt_eur(ti)},
                                     {"label": "Gastos", "value": fmt_eur(te)},
                                     {"label": "Neto", "value": fmt_eur(ti - te)}],
                               bars=series)
    elif report_id == "top-categories":
        type = "income" if type == "income" else "expense"
        by_cat = {}
        for t in transactions:
            if t.type == type:
                by_cat[t.category] = by_cat.get(t.category, 0) + t.amount
        ranked = sorted(by_cat.items(), key=lambda e: -e[1])[:8]
        total = sum(by_cat.values()) or 1
        pdf = build_report_pdf(f"Top Categorías ({'gastos' if type == 'expense' else 'ingresos'})",
                               f"Total: {fmt_eur(sum(by_cat.values()))}",
                               pie={"names": [n for n, _ in ranked], "values": [v for _, v in ranked]},
                               table={"columns": ["Categoría", "Importe", "%"],
                                      "rows": [[n, fmt_eur(v), f"{round(v / total * 100)}%"] for n, v in ranked],
                                      "right": [1, 2]})
    elif report_id == "category":
        cats = category_names(db, user.id)
        if name not in cats and cats:
            name = cats[0]
        catt = [t for t in transactions if t.category == name]
        series = monthly_series(catt, last_n_months(12))
        vals = [s["income"] + s["expense"] for s in series]
        total = sum(vals)
        pdf = build_report_pdf(f"Categoría · {name}", "Últimos 12 meses",
                               kpis=[{"label": "Total", "value": fmt_eur(total)},
                                     {"label": "Media/mes", "value": fmt_eur(total / 12)},
                                     {"label": "Movimientos", "value": str(len(catt))}],
                               line={"values": vals, "labels": [s["label"] for s in series]})
    elif report_id == "projection":
        current = net_worth_eur(accounts, loans)
        s6 = monthly_series(transactions, last_n_months(6))
        avg = sum(s["net"] for s in s6) / 6 if s6 else 0
        today = date.today()
        rem = 12 - today.month
        labels, vals = [], []
        for i in range(rem + 1):
            mm = today.month + i
            yy = today.year + (mm - 1) // 12
            labels.append(month_short_label(date(yy, (mm - 1) % 12 + 1, 1)))
            vals.append(current + avg * i)
        pdf = build_report_pdf("Proyección Anual", f"Estimación a fin de {today.year}",
                               kpis=[{"label": "Actual", "value": fmt_eur(current)},
                                     {"label": "Flujo medio/mes", "value": fmt_eur(avg)},
                                     {"label": f"Dic {today.year}", "value": fmt_eur(current + avg * rem)}],
                               line={"values": vals, "labels": labels})
    elif report_id in ("bills", "subscriptions"):
        bills = db.query(Bill).filter(Bill.user_id == user.id).order_by(Bill.due_day).all()
        total = sum(b.amount for b in bills)
        pdf = build_report_pdf("Facturas y Suscripciones", "Costes fijos mensuales",
                               kpis=[{"label": "Coste mensual", "value": fmt_eur(total)},
                                     {"label": "Coste anual", "value": fmt_eur(total * 12)},
                                     {"label": "Facturas", "value": str(len(bills))}],
                               table={"columns": ["Factura", "Día", "Importe"],
                                      "rows": [[b.name, str(b.due_day), fmt_eur(b.amount)] for b in bills],
                                      "right": [2]})
    elif report_id == "payees":
        by = {}
        for t in transactions:
            k = (t.note or "").strip() or "(sin nota)"
            d = by.setdefault(k, {"total": 0.0, "count": 0})
            d["total"] += t.amount
            d["count"] += 1
        ranked = sorted(by.items(), key=lambda e: -e[1]["total"])[:40]
        pdf = build_report_pdf("Beneficiarios", "Agrupado por nota / beneficiario",
                               table={"columns": ["Beneficiario", "Nº", "Importe"],
                                      "rows": [[n, str(v["count"]), fmt_eur(v["total"])] for n, v in ranked],
                                      "right": [1, 2]})
    else:
        pdf = build_report_pdf("Reporte", note="Este reporte aún no tiene exportación a PDF.")

    return _pdf_response(pdf, f"reporte-{report_id}.pdf")
