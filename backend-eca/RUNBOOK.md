# RUNBOOK — backend-eca

Guía operativa de `backend-eca` en producción (VPS `2.25.213.218`, servicio
`apieca`, dominio `api-eca.sembrandodatos.com`). Complementa, no
sustituye, a `docs-eca/06_PLAN_IMPLEMENTACION_ECA.md`.

## 1. Topología actual

- **Backend**: `apieca.service` (systemd), uvicorn+gunicorn en
  `127.0.0.1:8003`, 4 workers. Código en `/var/www/backend-eca`.
- **Base de datos**: PostgreSQL local, rol `eca`, base `eca_db`.
- **Storage de evidencias**: `/var/www/backend-eca/storage` (fuera del
  webroot — nginx nunca lo sirve como estático).
- **nginx**: `apieca-sembrandodatos` (proxy a `127.0.0.1:8003`), más los
  sites de los dos frontends (`saderapp-sembrandodatos` sirve `pwa-eca`,
  `saderadmin-sembrandodatos` sirve `admin-eca` — ver nota histórica en
  §5).
- **Certificados**: Let's Encrypt, uno por dominio.

## 2. Despliegue de una nueva versión del backend

```bash
# En local: empaquetar y subir
cd backend-eca
tar czf /tmp/backend-eca.tar.gz --exclude='.venv' --exclude='__pycache__' \
  --exclude='.pytest_cache' --exclude='*.pyc' --exclude='.env' .
scp -i ~/.ssh/id_ed25519_sader /tmp/backend-eca.tar.gz root@2.25.213.218:/tmp/

# En el servidor
cd /var/www/backend-eca
tar xzf /tmp/backend-eca.tar.gz
rm /tmp/backend-eca.tar.gz
chown -R root:root /var/www/backend-eca
source .venv/bin/activate
alembic upgrade head
systemctl restart apieca
sleep 2
systemctl is-active apieca
curl -s https://api-eca.sembrandodatos.com/health
```

Verificar siempre después de un deploy: `apisader`, `apipwa`,
`fastapi_sgi`, `pwasv-backend`, `nginx`, `postgresql` siguen `active` (el
backend de ECA es independiente, pero un error de despliegue no debe
tumbar nada más).

## 3. Migraciones

- `alembic upgrade head` aplica todas las pendientes.
- Antes de aplicar en producción, validar el DDL en modo offline cuando
  sea posible: `alembic upgrade <rev_anterior>:<rev_nueva> --sql`.
  **Limitación conocida**: las migraciones de datos (semillas con JSONB o
  `RETURNING`) no soportan `--sql`; se validan corriendo la suite de
  pruebas (mocks) y aplicando en vivo.
- **Rollback**: `alembic downgrade -1` revierte la última revisión. Cada
  migración de este proyecto tiene su `downgrade()` implementado.

## 4. Backups

- **Base de datos** (`pg_dump` diario, ejemplo de cron en el servidor):
  ```bash
  0 3 * * * pg_dump -U eca -Fc eca_db > /root/backups_eca/eca_db_$(date +\%Y\%m\%d).dump
  ```
  Retener al menos 14 días; rotar los más viejos.
- **`STORAGE_DIR`** (evidencias fotográficas): respaldo incremental diario
  (`rsync -a` a un destino externo, o snapshot del volumen).
- **Restauración — probarla, no solo documentarla**:
  ```bash
  createdb -U eca eca_db_restaurada
  pg_restore -U eca -d eca_db_restaurada /root/backups_eca/eca_db_<fecha>.dump
  # Verificar: conteos de filas en tablas clave, alembic_version coincide con el código desplegado.
  dropdb -U eca eca_db_restaurada
  ```

## 5. Frontends (`pwa-eca`, `admin-eca`)

Por decisión explícita de Jesús (confirmada en sesión), los dos frontends
se publican reemplazando el contenido estático de los dominios de
producción de SADER que ya existían:

- `pwa-eca` → `https://saderapp.sembrandodatos.com`
- `admin-eca` → `https://saderadmin.sembrandodatos.com`

Antes de ese reemplazo se respaldó el contenido anterior en
`/root/backups_sader_pre_eca/` en el servidor — restaurar desde ahí si
hiciera falta revertir.

```bash
cd pwa-eca   && npx vite build   # o admin-eca
tar czf /tmp/dist.tar.gz -C dist .
scp -i ~/.ssh/id_ed25519_sader /tmp/dist.tar.gz root@2.25.213.218:/tmp/

# En el servidor
rm -rf /var/www/saderapp.sembrandodatos.com/*   # o saderadmin...
tar xzf /tmp/dist.tar.gz -C /var/www/saderapp.sembrandodatos.com
chown -R root:root /var/www/saderapp.sembrandodatos.com
```

**Importante tras cada redeploy de `pwa-eca`**: el service worker viejo
puede quedar cacheando assets con hash antiguo y mostrar pantalla en
blanco. Verificar en el navegador y, si pasa, forzar
`navigator.serviceWorker.getRegistrations()` → `unregister()` +
`caches.keys()` → `delete()` + recarga forzada, o simplemente esperar al
`registerType: 'autoUpdate'` de `vite-plugin-pwa` en el siguiente ciclo.

## 6. Variables de entorno (`.env`, fuera del repo)

| Variable | Notas |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://eca:***@127.0.0.1:5432/eca_db` |
| `SECRET_KEY` | Aleatoria larga (`openssl rand -hex 32`). Nunca en el repo. |
| `CORS_ORIGINS` | Lista separada por comas de los orígenes de los frontends reales. |
| `STORAGE_DIR` | `/var/www/backend-eca/storage` |
| `REFRESH_TOKEN_DIAS` | **DP-1**, configurable — valor inicial de trabajo a revisar con la institución (default en código: 30). |
| `OFFLINE_SESSION_DIAS` | **DP-1**, configurable — validez de la sesión local offline de la PWA (default en código: 30). |

## 7. Incidentes comunes

- **502 justo después de reiniciar `apieca`**: normal durante 1-2 s
  mientras uvicorn levanta los 4 workers; reintentar el `curl`.
- **CORS bloqueado desde un frontend nuevo**: falta agregar su origen a
  `CORS_ORIGINS` en `.env` + `systemctl restart apieca`.
- **429 inesperado en login/sync**: rate limiting (`app/core/ratelimit.py`)
  — límites en memoria por proceso; con 4 workers el límite efectivo es
  `límite × 4`. Si un técnico legítimo lo dispara seguido, es señal de un
  bug de reintento en la PWA, no de que haya que subir el límite a ciegas.
- **Evidencia no descarga en el panel**: verificar que el técnico/admin
  tiene el permiso correcto (`actividades.ver_propias`/`ver_todas`) y que
  `STORAGE_DIR` existe y tiene el archivo (`storage_clave` en la fila de
  `actividades_evidencias`).

## 8. Antes de cada piloto/lanzamiento

1. `pytest -q` en verde (incluye `test_smoke.py`, que se salta sin
   `TEST_DATABASE_URL` — correrlo de verdad contra un entorno con BD antes
   del piloto).
2. Confirmar que `alembic_version` en producción coincide con la última
   revisión del código desplegado (`GET /health` → `migracion_actual`).
3. Backup reciente + restauración probada (§4).
4. `python -m scripts.seed_piloto` con la lista real de técnicos.
5. Checklist de seguridad: `SECRET_KEY` fuerte y fuera del repo, `/docs`
   deshabilitado en producción (ya lo hace `APP_ENV=production`), sin
   endpoints de volcado/debug, cabeceras de seguridad presentes
   (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
