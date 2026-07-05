from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.finance import fmt_eur, hash_color, ring_dash
from app.models import Goal, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/goals")
def goals_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = base_context(db, user, "goals")
    A = ctx["A"]
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.id).all()
    rows = []
    for g in goals:
        pct = min(1.0, g.current / g.target) if g.target else 0
        rows.append({
            "id": g.id, "name": g.name, "color": A(g.color), "raw_color": g.color, "dash": ring_dash(pct),
            "pct_label": f"{round(pct * 100)}%", "current": fmt_eur(g.current), "target": fmt_eur(g.target),
            "target_value": g.target, "target_date": g.target_date,
            "target_date_value": g.target_date.isoformat() if g.target_date else "",
        })
    return templates.TemplateResponse(request, "goals.html", {**ctx, "goals": rows})


@router.post("/goals")
def add_goal(
    name: str = Form(...), target: float = Form(...), target_date: str = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    db.add(Goal(user_id=user.id, name=name, target=target, current=0,
                 target_date=datetime.strptime(target_date, "%Y-%m-%d").date(), color=hash_color(name)))
    db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/edit")
def edit_goal(
    goal_id: int,
    name: str = Form(...), target: float = Form(...), target_date: str = Form(...), color: str = Form(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if g and target and target > 0:
        g.name = name.strip() or g.name
        g.target = target
        g.target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        g.color = color or g.color
        # El % de progreso se recalcula automáticamente al renderizar (current / target).
        db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/delete")
def delete_goal(goal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if g:
        db.delete(g)
        db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/contribute")
def contribute_goal(goal_id: int, amount: float = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if g and amount and amount > 0:
        g.current = round(g.current + amount, 2)
        db.commit()
    return RedirectResponse("/goals", status_code=303)
