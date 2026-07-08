from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.bank_sync import generate_demo_transactions, import_bank_transactions
from app.constants import AGGREGATORS, BANKS
from app.database import get_db
from app.finance import fmt_date_es, fmt_eur
from app.models import Account, BankConnection, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()

BANK_BY_ID = {b["id"]: b for b in BANKS}


@router.get("/connect")
def connect_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "connect")
    conns = (db.query(BankConnection)
             .filter(BankConnection.user_id == user.id, BankConnection.status != "disconnected")
             .order_by(BankConnection.id.desc()).all())
    rows = []
    for c in conns:
        acc = db.get(Account, c.account_id) if c.account_id else None
        rows.append({
            "id": c.id, "bank_name": c.bank_name, "provider": c.provider, "status": c.status,
            "color": BANK_BY_ID.get(c.bank_id, {}).get("color", "#7A756C"),
            "synced_count": c.synced_count or 0,
            "balance": fmt_eur(acc.balance) if acc else "—",
            "last_sync": (c.last_sync.strftime("%d/%m/%Y %H:%M") if c.last_sync else "Nunca"),
        })
    return templates.TemplateResponse(request, "connect.html", {
        **ctx, "banks": BANKS, "aggregators": AGGREGATORS, "connections": rows,
    })


@router.post("/connect/start")
def connect_start(bank_id: str = Form(...), provider: str = Form("demo"),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bank = BANK_BY_ID.get(bank_id)
    if not bank:
        raise HTTPException(status_code=404)
    # Crea la cuenta que recibirá las transacciones sincronizadas y una conexión pendiente.
    account = Account(user_id=user.id, name=bank["name"], type="bank", currency="EUR",
                      balance=0, color=bank["color"])
    db.add(account)
    db.flush()
    conn = BankConnection(user_id=user.id, provider=provider, bank_id=bank_id, bank_name=bank["name"],
                          status="pending", account_id=account.id)
    db.add(conn)
    db.commit()
    # Redirige a la pantalla de consentimiento OAuth simulada.
    return RedirectResponse(f"/connect/consent/{conn.id}", status_code=303)


@router.get("/connect/consent/{conn_id}")
def connect_consent(conn_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = db.query(BankConnection).filter(BankConnection.id == conn_id, BankConnection.user_id == user.id).first()
    if not conn:
        raise HTTPException(status_code=404)
    ctx = base_context(db, user, "connect")
    provider = next((a for a in AGGREGATORS if a["id"] == conn.provider), {"name": "Demo"})
    return templates.TemplateResponse(request, "connect_consent.html", {
        **ctx, "conn": conn, "bank_color": BANK_BY_ID.get(conn.bank_id, {}).get("color", "#12898F"),
        "provider_name": provider["name"],
    })


@router.post("/connect/authorize/{conn_id}")
def connect_authorize(conn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = db.query(BankConnection).filter(BankConnection.id == conn_id, BankConnection.user_id == user.id).first()
    if not conn:
        raise HTTPException(status_code=404)
    conn.status = "connected"
    db.commit()
    # Sincronización inicial en modo demo: importa 10-15 transacciones de ejemplo.
    import_bank_transactions(db, conn, generate_demo_transactions())
    return RedirectResponse("/connect?connected=1", status_code=303)


@router.post("/connect/{conn_id}/sync")
def connect_sync(conn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = db.query(BankConnection).filter(BankConnection.id == conn_id, BankConnection.user_id == user.id,
                                           BankConnection.status == "connected").first()
    if conn:
        import_bank_transactions(db, conn, generate_demo_transactions(n=5))
    return RedirectResponse("/connect", status_code=303)


@router.post("/connect/{conn_id}/disconnect")
def connect_disconnect(conn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = db.query(BankConnection).filter(BankConnection.id == conn_id, BankConnection.user_id == user.id).first()
    if conn:
        conn.status = "disconnected"
        db.commit()
    return RedirectResponse("/connect", status_code=303)


@router.post("/webhooks/bank/{provider}")
async def bank_webhook(provider: str, request: Request, db: Session = Depends(get_db)):
    """Endpoint que recibiría las transacciones sincronizadas de un agregador real.
    Formato esperado: {"connection_id": int, "transactions": [{date, description, amount, category?}]}.
    En producción, verificar aquí la firma del webhook con el secreto del agregador."""
    # secret = request.headers.get("X-Webhook-Secret")  # TODO: validar con el secreto real del agregador
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)
    conn = db.query(BankConnection).filter(BankConnection.id == body.get("connection_id"),
                                           BankConnection.provider == provider).first()
    if not conn:
        return JSONResponse({"error": "connection not found"}, status_code=404)
    imported = import_bank_transactions(db, conn, body.get("transactions", []))
    return JSONResponse({"imported": imported, "connection_id": conn.id})
