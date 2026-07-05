PROFILES = {
    "melia": {
        "name": "Meliá",
        "color": "#12898F",
        "income_categories": ["Salario base", "Horas extra", "Bono", "Propinas"],
        "expense_categories": ["Transporte", "Comidas", "Uniforme", "Otros"],
    },
    "realestate": {
        "name": "Real Estate",
        "color": "#D9932E",
        "income_categories": ["Comisión venta", "Comisión alquiler", "Bono de cierre"],
        "expense_categories": ["Marketing", "Gasolina", "Materiales", "Comisión colaborador"],
    },
    "freelance": {
        "name": "Freelance",
        "color": "#3FA65C",
        "income_categories": ["Proyecto branding", "Proyecto web", "Ilustración", "Retainer"],
        "expense_categories": ["Software/Licencias", "Equipo", "Marketing", "Subcontratación"],
    },
    "personal": {
        "name": "Personal",
        "color": "#D3775A",
        "income_categories": ["Ingreso extra", "Regalo", "Reembolso"],
        "expense_categories": ["Compras", "Ocio", "Salud", "Hogar", "Suscripciones"],
    },
}
PROFILE_IDS = ["melia", "realestate", "freelance", "personal"]

SIDEBAR_DEF = [
    {"id": "overview", "label": "Resumen", "kind": "link"},
    {"label": "Perfiles", "kind": "label"},
    {"id": "melia", "label": "Meliá", "kind": "link"},
    {"id": "realestate", "label": "Real Estate", "kind": "link"},
    {"id": "freelance", "label": "Freelance", "kind": "link"},
    {"id": "personal", "label": "Personal", "kind": "link"},
    {"label": "Gestión", "kind": "label"},
    {"id": "accounts", "label": "Cuentas", "kind": "link"},
    {"id": "categories", "label": "Categorías", "kind": "link"},
    {"id": "goals", "label": "Metas", "kind": "link"},
    {"id": "debts", "label": "Deudas y Facturas", "kind": "link"},
    {"id": "reports", "label": "Informes", "kind": "link"},
    {"id": "transactions", "label": "Todos los Movimientos", "kind": "link"},
    {"id": "settings", "label": "Ajustes", "kind": "link"},
]

BOTTOM_TAB_DEF = [
    {"id": "overview", "label": "Resumen"},
    {"id": "debts", "label": "Deudas"},
    {"id": "goals", "label": "Metas"},
    {"id": "transactions", "label": "Movim."},
    {"id": "more", "label": "Más"},
]

MORE_DEF = [
    {"id": "melia", "label": "Meliá"},
    {"id": "realestate", "label": "Real Estate"},
    {"id": "freelance", "label": "Freelance"},
    {"id": "personal", "label": "Personal"},
    {"id": "accounts", "label": "Cuentas"},
    {"id": "categories", "label": "Categorías"},
    {"id": "reports", "label": "Informes"},
    {"id": "settings", "label": "Ajustes"},
]

PROFILE_FILTER_OPTIONS = [
    {"id": "all", "name": "Todos los perfiles"},
    {"id": "melia", "name": "Meliá"},
    {"id": "realestate", "name": "Real Estate"},
    {"id": "freelance", "name": "Freelance"},
    {"id": "personal", "name": "Personal"},
]
TYPE_FILTER_OPTIONS = [
    {"id": "all", "name": "Todos"},
    {"id": "income", "name": "Ingresos"},
    {"id": "expense", "name": "Gastos"},
]

ACCENT_OPTIONS = [
    {"key": "teal", "hex": "#12898F"},
    {"key": "amber", "hex": "#D9932E"},
    {"key": "green", "hex": "#3FA65C"},
    {"key": "terracotta", "hex": "#D3775A"},
    {"key": "plum", "hex": "#6B5B95"},
    {"key": "blue", "hex": "#4A79D9"},
]
CATEGORY_PALETTE = ["#12898F", "#D9932E", "#3FA65C", "#D3775A", "#6B5B95", "#4A79D9", "#C2555B", "#8A8F5C"]
FX_RATES = {"EUR": 1, "USD": 0.92, "GBP": 1.17}
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

LIGHT_THEME = {
    "bg": "#FAF9F6", "card": "#FFFFFF", "ink": "#211F1A", "secondary": "#7A756C", "secondaryAlt": "#57534A",
    "border": "rgba(33,31,26,0.07)", "borderStrong": "rgba(33,31,26,0.1)", "borderInput": "rgba(33,31,26,0.14)",
    "shadow": "0 2px 10px rgba(33,31,26,0.06)", "muted": "#A39C90", "trackBg": "#F0EDE6",
    "solidBtnBg": "#211F1A", "solidBtnColor": "#FAF9F6", "navActiveBg": "#F3F1EA",
}
DARK_THEME = {
    "bg": "#1C1A14", "card": "#252319", "ink": "#F5F1E8", "secondary": "#ABA294", "secondaryAlt": "#C9C0B0",
    "border": "rgba(255,255,255,0.08)", "borderStrong": "rgba(255,255,255,0.12)", "borderInput": "rgba(255,255,255,0.16)",
    "shadow": "0 2px 10px rgba(0,0,0,0.4)", "muted": "#8B8474", "trackBg": "#302C1F",
    "solidBtnBg": "#F5F1E8", "solidBtnColor": "#1C1A14", "navActiveBg": "#26241A",
}

ACCOUNT_TYPE_LABELS = {"cash": "Efectivo", "bank": "Banco", "savings": "Ahorro", "card": "Tarjeta"}
