from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.finance import amortize, fmt_eur, payoff_date_label, ring_dash
from app.models import Bill, Loan, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/debts")
def debts_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "debts")
    A = ctx["A"]

    loans = db.query(Loan).filter(Loan.user_id == user.id).order_by(Loan.id).all()
    bills = db.query(Bill).filter(Bill.user_id == user.id).order_by(Bill.id).all()

    active_loans, completed_loans = [], []
    active_amorts = []
    for l in loans:
        amort = amortize(l.balance, l.rate, l.payment)
        pct = min(1.0, 1 - (l.balance / l.principal)) if l.principal else 0
        card = {
            "id": l.id, "name": l.name, "balance": fmt_eur(l.balance), "payment": fmt_eur(l.payment),
            "rate": f"{l.rate:.2f}%", "flagged": amort["never_pays_off"],
            "border_color": "rgba(226,87,76,0.4)" if amort["never_pays_off"] else None,
            "ring_color": A("#E2574C" if amort["never_pays_off"] else "#12898F"),
            "dash": ring_dash(pct), "pct_label": f"{round(pct * 100)}%",
            "total_interest": fmt_eur(amort["total_interest"]),
            "payoff_date": payoff_date_label(amort["payoff_month"], amort["never_pays_off"]),
            "raw_principal": l.principal, "raw_balance": l.balance, "raw_rate": l.rate, "raw_payment": l.payment,
        }
        if l.balance <= 0:
            completed_loans.append(card)
        else:
            active_loans.append(card)
            active_amorts.append(amort)

    pending_bills, paid_bills = [], []
    for b in bills:
        pct = min(1.0, b.paid / b.amount) if b.amount else 0
        card = {
            "id": b.id, "name": b.name, "due_day": b.due_day, "paid": fmt_eur(b.paid), "amount": fmt_eur(b.amount),
            "pct_width": f"{round(pct * 100)}%", "bar_color": "#3FA65C" if pct >= 1 else A("#D9932E"),
            "toggle_label": "Marcar como pendiente" if b.paid >= b.amount else "Marcar como pagada",
            "raw_amount": b.amount, "raw_due_day": b.due_day,
        }
        if b.amount and b.paid >= b.amount:
            paid_bills.append(card)
        else:
            pending_bills.append(card)

    total_debt = sum(l.balance for l in loans if l.balance > 0)
    total_payment = sum(l.payment for l in loans if l.balance > 0)
    any_never = any(a["never_pays_off"] for a in active_amorts)
    max_months = max([0] + [a["payoff_month"] or 0 for a in active_amorts if not a["never_pays_off"]])
    if not active_loans:
        debt_free_date = "—"
    elif any_never:
        debt_free_date = "Indeterminado"
    else:
        debt_free_date = payoff_date_label(max_months, False, long=True)

    kpis = [
        {"label": "Deuda pendiente", "value": fmt_eur(total_debt), "color": A("#D9932E")},
        {"label": "Pago mensual total", "value": fmt_eur(total_payment), "color": A("#12898F")},
        {"label": "Préstamos activos", "value": str(len(active_loans)), "color": ctx["T"]["ink"]},
        {"label": "Libre de deudas (est.)", "value": debt_free_date, "color": A("#E2574C" if any_never else "#3FA65C")},
    ]

    completed_count = len(completed_loans) + len(paid_bills)
    return templates.TemplateResponse(request, "debts.html", {
        **ctx, "kpis": kpis, "loans": active_loans, "bills": pending_bills,
        "completed_loans": completed_loans, "paid_bills": paid_bills, "completed_count": completed_count,
    })


@router.post("/loans")
def add_loan(
    name: str = Form(...), principal: float = Form(...), balance: float = Form(...),
    rate: float = Form(...), payment: float = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    db.add(Loan(user_id=user.id, name=name, principal=principal, balance=balance, rate=rate, payment=payment))
    db.commit()
    return RedirectResponse("/debts", status_code=303)


@router.post("/loans/{loan_id}/edit")
def edit_loan(
    loan_id: int,
    name: str = Form(...), principal: float = Form(...), balance: float = Form(...),
    rate: float = Form(...), payment: float = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    l = db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == user.id).first()
    if l:
        l.name = name.strip() or l.name
        l.principal = principal
        l.balance = balance
        l.rate = rate
        l.payment = payment
        db.commit()
    return RedirectResponse("/debts", status_code=303)


@router.post("/loans/{loan_id}/delete")
def delete_loan(loan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    l = db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == user.id).first()
    if l:
        db.delete(l)
        db.commit()
    return RedirectResponse("/debts", status_code=303)


@router.post("/bills")
def add_bill(
    name: str = Form(...), amount: float = Form(...), due_day: int = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    db.add(Bill(user_id=user.id, name=name, amount=amount, due_day=due_day, paid=0))
    db.commit()
    return RedirectResponse("/debts", status_code=303)


@router.post("/bills/{bill_id}/edit")
def edit_bill(
    bill_id: int,
    name: str = Form(...), amount: float = Form(...), due_day: int = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    b = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == user.id).first()
    if b:
        b.name = name.strip() or b.name
        b.amount = amount
        b.due_day = due_day
        # Si ya estaba marcada como pagada, mantenemos el importe pagado alineado al nuevo total.
        if b.paid >= b.amount:
            b.paid = b.amount
        db.commit()
    return RedirectResponse("/debts", status_code=303)


@router.post("/bills/{bill_id}/toggle")
def toggle_bill(bill_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == user.id).first()
    if b:
        b.paid = 0 if b.paid >= b.amount else b.amount
        db.commit()
    return RedirectResponse("/debts", status_code=303)
