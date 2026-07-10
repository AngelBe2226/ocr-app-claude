import csv
import io
import json
import math
from datetime import date, datetime, timedelta

from app.constants import CATEGORY_PALETTE, FX_RATES, MESES, PROFILES

MESES_LONG = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def fmt_eur(n: float) -> str:
    v = round((n or 0) * 100) / 100
    sign = "-" if v < 0 else ""
    abs_str = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{abs_str} €"


def fmt_money(n: float, currency: str) -> str:
    symbols = {"EUR": "€", "USD": "$", "GBP": "£"}
    v = round((n or 0) * 100) / 100
    sign = "-" if v < 0 else ""
    abs_str = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{abs_str} {symbols.get(currency, currency)}"


def fmt_date_es(d: date) -> str:
    if d is None:
        return ""
    return f"{d.day:02d} {MESES[d.month - 1].lower()} {d.year}"


def today_iso() -> date:
    return date.today()


def last_n_months(n: int, anchor: date | None = None) -> list[date]:
    anchor = anchor or date.today()
    out = []
    y, m = anchor.year, anchor.month
    for i in range(n - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        out.append(date(yy, mm, 1))
    return out


def month_short_label(d: date) -> str:
    return f"{MESES[d.month - 1]} '{str(d.year)[2:]}"


def hash_color(s: str) -> str:
    h = sum(ord(c) for c in s)
    return CATEGORY_PALETTE[h % len(CATEGORY_PALETTE)]


def lighten(hex_color: str, amt: float) -> str:
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    nr = round(r + (255 - r) * amt)
    ng = round(g + (255 - g) * amt)
    nb = round(b + (255 - b) * amt)
    return f"#{nr:02x}{ng:02x}{nb:02x}"


def amortize(principal_balance: float, rate_pct: float, payment: float) -> dict:
    """Monthly-compounding amortization. Mirrors the prototype's amortize()."""
    r = (rate_pct / 100) / 12
    bal = principal_balance
    interest_first = bal * r
    never_pays_off = payment <= interest_first
    horizon = 24 if never_pays_off else 360
    months = 0
    total_interest = 0.0
    payoff_month = None
    while bal > 0 and months < horizon:
        interest = bal * r
        total_interest += interest
        bal = bal + interest - payment
        months += 1
        if bal < 0:
            bal = 0
        if bal <= 0 and payoff_month is None:
            payoff_month = months
    return {"payoff_month": payoff_month, "never_pays_off": never_pays_off, "total_interest": total_interest}


def net_worth_eur(accounts, loans) -> float:
    total = sum(a.balance * FX_RATES.get(a.currency, 1) for a in accounts)
    total -= sum(l.balance for l in loans)
    return total


def totals_for(transactions) -> dict:
    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")
    return {"income": income, "expense": expense, "net": income - expense}


def monthly_series(transactions, months: list[date]) -> list[dict]:
    out = []
    for m in months:
        key = f"{m.year}-{m.month:02d}"
        in_month = [t for t in transactions if t.date.strftime("%Y-%m") == key]
        income = sum(t.amount for t in in_month if t.type == "income")
        expense = sum(t.amount for t in in_month if t.type == "expense")
        out.append({"label": month_short_label(m), "income": income, "expense": expense, "net": income - expense})
    return out


def donut_segments(expense_by_cat: dict, r: float = 60) -> list[dict]:
    entries = sorted(expense_by_cat.items(), key=lambda e: -e[1])
    total = sum(v for _, v in entries) or 1
    circumference = 2 * math.pi * r
    cumulative = 0.0
    segs = []
    for name, val in entries:
        frac = val / total
        segs.append({
            "name": name, "pct": round(frac * 100), "color": hash_color(name),
            "dash": f"{frac * circumference} {circumference}",
            "offset": -cumulative * circumference,
        })
        cumulative += frac
    return segs


def ring_dash(pct: float, r: float = 30) -> str:
    pct = max(0.0, min(1.0, pct))
    circumference = 2 * math.pi * r
    return f"{pct * circumference} {circumference}"


def budget_rows(profile_id: str, budgets, transactions, cur_key: str, months3_keys: list[str]) -> list[dict]:
    rows = []
    for b in budgets:
        spent = sum(
            t.amount for t in transactions
            if t.profile == profile_id and t.type == "expense" and t.category == b.category
            and t.date.strftime("%Y-%m") == cur_key
        )
        pct = min(1.0, spent / (b.allocated or 1))
        past = [
            t for t in transactions
            if t.profile == profile_id and t.type == "expense" and t.category == b.category
            and t.date.strftime("%Y-%m") in months3_keys
        ]
        avg = (sum(t.amount for t in past) / 3) if past else 0.0
        has_suggestion = avg > 0 and abs(avg - b.allocated) > 5
        rows.append({
            "category": b.category, "allocated": b.allocated, "spent": spent,
            "pct": pct, "pct_width": f"{round(pct * 100)}%",
            "over": pct >= 1, "has_suggestion": has_suggestion, "suggestion": avg,
        })
    return rows


def filter_transactions(transactions, search: str = "", profile: str = "all", type_: str = "all",
                        account_id: str = "all", date_from: str = "", date_to: str = "",
                        category: str = "all", subcategory: str = "all", store: str = "all") -> list:
    out = list(transactions)
    if profile and profile != "all":
        out = [t for t in out if t.profile == profile]
    if type_ and type_ != "all":
        out = [t for t in out if t.type == type_]
    if account_id and account_id != "all":
        out = [t for t in out if str(t.account_id) == str(account_id)]
    if category and category != "all":
        out = [t for t in out if t.category == category]
    if subcategory and subcategory != "all":
        out = [t for t in out if (t.subcategory or "") == subcategory]
    if store and store != "all":
        out = [t for t in out if (t.store or "") == store]
    if date_from:
        out = [t for t in out if t.date.isoformat() >= date_from]
    if date_to:
        out = [t for t in out if t.date.isoformat() <= date_to]
    if search:
        q = search.lower()
        def matches(t):
            acc = (t.account.name if t.account else "")
            haystack = " ".join([(t.note or ""), (t.category or ""), (t.subcategory or ""), (t.store or ""),
                                 acc, f"{t.amount:.2f}", str(t.amount)]).lower()
            return q in haystack
        out = [t for t in out if matches(t)]
    out.sort(key=lambda t: (t.date.isoformat(), t.id), reverse=True)
    return out


def month_groups(rows: list[dict]) -> list[dict]:
    """Agrupa filas de transacciones (dicts con 'date' y 'signed') por mes, en orden
    descendente, con etiqueta en español y total neto del mes."""
    groups: list[dict] = []
    current = None
    for r in rows:
        d = r["date"]
        key = (d.year, d.month)
        if current is None or current["key"] != key:
            label = f"{MESES_LONG[d.month - 1].capitalize()} {d.year}"
            current = {"key": key, "label": label, "rows": [], "total": 0.0}
            groups.append(current)
        current["rows"].append(r)
        current["total"] += r.get("signed", 0.0)
    for g in groups:
        g["count"] = len(g["rows"])
        g["total_label"] = fmt_eur(g["total"])
    return groups


def export_csv_bytes(rows) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Fecha", "Perfil", "Categoria", "Nota", "Tipo", "Importe"])
    for t in rows:
        profile_name = PROFILES.get(t.profile, {}).get("name", t.profile)
        writer.writerow([t.date.isoformat(), profile_name, t.category, (t.note or "").replace(",", ";"), t.type, t.amount])
    return buf.getvalue().encode("utf-8")


def export_backup_json(accounts, transactions, loans, bills, goals, budgets) -> bytes:
    def ser(obj, fields):
        return {f: (getattr(obj, f).isoformat() if isinstance(getattr(obj, f), date) else getattr(obj, f)) for f in fields}

    data = {
        "accounts": [ser(a, ["id", "name", "type", "currency", "balance", "color", "cycle_end", "due_date"]) for a in accounts],
        "transactions": [ser(t, ["id", "profile", "type", "category", "amount", "date", "note", "account_id", "attachment_name"]) for t in transactions],
        "loans": [ser(l, ["id", "name", "principal", "balance", "rate", "payment"]) for l in loans],
        "bills": [ser(b, ["id", "name", "amount", "due_day", "paid"]) for b in bills],
        "goals": [ser(g, ["id", "name", "target", "current", "target_date", "color"]) for g in goals],
        "budgets": [ser(b, ["id", "profile", "category", "allocated", "rollover"]) for b in budgets],
    }
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


def period_bounds(today: date, period: str) -> dict:
    """Devuelve los límites del periodo (mensual o anual) para calcular presupuestos:
    inicio, fin, días totales y días restantes."""
    if period == "annual":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
        days_total = (end - start).days + 1
        days_remaining = (end - today).days
        label = str(today.year)
    else:  # monthly
        import calendar as _cal
        last = _cal.monthrange(today.year, today.month)[1]
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month, last)
        days_total = last
        days_remaining = last - today.day
        label = f"{MESES[today.month - 1]} {today.year}"
    return {"start": start, "end": end, "days_total": days_total,
            "days_remaining": max(0, days_remaining), "label": label}


def _shift_month(d: date, delta: int) -> date:
    y = d.year + (d.month - 1 + delta) // 12
    m = (d.month - 1 + delta) % 12 + 1
    import calendar as _cal
    return date(y, m, min(d.day, _cal.monthrange(y, m)[1]))


def parse_anchor(anchor_iso: str | None) -> date:
    try:
        return date.fromisoformat(anchor_iso) if anchor_iso else date.today()
    except (ValueError, TypeError):
        return date.today()


def resolve_period(period: str, anchor: date | None = None) -> dict:
    """Rango de tiempo navegable estilo Money Manager: day / week / month / year.
    Devuelve inicio, fin, etiqueta es-ES, y anclas prev/next para navegar con ‹ ›."""
    import calendar as _cal
    anchor = anchor or date.today()
    if period == "all":
        start, end = date(1970, 1, 1), date(2100, 12, 31)
        a = anchor.isoformat()
        return {"period": "all", "start": start, "end": end, "label": "Todo el histórico",
                "key": "all", "anchor": a, "prev": a, "next": a, "is_all": True,
                "days_total": (end - start).days + 1, "days_elapsed": 1}
    if period == "day":
        start = end = anchor
        label = fmt_date_es(anchor)
        prev, nxt = anchor - timedelta(days=1), anchor + timedelta(days=1)
        key = anchor.isoformat()
    elif period == "week":
        start = anchor - timedelta(days=anchor.weekday())  # lunes
        end = start + timedelta(days=6)
        if start.month == end.month:
            label = f"{start.day}–{end.day} {MESES[end.month - 1]} {end.year}"
        else:
            label = f"{start.day} {MESES[start.month - 1][:3]} – {end.day} {MESES[end.month - 1][:3]} {end.year}"
        prev, nxt = start - timedelta(days=7), start + timedelta(days=7)
        key = f"{start.year}-W{start.isocalendar().week:02d}"
    elif period == "year":
        start, end = date(anchor.year, 1, 1), date(anchor.year, 12, 31)
        label = str(anchor.year)
        prev, nxt = date(anchor.year - 1, 1, 1), date(anchor.year + 1, 1, 1)
        key = str(anchor.year)
    else:  # month (por defecto)
        period = "month"
        last = _cal.monthrange(anchor.year, anchor.month)[1]
        start, end = date(anchor.year, anchor.month, 1), date(anchor.year, anchor.month, last)
        label = f"{MESES[anchor.month - 1]} {anchor.year}"
        prev, nxt = _shift_month(start, -1), _shift_month(start, 1)
        key = f"{anchor.year}-{anchor.month:02d}"
    return {
        "period": period, "start": start, "end": end, "label": label, "key": key,
        "anchor": anchor.isoformat(), "prev": prev.isoformat(), "next": nxt.isoformat(),
        "days_total": (end - start).days + 1,
        "days_elapsed": max(1, min((date.today() - start).days + 1, (end - start).days + 1)),
    }


PERIOD_OPTIONS = [("day", "Día"), ("week", "Semana"), ("month", "Mes"), ("year", "Año")]


def in_period(transactions, start: date, end: date) -> list:
    return [t for t in transactions if start <= t.date <= end]


def savings_breakdown(profiles, categories, transactions, start: date, end: date) -> dict:
    """Por cada perfil, calcula el ingreso que SÍ cuenta para el ahorro (excluye las
    categorías de ingreso marcadas como no-computables: reventa, préstamos) y aplica
    tax_rate (impuestos IRPF/SS) y savings_rate (ahorro) del perfil."""
    excluded = {(c.profile, c.name) for c in categories
                if c.kind == "income" and not c.counts_for_savings}
    rows = []
    tot_income = tot_tax = tot_savings = 0.0
    for p in profiles:
        qualifying = sum(
            t.amount for t in transactions
            if t.profile == p.slug and t.type == "income" and start <= t.date <= end
            and (p.slug, t.category) not in excluded
        )
        tax = qualifying * (p.tax_rate or 0) / 100.0
        sav = qualifying * (p.savings_rate or 0) / 100.0
        if qualifying <= 0 and (p.savings_rate or 0) == 0 and (p.tax_rate or 0) == 0:
            continue
        rows.append({
            "slug": p.slug, "name": p.name, "color": p.color,
            "income": qualifying, "income_label": fmt_eur(qualifying),
            "tax_rate": p.tax_rate or 0, "savings_rate": p.savings_rate or 0,
            "tax": tax, "tax_label": fmt_eur(tax),
            "savings": sav, "savings_label": fmt_eur(sav),
            "total": tax + sav, "total_label": fmt_eur(tax + sav),
        })
        tot_income += qualifying
        tot_tax += tax
        tot_savings += sav
    return {
        "rows": rows,
        "income": tot_income, "income_label": fmt_eur(tot_income),
        "tax": tot_tax, "tax_label": fmt_eur(tot_tax),
        "savings": tot_savings, "savings_label": fmt_eur(tot_savings),
        "total": tot_tax + tot_savings, "total_label": fmt_eur(tot_tax + tot_savings),
        "excluded_names": sorted({c.name for c in categories if c.kind == "income" and not c.counts_for_savings}),
    }


def spent_in_period(transactions, profile: str, category: str, start: date, end: date) -> float:
    return sum(
        t.amount for t in transactions
        if t.profile == profile and t.type == "expense" and t.category == category
        and start <= t.date <= end
    )


def net_worth_series(current_net: float, transactions, months: list[date]) -> list[dict]:
    """Serie aproximada de patrimonio neto por mes: como los saldos son manuales
    (no derivados de transacciones), reconstruimos el histórico restando al neto
    actual los flujos de transacciones posteriores al fin de cada mes."""
    import calendar as _cal
    out = []
    for m in months:
        last = _cal.monthrange(m.year, m.month)[1]
        month_end = date(m.year, m.month, last)
        flow_after = sum((t.amount if t.type == "income" else -t.amount)
                         for t in transactions if t.date > month_end)
        out.append({"label": month_short_label(m), "value": current_net - flow_after})
    return out


def line_chart(values: list[float], labels: list[str], width: float = 560, height: float = 120,
               x0: float = 20, y0: float = 15) -> dict:
    n = len(values)
    lo = min([0.0] + list(values))
    hi = max([1.0] + list(values))
    rng = (hi - lo) or 1
    dots = []
    for i, (v, lab) in enumerate(zip(values, labels)):
        x = (i / (n - 1 if n > 1 else 1)) * width + x0
        y = (y0 + height) - ((v - lo) / rng) * height
        dots.append({"x": round(x, 1), "y": round(y, 1), "label": lab, "value": v})
    return {"points": " ".join(f"{d['x']},{d['y']}" for d in dots), "dots": dots}


def bar_chart(series: list[dict], width: float = 560, height: float = 120,
              x0: float = 20, y0: float = 15) -> list[dict]:
    """series: [{label, income, expense}]. Devuelve geometría de barras income/expense."""
    maxv = max([1.0] + [max(s["income"], s["expense"]) for s in series])
    n = max(1, len(series))
    slot = width / n
    bw = min(18, slot * 0.28)
    bars = []
    for i, s in enumerate(series):
        cx = x0 + i * slot + slot / 2
        ih = (s["income"] / maxv) * height
        eh = (s["expense"] / maxv) * height
        bars.append({
            "label": s["label"],
            "ix": round(cx - bw - 1, 1), "iy": round(y0 + height - ih, 1), "ih": round(ih, 1),
            "ex": round(cx + 1, 1), "ey": round(y0 + height - eh, 1), "eh": round(eh, 1),
            "w": round(bw, 1), "labelx": round(cx, 1),
        })
    return bars


def payoff_date_label(payoff_month: int | None, never_pays_off: bool, long: bool = False) -> str:
    if never_pays_off:
        return "Indeterminado"
    if payoff_month is None:
        return "Indeterminado"
    d = date.today()
    y, m = d.year, d.month + payoff_month
    while m > 12:
        m -= 12
        y += 1
    if long:
        return f"{MESES_LONG[m - 1]} de {y}"
    return f"{MESES[m - 1].lower()} {y}"
