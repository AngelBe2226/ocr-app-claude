"""Tipos de cambio en vivo (Frankfurter, datos del BCE, sin API key).

Convierte a EUR: rates[cur] = cuántos EUR vale 1 unidad de 'cur'. Cachea en memoria
y en disco (TTL 6 h) y, si no hay red, usa las tasas fijas de constants.FX_RATES como
respaldo. Nunca lanza excepción: siempre devuelve un mapa de tasas usable."""
import json
import time
import urllib.request
from pathlib import Path

from app.constants import FX_RATES

CACHE_FILE = Path(__file__).resolve().parent.parent / "fx_cache.json"
TTL_SECONDS = 6 * 3600
CURRENCIES = ["USD", "GBP", "CHF", "JPY", "MXN", "COP", "CUP"]  # además de EUR (base)
_mem = {"ts": 0.0, "rates": None, "date": None, "live": False}


def _load_disk():
    try:
        d = json.loads(CACHE_FILE.read_text())
        return float(d.get("ts", 0)), d.get("rates"), d.get("date")
    except Exception:
        return 0.0, None, None


def _save_disk(ts, rates, date):
    try:
        CACHE_FILE.write_text(json.dumps({"ts": ts, "rates": rates, "date": date}))
    except Exception:
        pass


def _fetch():
    url = "https://api.frankfurter.app/latest?from=EUR&to=" + ",".join(CURRENCIES)
    req = urllib.request.Request(url, headers={"User-Agent": "MyMoney/1.0"})
    with urllib.request.urlopen(req, timeout=4) as r:
        data = json.loads(r.read().decode())
    rates = {"EUR": 1.0}
    for cur, eur_to_cur in (data.get("rates") or {}).items():
        if eur_to_cur:
            rates[cur] = round(1.0 / eur_to_cur, 6)  # EUR por 1 unidad de 'cur'
    return rates, data.get("date")


def get_rates(force: bool = False) -> dict:
    now = time.time()
    if not force and _mem["rates"] and now - _mem["ts"] < TTL_SECONDS:
        return _mem["rates"]
    # Cargar de disco si aún no está en memoria.
    if not _mem["rates"]:
        ts, rates, date = _load_disk()
        if rates:
            _mem.update(ts=ts, rates=rates, date=date, live=True)
            if now - ts < TTL_SECONDS and not force:
                return rates
    # Refrescar desde la red (best-effort).
    try:
        rates, date = _fetch()
        merged = dict(FX_RATES)
        merged.update(rates)
        _mem.update(ts=now, rates=merged, date=date, live=True)
        _save_disk(now, merged, date)
        return merged
    except Exception:
        if _mem["rates"]:
            return _mem["rates"]
        _mem.update(rates=dict(FX_RATES), live=False, date=None)
        return _mem["rates"]


def rate(currency: str) -> float:
    return get_rates().get(currency, FX_RATES.get(currency, 1.0))


def to_eur(amount: float, currency: str) -> float:
    return (amount or 0) * rate(currency)


def info() -> dict:
    """Para mostrar en Ajustes: tasas, fecha del BCE y antigüedad de la caché."""
    r = get_rates()
    age = (time.time() - _mem["ts"]) if _mem["ts"] else None
    return {
        "rates": r, "date": _mem.get("date"), "live": _mem.get("live", False),
        "age_hours": round(age / 3600, 1) if age is not None else None,
    }
