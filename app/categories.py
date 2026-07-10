"""Helpers para trabajar con las categorías almacenadas en BD.

Modelo GLOBAL: las categorías son compartidas por todos los perfiles (como Money
Manager). Se guardan con Category.profile = GLOBAL. Cada transacción tiene su propio
perfil y una categoría global; ambos son independientes."""
from sqlalchemy.orm import Session

from app.models import Category

UNCATEGORIZED_NAME = "Sin categoría"
GLOBAL = "_global"  # valor de Category.profile para categorías globales


def list_categories(db: Session, user_id: int, kind: str | None = None):
    q = db.query(Category).filter(Category.user_id == user_id)
    if kind:
        q = q.filter(Category.kind == kind)
    return q.order_by(Category.name).all()


def category_index(db: Session, user_id: int) -> dict:
    """Mapa para resolver icono/color de cada transacción. Clave por (tipo, nombre)
    y también por nombre (fallback), ya que las categorías son globales."""
    idx: dict = {}
    for c in list_categories(db, user_id):
        idx[(c.kind, c.name)] = c
        idx.setdefault(c.name, c)
    return idx


def category_names(db: Session, user_id: int, kind: str | None = None) -> list[str]:
    seen: list[str] = []
    for c in list_categories(db, user_id, kind):
        if c.name not in seen:
            seen.append(c.name)
    return seen


def ensure_uncategorized(db: Session, user_id: int, kind: str) -> Category:
    """Devuelve (creándola si hace falta) la categoría de sistema 'Sin categoría'
    global para un tipo dado. Es donde se reasignan las transacciones al borrar."""
    cat = (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.kind == kind, Category.name == UNCATEGORIZED_NAME)
        .first()
    )
    if not cat:
        cat = Category(user_id=user_id, profile=GLOBAL, kind=kind,
                       name=UNCATEGORIZED_NAME, color="#A39C90", is_system=True)
        db.add(cat)
        db.flush()
    return cat
