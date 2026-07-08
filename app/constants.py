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
    {"kind": "profiles"},  # marcador: se expande a los perfiles de la BD (editables)
    {"id": "profiles", "label": "Gestionar perfiles", "kind": "link"},
    {"label": "Gestión", "kind": "label"},
    {"id": "accounts", "label": "Cuentas", "kind": "link"},
    {"id": "connect", "label": "Conectar banco", "kind": "link"},
    {"id": "categories", "label": "Categorías", "kind": "link"},
    {"id": "budgets", "label": "Presupuestos", "kind": "link"},
    {"id": "goals", "label": "Metas", "kind": "link"},
    {"id": "debts", "label": "Deudas y Facturas", "kind": "link"},
    {"id": "reports", "label": "Informes", "kind": "link"},
    {"id": "transactions", "label": "Todos los Movimientos", "kind": "link"},
    {"id": "search", "label": "Buscar", "kind": "link"},
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
    {"id": "profiles", "label": "Perfiles"},
    {"id": "accounts", "label": "Cuentas"},
    {"id": "connect", "label": "Conectar banco"},
    {"id": "categories", "label": "Categorías"},
    {"id": "budgets", "label": "Presupuestos"},
    {"id": "reports", "label": "Informes"},
    {"id": "search", "label": "Buscar"},
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
    "bg": "#F4F2EE", "card": "#FFFFFF", "ink": "#211F1A", "secondary": "#7A756C", "secondaryAlt": "#57534A",
    "border": "rgba(33,31,26,0.05)", "borderStrong": "rgba(33,31,26,0.08)", "borderInput": "rgba(33,31,26,0.12)",
    "shadow": "0 6px 20px rgba(33,31,26,0.07), 0 1px 3px rgba(33,31,26,0.04)", "muted": "#A39C90", "trackBg": "#EFECE5",
    "solidBtnBg": "#211F1A", "solidBtnColor": "#FAF9F6", "navActiveBg": "#F3F1EA", "cardHi": "rgba(255,255,255,0.75)",
}
DARK_THEME = {
    "bg": "#16150F", "card": "#252319", "ink": "#F5F1E8", "secondary": "#ABA294", "secondaryAlt": "#C9C0B0",
    "border": "rgba(255,255,255,0.07)", "borderStrong": "rgba(255,255,255,0.11)", "borderInput": "rgba(255,255,255,0.15)",
    "shadow": "0 8px 24px rgba(0,0,0,0.5), 0 1px 3px rgba(0,0,0,0.35)", "muted": "#8B8474", "trackBg": "#302C1F",
    "solidBtnBg": "#F5F1E8", "solidBtnColor": "#1C1A14", "navActiveBg": "#26241A", "cardHi": "rgba(255,255,255,0.05)",
}

ACCOUNT_TYPE_LABELS = {"cash": "Efectivo", "bank": "Banco", "savings": "Ahorro", "card": "Tarjeta"}

# Bancos disponibles para el flujo de conexión (modo demo hasta configurar un agregador real).
BANKS = [
    {"id": "bbva", "name": "BBVA", "color": "#004481"},
    {"id": "santander", "name": "Santander", "color": "#EC0000"},
    {"id": "caixabank", "name": "CaixaBank", "color": "#007EAE"},
    {"id": "ing", "name": "ING", "color": "#FF6200"},
    {"id": "sabadell", "name": "Banco Sabadell", "color": "#00A0DF"},
    {"id": "bankinter", "name": "Bankinter", "color": "#FF6600"},
    {"id": "openbank", "name": "Openbank", "color": "#E4022B"},
    {"id": "revolut", "name": "Revolut", "color": "#0075EB"},
]
# Agregadores Open Banking soportados (requieren registro + API keys para uso real).
AGGREGATORS = [
    {"id": "tink", "name": "Tink"},
    {"id": "gocardless", "name": "GoCardless"},
    {"id": "truelayer", "name": "TrueLayer"},
]
