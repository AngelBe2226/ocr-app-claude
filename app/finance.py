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
                         date_from: str = "", date_to: str = "") -> list:
    out = list(transactions)
    if profile and profile != "all":
        out = [t for t in out if t.profile == profile]
    if type_ and type_ != "all":
        out = [t for t in out if t.type == type_]
    if date_from:
        out = [t for t in out if t.date.isoformat() >= date_from]
    if date_to:
        out = [t for t in out if t.date.isoformat() <= date_to]
    if search:
        q = search.lower()
        out = [t for t in out if q in (t.note or "").lower() or q in (t.category or "").lower()]
    out.sort(key=lambda t: (t.date.isoformat(), t.id), reverse=True)
    return out


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
