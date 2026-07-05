# Mis Finanzas

Personal Finance Dashboard — FastAPI + SQLite backend, Jinja2 server-rendered frontend.

## Ejecutar

```
python3 -m uvicorn app.main:app --reload
```

## ¿Olvidaste la contraseña?

Ejecuta `python reset_password.py` desde la raíz del proyecto. Te pedirá el nuevo email y la nueva contraseña por consola y actualizará el usuario existente en la base de datos.
