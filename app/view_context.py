from datetime import date

from sqlalchemy.orm import Session

from app.auth import get_or_create_settings
from app.constants import (
    ACCENT_OPTIONS, BOTTOM_TAB_DEF, DARK_THEME, LIGHT_THEME, MORE_DEF, SIDEBAR_DEF,
)
from app.finance import lighten
from app.models import User
from app.profiles import list_profiles

MESES_LONG = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

MANAGE_IDS = ("profiles", "accounts", "connect", "categories", "budgets", "savings", "goals",
              "debts", "reports", "transactions", "search", "settings")

NAV_ICONS = {
    "overview": "grid", "profiles": "users", "accounts": "wallet", "connect": "bank",
    "categories": "tag", "budgets": "piggy-bank", "savings": "cash", "goals": "target", "debts": "receipt",
    "reports": "chart", "transactions": "list", "search": "search", "settings": "gear",
    "more": "more",
}


def base_context(db: Session, user: User, view: str) -> dict:
    settings = get_or_create_settings(db, user)
    is_dark = settings.theme == "dark"
    theme = DARK_THEME if is_dark else LIGHT_THEME

    def A(hex_color: str) -> str:
        return lighten(hex_color, 0.22) if is_dark else hex_color

    accent = next((a for a in ACCENT_OPTIONS if a["key"] == settings.accent_key), ACCENT_OPTIONS[0])
    accent_hex = A(accent["hex"])
    accent_hex_soft = lighten(accent_hex, 0.28)

    profiles = list_profiles(db, user.id)

    sidebar_items = []
    for n in SIDEBAR_DEF:
        if n["kind"] == "profiles":
            # Perfiles dinámicos desde la BD (editables): usan su punto/icono de color.
            for p in profiles:
                sidebar_items.append({"is_label": False, "id": p.slug, "label": p.name,
                                      "active": view == p.slug, "dot": A(p.color),
                                      "profile_icon": p.icon})
            continue
        if n["kind"] == "label":
            sidebar_items.append({"is_label": True, "label": n["label"]})
            continue
        sidebar_items.append({"is_label": False, "id": n["id"], "label": n["label"],
                              "active": view == n["id"], "nav_icon": NAV_ICONS.get(n["id"], "circle")})

    bottom_tabs = [{"id": n["id"], "label": n["label"], "active": (view == n["id"]),
                    "nav_icon": NAV_ICONS.get(n["id"], "circle")} for n in BOTTOM_TAB_DEF]
    more_items = [{"id": "profiles", "label": "Perfiles", "nav_icon": "users"}]
    more_items += [{"id": p.slug, "label": p.name, "dot": A(p.color), "profile_icon": p.icon} for p in profiles]
    more_items += [{"id": n["id"], "label": n["label"], "nav_icon": NAV_ICONS.get(n["id"], "circle")}
                   for n in MORE_DEF if n["id"] != "profiles"]

    accent_options = [
        {"hex": a["hex"], "key": a["key"], "active": settings.accent_key == a["key"]}
        for a in ACCENT_OPTIONS
    ]

    today = date.today()
    current_date_label = f"{today.day:02d} de {MESES_LONG[today.month - 1]} de {today.year}"

    return {
        "T": theme, "is_dark": is_dark, "A": A,
        "accent_hex": accent_hex, "accent_hex_soft": accent_hex_soft,
        "sidebar_items": sidebar_items, "bottom_tabs": bottom_tabs, "more_items": more_items,
        "accent_options": accent_options, "accent_key": settings.accent_key,
        "view": view, "current_date_label": current_date_label,
        "theme_track_bg": "#12898F" if is_dark else "rgba(33,31,26,0.15)",
        "theme_knob_left": "15px" if is_dark else "2px",
    }
