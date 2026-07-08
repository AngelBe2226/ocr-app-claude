"""Helpers para trabajar con los perfiles (ahora almacenados en BD, editables)."""
import re
import unicodedata

from sqlalchemy.orm import Session

from app.models import Profile


def list_profiles(db: Session, user_id: int) -> list[Profile]:
    return (db.query(Profile).filter(Profile.user_id == user_id)
            .order_by(Profile.position, Profile.id).all())


def profiles_map(db: Session, user_id: int) -> dict[str, Profile]:
    return {p.slug: p for p in list_profiles(db, user_id)}


def profile_slugs(db: Session, user_id: int) -> list[str]:
    return [p.slug for p in list_profiles(db, user_id)]


def profile_filter_options(db: Session, user_id: int) -> list[dict]:
    opts = [{"id": "all", "name": "Todos los perfiles"}]
    opts += [{"id": p.slug, "name": p.name} for p in list_profiles(db, user_id)]
    return opts


def pname(pmap: dict, slug: str) -> str:
    p = pmap.get(slug)
    return p.name if p else slug


def pcolor(pmap: dict, slug: str) -> str:
    p = pmap.get(slug)
    return p.color if p else "#7A756C"


def slugify(name: str, existing: set[str]) -> str:
    base = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "perfil"
    slug = base
    i = 2
    while slug in existing:
        slug = f"{base}-{i}"
        i += 1
    return slug
