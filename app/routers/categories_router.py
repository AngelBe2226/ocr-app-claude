from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.categories import UNCATEGORIZED_NAME, ensure_uncategorized, list_categories
from app.constants import PROFILE_IDS, PROFILES
from app.database import get_db
from app.finance import hash_color
from app.models import Budget, Category, Subcategory, Transaction, User
from app.templates_env import templates
from app.view_context import base_context

router = APIRouter()


@router.get("/categories")
def categories_page(request: Request, kind: str = "expense",
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if kind not in ("income", "expense"):
        kind = "expense"
    ctx = base_context(db, user, "categories")
    A = ctx["A"]

    cats = list_categories(db, user.id, kind=kind)
    # Cuenta de transacciones por categoría (perfil + nombre) para avisar al borrar.
    tx_counts: dict[tuple[str, str], int] = {}
    for t in db.query(Transaction).filter(Transaction.user_id == user.id).all():
        key = (t.profile, t.category)
        tx_counts[key] = tx_counts.get(key, 0) + 1

    groups = []
    for pid in PROFILE_IDS:
        rows = []
        for c in [c for c in cats if c.profile == pid]:
            rows.append({
                "id": c.id, "name": c.name, "icon": c.icon or c.name[0].upper(),
                "color": A(c.color), "raw_color": c.color, "is_system": c.is_system,
                "tx_count": tx_counts.get((pid, c.name), 0),
                "subcategories": [{"id": s.id, "name": s.name, "icon": s.icon} for s in c.subcategories],
            })
        if rows:
            groups.append({"profile": pid, "name": PROFILES[pid]["name"], "color": A(PROFILES[pid]["color"]), "categories": rows})

    return templates.TemplateResponse(request, "categories.html", {
        **ctx, "kind": kind, "groups": groups,
        "profiles": [{"id": p, "name": PROFILES[p]["name"]} for p in PROFILE_IDS],
    })


@router.post("/categories")
def add_category(kind: str = Form(...), profile: str = Form(...), name: str = Form(...),
                 icon: str = Form(""), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = name.strip()
    if name and profile in PROFILES and kind in ("income", "expense"):
        exists = (db.query(Category)
                  .filter(Category.user_id == user.id, Category.profile == profile,
                          Category.kind == kind, Category.name == name).first())
        if not exists:
            db.add(Category(user_id=user.id, profile=profile, kind=kind, name=name,
                            icon=icon.strip(), color=hash_color(name)))
            db.commit()
    return RedirectResponse(f"/categories?kind={kind}", status_code=303)


@router.post("/categories/{category_id}/rename")
def rename_category(category_id: int, name: str = Form(...), color: str = Form(...), icon: str = Form(""),
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    if c and not c.is_system:
        new_name = name.strip()
        if new_name and new_name != c.name:
            old_name = c.name
            # Propaga el cambio de nombre al histórico y a los presupuestos del mismo perfil.
            db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.profile == c.profile,
                                         Transaction.category == old_name).update({"category": new_name}, synchronize_session=False)
            db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == c.profile,
                                    Budget.category == old_name).update({"category": new_name}, synchronize_session=False)
            c.name = new_name
        c.color = color or c.color
        c.icon = icon.strip()
        db.commit()
    return RedirectResponse(f"/categories?kind={c.kind if c else 'expense'}", status_code=303)


@router.post("/categories/{category_id}/delete")
def delete_category(category_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    kind = c.kind if c else "expense"
    if c and not c.is_system:
        # Reasigna las transacciones existentes a "Sin categoría" en vez de borrarlas.
        uncategorized = ensure_uncategorized(db, user.id, c.profile, c.kind)
        db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.profile == c.profile,
                                     Transaction.category == c.name).update({"category": uncategorized.name}, synchronize_session=False)
        # Los presupuestos ligados a esta categoría se eliminan (la asignación deja de tener sentido).
        db.query(Budget).filter(Budget.user_id == user.id, Budget.profile == c.profile,
                                Budget.category == c.name).delete(synchronize_session=False)
        db.delete(c)
        db.commit()
    return RedirectResponse(f"/categories?kind={kind}", status_code=303)


@router.post("/categories/{category_id}/subcategories")
def add_subcategory(category_id: int, name: str = Form(...), icon: str = Form(""),
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Category).filter(Category.id == category_id, Category.user_id == user.id).first()
    if c and name.strip():
        db.add(Subcategory(category_id=c.id, name=name.strip(), icon=icon.strip()))
        db.commit()
    return RedirectResponse(f"/categories?kind={c.kind if c else 'expense'}", status_code=303)


@router.post("/subcategories/{sub_id}/rename")
def rename_subcategory(sub_id: int, name: str = Form(...), icon: str = Form(""),
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = (db.query(Subcategory).join(Category)
         .filter(Subcategory.id == sub_id, Category.user_id == user.id).first())
    kind = "expense"
    if s and name.strip():
        s.name = name.strip()
        s.icon = icon.strip()
        kind = s.category.kind
        db.commit()
    return RedirectResponse(f"/categories?kind={kind}", status_code=303)


@router.post("/subcategories/{sub_id}/delete")
def delete_subcategory(sub_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = (db.query(Subcategory).join(Category)
         .filter(Subcategory.id == sub_id, Category.user_id == user.id).first())
    kind = s.category.kind if s else "expense"
    if s:
        db.delete(s)
        db.commit()
    return RedirectResponse(f"/categories?kind={kind}", status_code=303)
