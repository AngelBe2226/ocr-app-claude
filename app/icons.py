"""Paquete de iconos SVG inline (estilo línea, viewBox 24x24, usan currentColor).

CÓMO AÑADIR / CAMBIAR ICONOS
----------------------------
1. Iconos SVG propios: añade una entrada a ICONS con el markup interno del SVG
   (usa currentColor para que herede el color). Ejemplo:
       "mi-icono": '<circle cx="12" cy="12" r="8"/>'
   Aparecerá automáticamente en el selector de iconos de la app.

2. Fuente de iconos (p.ej. exportada de RightFont): declara la @font-face en
   static/custom-icons.css y guarda un valor de icono con el prefijo "font:",
   p.ej. "font:e900". render() lo pinta como <i class="cicon">&#xe900;</i>.
   (El plumbing está listo; solo falta tu archivo de fuente para activarlo.)
"""
from markupsafe import Markup

# Cada valor es el markup interno del SVG. Los trazos usan currentColor;
# los rellenos sólidos llevan fill="currentColor" explícito.
ICONS: dict[str, str] = {
    "circle": '<circle cx="12" cy="12" r="7"/>',
    "shopping-bag": '<path d="M6 7h12l1 13H5L6 7z"/><path d="M9 7a3 3 0 0 1 6 0"/>',
    "shopping-cart": '<circle cx="9" cy="20" r="1.4" fill="currentColor" stroke="none"/><circle cx="18" cy="20" r="1.4" fill="currentColor" stroke="none"/><path d="M2 3h3l2.2 11.2a1 1 0 0 0 1 .8h8.6a1 1 0 0 0 1-.8L20 7H6"/>',
    "home": '<path d="M4 11l8-7 8 7"/><path d="M6 10v9h12v-9"/>',
    "car": '<path d="M3 12l2-5h14l2 5"/><rect x="3" y="12" width="18" height="5" rx="1"/><circle cx="7" cy="17.5" r="1.3" fill="currentColor" stroke="none"/><circle cx="17" cy="17.5" r="1.3" fill="currentColor" stroke="none"/>',
    "bus": '<rect x="4" y="4" width="16" height="13" rx="2"/><path d="M4 11h16M8 17v2M16 17v2"/><circle cx="8" cy="14" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="14" r="1" fill="currentColor" stroke="none"/>',
    "fuel": '<rect x="4" y="4" width="9" height="16" rx="1"/><path d="M13 9h3a2 2 0 0 1 2 2v5a1.5 1.5 0 0 0 3 0V8l-2.5-2.5"/><path d="M6 8h5"/>',
    "coffee": '<path d="M4 8h13v5a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8z"/><path d="M17 9h2a2 2 0 0 1 0 4h-2"/><path d="M7 3v2M11 3v2"/>',
    "utensils": '<path d="M5 3v7a2 2 0 0 0 4 0V3M7 10v11"/><path d="M16 3c-1.5 1-2.5 3-2.5 5.5S15 12 16 12v9"/>',
    "heart": '<path d="M12 20s-7-4.5-7-9.5A3.5 3.5 0 0 1 12 7a3.5 3.5 0 0 1 7 3.5C19 15.5 12 20 12 20z"/>',
    "pill": '<rect x="3" y="9" width="18" height="6" rx="3"/><path d="M12 9v6"/>',
    "dumbbell": '<path d="M2 9v6M6 7v10M18 7v10M22 9v6M6 12h12"/>',
    "plane": '<path d="M2 13l20-6-7 14-3-6-6-2z"/>',
    "gift": '<rect x="4" y="9" width="16" height="11" rx="1"/><path d="M2 9h20M12 9v11"/><path d="M12 9C10 9 8 8 8 6.5S10 5 12 9c0-4 2-2.5 4-2.5S14 9 12 9z"/>',
    "wallet": '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><circle cx="17" cy="14" r="1" fill="currentColor" stroke="none"/>',
    "briefcase": '<rect x="3" y="8" width="18" height="12" rx="2"/><path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "laptop": '<rect x="4" y="5" width="16" height="11" rx="1"/><path d="M2 20h20"/>',
    "palette": '<circle cx="12" cy="12" r="9"/><circle cx="8.5" cy="9" r="1" fill="currentColor" stroke="none"/><circle cx="15.5" cy="9" r="1" fill="currentColor" stroke="none"/><circle cx="9" cy="15" r="1" fill="currentColor" stroke="none"/>',
    "megaphone": '<path d="M3 11v2l13 5V6L3 11z"/><path d="M16 8a4 4 0 0 1 0 8"/>',
    "wrench": '<path d="M14.5 6a4 4 0 0 0-5.3 5.3l-6 6 1.5 1.5 6-6A4 4 0 0 0 18 7.5l-2.3 2.3-1.7-.3-.3-1.7L16 5.5z"/>',
    "shirt": '<path d="M8 3l4 3 4-3 4 4-3 2v11H7V9L4 7z"/>',
    "music": '<circle cx="7" cy="17" r="2"/><circle cx="17" cy="15" r="2"/><path d="M9 17V6l10-2v11"/>',
    "film": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 15h18M8 4v16M16 4v16"/>',
    "gamepad": '<rect x="3" y="8" width="18" height="9" rx="4"/><path d="M8 12v2M7 13h2"/><circle cx="16" cy="12" r="0.8" fill="currentColor" stroke="none"/><circle cx="17.5" cy="14" r="0.8" fill="currentColor" stroke="none"/>',
    "phone": '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',
    "wifi": '<path d="M2 8a15 15 0 0 1 20 0M5 12a10 10 0 0 1 14 0M8.5 15.5a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1" fill="currentColor" stroke="none"/>',
    "credit-card": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18"/>',
    "bank": '<path d="M3 9l9-5 9 5"/><path d="M5 9v9M9 9v9M15 9v9M19 9v9M3 20h18"/>',
    "cash": '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>',
    "piggy-bank": '<path d="M4 13a6 6 0 0 1 6-6h3a6 6 0 0 1 6 6v2h-2l-1 3h-3l-1-2h-1l-1 2H7l-1-3a3 3 0 0 1-2-2z"/><circle cx="15" cy="12" r="1" fill="currentColor" stroke="none"/>',
    "chart": '<path d="M4 4v16h16"/><rect x="7" y="12" width="3" height="5"/><rect x="13" y="8" width="3" height="9"/>',
    "tag": '<path d="M3 3h8l10 10-8 8L3 11V3z"/><circle cx="7.5" cy="7.5" r="1.2" fill="currentColor" stroke="none"/>',
    "bolt": '<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>',
    "leaf": '<path d="M4 20C4 10 12 4 20 4c0 8-6 16-16 16z"/><path d="M4 20C8 14 12 12 18 10"/>',
    "graduation": '<path d="M12 4L2 9l10 5 10-5-10-5z"/><path d="M6 11v4c0 1.5 3 2.5 6 2.5s6-1 6-2.5v-4"/>',
    "paw": '<circle cx="6" cy="11" r="1.6" fill="currentColor" stroke="none"/><circle cx="10" cy="8" r="1.6" fill="currentColor" stroke="none"/><circle cx="14" cy="8" r="1.6" fill="currentColor" stroke="none"/><circle cx="18" cy="11" r="1.6" fill="currentColor" stroke="none"/><path d="M8.5 15a3.5 3.5 0 0 1 7 0 2.6 2.6 0 0 1-2.6 2.6h-1.8A2.6 2.6 0 0 1 8.5 15z" fill="currentColor" stroke="none"/>',
    "receipt": '<path d="M6 2h12v20l-3-2-3 2-3-2-3 2V2z"/><path d="M9 7h6M9 11h6"/>',
    "star": '<path d="M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.2l1-5.8L3.5 9.2l5.9-.9L12 3z"/>',
    "star-favorite": '<path d="M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.2l1-5.8L3.5 9.2l5.9-.9L12 3z" fill="currentColor"/>',
    "building": '<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    # Iconos de navegación (también disponibles en el selector).
    "grid": '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    "users": '<circle cx="9" cy="8" r="3"/><path d="M3.5 20a5.5 5.5 0 0 1 11 0"/><path d="M16 5.5a3 3 0 0 1 0 5.8M20.5 20a5.5 5.5 0 0 0-4-5.3"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
    "list": '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.2" fill="currentColor" stroke="none"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.2 5.2l2.1 2.1M16.7 16.7l2.1 2.1M18.8 5.2l-2.1 2.1M7.3 16.7l-2.1 2.1"/>',
    "more": '<circle cx="5" cy="12" r="1.7" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.7" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1.7" fill="currentColor" stroke="none"/>',
}

ICON_NAMES = list(ICONS.keys())


def render(value: str, size: int = 18) -> Markup:
    """Devuelve el markup del icono para un valor guardado (nombre de la librería,
    'font:XXXX' para fuente propia, emoji/texto, o vacío)."""
    if not value:
        return Markup("")
    if value in ICONS:
        return Markup(
            f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" style="display:block;">{ICONS[value]}</svg>'
        )
    if value.startswith("font:"):
        cp = value.split(":", 1)[1]
        return Markup(f'<i class="cicon" style="font-size:{size}px;font-style:normal;">&#x{cp};</i>')
    # Emoji o texto corto.
    from markupsafe import escape
    return Markup(f'<span style="font-size:{size - 2}px;">{escape(value)}</span>')
