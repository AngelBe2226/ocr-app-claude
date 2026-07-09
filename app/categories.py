"""Helpers para trabajar con las categorías almacenadas en BD."""
from sqlalchemy.orm import Session

from app.models import Category

UNCATEGORIZED_NAME = "Sin categoría"


def list_categories(db: Session, user_id: int, profile: str | None = None, kind: str | None = None):
    q = db.query(Category).filter(Category.user_id == user_id)
    if profile:
        q = q.filter(Category.profile == profile)
    if kind:
        q = q.filter(Category.kind == kind)
    return q.order_by(Category.name).all()


def category_index(db: Session, user_id: int) -> dict:
    """Mapa (perfil, nombre) -> Category, para resolver icono/color de cada transacción."""
    return {(c.profile, c.name): c for c in list_categories(db, user_id)}


def category_names(db: Session, user_id: int, profile: str | None = None, kind: str | None = None) -> list[str]:
    seen: list[str] = []
    for c in list_categories(db, user_id, profile, kind):
        if c.name not in seen:
            seen.append(c.name)
    return seen


def ensure_uncategorized(db: Session, user_id: int, profile: str, kind: str) -> Category:
    """Devuelve (creándola si hace falta) la categoría de sistema 'Sin categoría'
    para un perfil y tipo dados. Es donde se reasignan las transacciones al borrar."""
    cat = (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.profile == profile,
                Category.kind == kind, Category.name == UNCATEGORIZED_NAME)
        .first()
    )
    if not cat:
        cat = Category(user_id=user_id, profile=profile, kind=kind,
                       name=UNCATEGORIZED_NAME, color="#A39C90", is_system=True)
        db.add(cat)
        db.flush()
    return cat
