import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NotAuthenticated
from app.database import Base, SessionLocal, engine
from app.migrations import ensure_schema
from app.routers import (
    accounts_router, add_router, auth_router, budgets_router, categories_router, debts_router,
    goals_router, overview_router, profiles_router, reports_router, settings_router, transactions_router,
)
from app.seed import ensure_categories, seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranque: crea tablas nuevas, añade columnas que falten, siembra datos si la
    # BD está vacía y garantiza que las categorías estén migradas a BD.
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    with SessionLocal() as db:
        seed_if_empty(db)
        ensure_categories(db)
    yield
    # Apagado: nada que limpiar por ahora.


app = FastAPI(title="Mis Finanzas", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-secret-mis-finanzas"))
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(NotAuthenticated)
def not_authenticated_handler(request: Request, exc: NotAuthenticated):
    return RedirectResponse("/login", status_code=303)


app.include_router(auth_router.router)
app.include_router(add_router.router)
app.include_router(overview_router.router)
# Specific-path routers must be registered before profiles_router's /{profile_id}
# catch-all, otherwise it would swallow paths like /accounts, /goals, etc.
app.include_router(accounts_router.router)
app.include_router(categories_router.router)
app.include_router(budgets_router.router)
app.include_router(goals_router.router)
app.include_router(debts_router.router)
app.include_router(reports_router.router)
app.include_router(transactions_router.router)
app.include_router(settings_router.router)
app.include_router(profiles_router.router)
