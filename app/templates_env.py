import time
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.finance import fmt_date_es, fmt_eur, fmt_money

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["eur"] = fmt_eur
templates.env.filters["money"] = fmt_money
templates.env.filters["date_es"] = fmt_date_es
templates.env.globals["static_version"] = str(int(time.time()))
