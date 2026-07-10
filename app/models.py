from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String, default="EUR")
    balance: Mapped[float] = mapped_column(Float, default=0)
    color: Mapped[str] = mapped_column(String, default="#7A756C")
    icon: Mapped[str] = mapped_column(String, default="")
    cycle_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String, default="")
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    attachment_name: Mapped[str] = mapped_column(String, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    place_name: Mapped[str] = mapped_column(String, default="")
    subcategory: Mapped[str] = mapped_column(String, default="")  # subcategoría opcional
    store: Mapped[str] = mapped_column(String, default="")        # tienda/comercio (SPAR, etc.)

    account: Mapped["Account"] = relationship()


class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[float] = mapped_column(Float)
    date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String, default="")


class Loan(Base):
    __tablename__ = "loans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    principal: Mapped[float] = mapped_column(Float)
    balance: Mapped[float] = mapped_column(Float)
    rate: Mapped[float] = mapped_column(Float)
    payment: Mapped[float] = mapped_column(Float)


class Bill(Base):
    __tablename__ = "bills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    due_day: Mapped[int] = mapped_column(Integer)
    paid: Mapped[float] = mapped_column(Float, default=0)


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    target: Mapped[float] = mapped_column(Float)
    current: Mapped[float] = mapped_column(Float, default=0)
    target_date: Mapped[date] = mapped_column(Date)
    color: Mapped[str] = mapped_column(String, default="#12898F")


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    allocated: Mapped[float] = mapped_column(Float, default=0)
    rollover: Mapped[bool] = mapped_column(Boolean, default=False)
    period: Mapped[str] = mapped_column(String, default="monthly")  # monthly / annual


class SpendingLimit(Base):
    __tablename__ = "spending_limits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile: Mapped[str | None] = mapped_column(String, nullable=True)  # None = global
    daily: Mapped[float | None] = mapped_column(Float, nullable=True)
    monthly: Mapped[float | None] = mapped_column(Float, nullable=True)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    slug: Mapped[str] = mapped_column(String)   # identificador estable usado en transacciones/URLs
    name: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String, default="#12898F")
    icon: Mapped[str] = mapped_column(String, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Motor de ahorro: % del ingreso que cuenta reservado para ahorro y para impuestos (IRPF/SS).
    savings_rate: Mapped[float] = mapped_column(Float, default=40.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile: Mapped[str] = mapped_column(String)          # melia / realestate / freelance / personal
    kind: Mapped[str] = mapped_column(String)             # income / expense
    name: Mapped[str] = mapped_column(String)
    icon: Mapped[str] = mapped_column(String, default="")  # emoji opcional; si vacío se usa la inicial
    color: Mapped[str] = mapped_column(String, default="#12898F")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # "Sin categoría": no editable/borrable
    # Ingresos que NO cuentan para el ahorro (reventa, préstamos de familia/amigos/banco).
    counts_for_savings: Mapped[bool] = mapped_column(Boolean, default=True)

    subcategories: Mapped[list["Subcategory"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Subcategory(Base):
    __tablename__ = "subcategories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String)
    icon: Mapped[str] = mapped_column(String, default="")

    category: Mapped["Category"] = relationship(back_populates="subcategories")


class SavingsReserve(Base):
    """Reserva de ahorro/impuestos apartada por el usuario (botón 'Reservar').
    Registra cuánto se ha apartado de un perfil en un periodo, separando impuestos y ahorro."""
    __tablename__ = "savings_reserves"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile: Mapped[str | None] = mapped_column(String, nullable=True)  # slug de perfil; None = global
    period_key: Mapped[str] = mapped_column(String)      # p.ej. "2026-07" (mes) o "2026" (año)
    kind: Mapped[str] = mapped_column(String)            # 'tax' (impuestos) | 'savings' (ahorro)
    amount: Mapped[float] = mapped_column(Float)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    theme: Mapped[str] = mapped_column(String, default="light")
    accent_key: Mapped[str] = mapped_column(String, default="teal")


class FamilyInvite(Base):
    __tablename__ = "family_invites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankConnection(Base):
    __tablename__ = "bank_connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String, default="demo")  # tink / gocardless / truelayer / demo
    bank_id: Mapped[str] = mapped_column(String)
    bank_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending / connected / disconnected
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    synced_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
