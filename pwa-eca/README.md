# pwa-eca

PWA de **técnicos de campo** del sistema ECA (Escuelas de Campo).

Es la aplicación que usará el técnico para: iniciar sesión, consultar sus ECA relevantes,
iniciar/terminar jornada, registrar actividades georreferenciadas con evidencia fotográfica,
trabajar **sin conexión** y sincronizar sin duplicados.

Sistema **independiente** del de Sembrando Vida (`pwasuper/`). No comparte código ni backend.
Ver `docs-eca/04_ARQUITECTURA_OBJETIVO.md` §4 y §9.

## Estado — ECA-001

Solo **estructura base**: scaffold Vue 3 + Vite que compila. Este ticket **no** incluye:

- capacidades PWA (service worker, manifest, offline) → **ECA-011**;
- autenticación / sesión local offline → **ECA-011** (`docs-eca/06` §2.2);
- jornada, actividad, GPS, evidencias → **ECA-012…ECA-015**;
- IndexedDB / outbox / sincronización → **ECA-016…ECA-018**;
- Pinia, `idb`, Leaflet, axios y demás dependencias → se añaden en su ticket.

## Stack (ECA-001)

- Vue 3 + Vue Router 4
- Vite 4 + `@vitejs/plugin-vue` 4

> **Nota:** se fija Vite 4 (no 5/6) por compatibilidad con Node 16, que es la versión
> disponible en el entorno actual. Al disponer de Node ≥ 18 puede alinearse con el resto del
> stack objetivo (Vite 6). Ver *decisión pendiente* al final.

## Requisitos

- Node 16 (probado) — recomendado migrar a Node ≥ 18 antes del piloto.

## Puesta en marcha (scaffold)

```bash
npm install
npm run dev      # servidor de desarrollo
npm run build    # genera dist/
npm run preview  # sirve dist/ localmente
```

## Estructura

```
pwa-eca/
├── index.html
├── vite.config.js
├── public/
└── src/
    ├── main.js
    ├── App.vue
    ├── router/      # rutas (guard de sesión → ECA-011)
    ├── stores/      # Pinia → ECA-011+
    ├── services/    # api, sync, gps, sesión local… → ECA-011+
    └── views/       # pantallas
```

## Decisión pendiente

`VITE_API_URL` y la URL relativa `/api` en producción se definen en `.env` y se consumen a
partir de ECA-011. Ver `.env.example`.
