#!/usr/bin/env bash
# deploy.sh — despliegue en el VPS desde el propio clon del repo en
# /var/www/ECAPWA. Correr esto DENTRO del VPS (por SSH), no en local.
#
# Reemplaza el flujo anterior de `scp` archivo por archivo: ahora es
# `git pull` + reconstruir lo que cambió + reiniciar lo que haga falta.
set -euo pipefail
cd "$(dirname "$0")"

echo "== git pull =="
git pull origin main

echo "== backend-eca =="
cd backend-eca
.venv/bin/pip install . -q
.venv/bin/alembic upgrade head
cd ..
systemctl restart apieca
sleep 1
curl -sf http://127.0.0.1:8003/health && echo || echo "AVISO: /health no respondió OK"

echo "== pwa-eca =="
cd pwa-eca
npm install --no-audit --no-fund
npm run build
cd ..

echo "== admin-eca =="
cd admin-eca
npm install --no-audit --no-fund
npm run build
cd ..

echo "== listo =="
