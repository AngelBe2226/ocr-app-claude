# Mis Finanzas

Personal Finance Dashboard — FastAPI + SQLite backend, Jinja2 server-rendered frontend.

## Ejecutar (para verlo en tu navegador)

Abre la app **Terminal** y pega:

```
cd /Users/angel/Documents/GitHub/ocr-app-claude
./run.sh
```

Luego abre **http://localhost:8000** en tu navegador.
Usuario: `angelgbct@gmail.com` · Contraseña: `finanzas123`.

Si el puerto 8000 está ocupado, usa otro: `./run.sh 8001` → http://localhost:8001
Para parar el servidor: `Ctrl+C` en la Terminal.

## ¿Olvidaste la contraseña?

Ejecuta `python reset_password.py` desde la raíz del proyecto. Te pedirá el nuevo email y la nueva contraseña por consola y actualizará el usuario existente en la base de datos.
