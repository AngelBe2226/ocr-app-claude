"""Reset the login email/password for the single seeded user.

Usage: python reset_password.py
"""
from passlib.hash import bcrypt

from app.database import SessionLocal
from app.models import User


def main():
    email = input("Nuevo email: ").strip()
    password = input("Nueva contraseña: ").strip()

    if not email or not password:
        print("El email y la contraseña no pueden estar vacíos.")
        return

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("No se encontró ningún usuario en la base de datos.")
            return

        user.email = email
        user.password_hash = bcrypt.hash(password)
        db.commit()
    finally:
        db.close()

    print("Contraseña actualizada correctamente")


if __name__ == "__main__":
    main()
