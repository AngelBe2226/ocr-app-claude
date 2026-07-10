# MyMoney

Personal Finance Dashboard — FastAPI + Jinja2. Base de datos SQLite por defecto, o Postgres/Neon para varios dispositivos.

## Siempre encendido (ya configurado) ✅

La app corre **sola** como servicio de macOS (`launchd`): arranca al iniciar sesión y se reinicia
si se cae. No hace falta abrir la Terminal.

Abre en tu navegador: **http://localhost:8000**
Usuario: `angelgbct@gmail.com` · Contraseña: `finanzas123`.

### Controlar el servicio (Terminal)

```
# Ver si está encendido (aparece 'com.mymoney.app')
launchctl list | grep mymoney

# Reiniciar (p.ej. tras actualizar el código)
launchctl kickstart -k gui/$(id -u)/com.mymoney.app

# Apagar / encender el servicio
launchctl unload ~/Library/LaunchAgents/com.mymoney.app.plist
launchctl load -w ~/Library/LaunchAgents/com.mymoney.app.plist

# Ver el registro / errores
tail -f mymoney.log
```

## Ejecutar a mano (alternativa)

```
cd /Users/angel/Documents/GitHub/ocr-app-claude
./run.sh          # http://localhost:8000  (Ctrl+C para parar)
./run.sh 8001     # otro puerto si el 8000 está ocupado
```

## Acceder desde varios dispositivos

**Opción A — misma red WiFi (rápido):** el servicio ya escucha en toda la red (`0.0.0.0:8000`).
Desde el móvil/tablet en la misma WiFi abre **http://TU_IP_LOCAL:8000** (tu IP hoy es `192.168.1.132`,
míralas con `ipconfig getifaddr en0`). La primera vez macOS puede pedir permitir conexiones entrantes a
Python: **Ajustes → Red → Firewall → Opciones → permitir Python** (o desactiva el firewall en casa).

**Opción B — desde cualquier sitio (base de datos en la nube con Neon):** ver más abajo.

## Base de datos en la nube (Neon) para compartir entre dispositivos

Por defecto los datos viven en `finance.db` (SQLite, solo este Mac). Para tener una única base de
datos compartida, usa **Neon** (Postgres serverless con capa gratuita):

1. Crea una cuenta en **https://neon.tech** (gratis) → **New Project** (elige región cercana, p.ej. *Frankfurt / eu-central-1*).
2. En el panel del proyecto, copia el **Connection string** (empieza por `postgresql://...` e incluye `?sslmode=require`).
3. Instala el driver de Postgres una vez:
   ```
   python3 -m pip install --user "psycopg[binary]"
   ```
4. Dile a la app que use Neon con la variable `DATABASE_URL`:
   - **A mano:** `DATABASE_URL='postgresql://...' ./run.sh`
   - **Servicio siempre-encendido:** edita `~/Library/LaunchAgents/com.mymoney.app.plist`, y dentro de
     `<key>EnvironmentVariables</key>` añade:
     ```xml
     <key>DATABASE_URL</key>
     <string>postgresql://usuario:clave@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require</string>
     ```
     Luego reinicia: `launchctl kickstart -k gui/$(id -u)/com.mymoney.app`.
5. Al arrancar, la app crea las tablas en Neon y siembra los datos de ejemplo automáticamente.

> Para **acceder desde fuera de casa** (4G, otra red), además de la BD en Neon necesitas publicar la
> app en internet. Lo más sencillo: desplegarla gratis en **Render.com** o **Railway.app** (repo Git +
> variable `DATABASE_URL`), o exponer este Mac con **Tailscale**/**ngrok**. Dímelo y te lo dejo montado.

> Migrar tus datos actuales de SQLite a Neon no es automático: pídemelo y te preparo un script de volcado.

## ¿Olvidaste la contraseña?

Ejecuta `python reset_password.py` desde la raíz del proyecto. Te pedirá el nuevo email y la nueva contraseña por consola y actualizará el usuario existente en la base de datos.
