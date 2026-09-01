# admin-eca

Panel **administrativo** del sistema ECA (Escuelas de Campo).

Lo usará el administrador para: crear/importar usuarios, administrar estados y municipios,
importar el catálogo de ~5 000 ECA, asignar municipios de trabajo y ECA a los técnicos,
administrar catálogos de actividad y consultar las actividades registradas.

SPA (no PWA, no offline). Sistema **independiente** del panel de Sembrando Vida (`admin-pwa/`):
no comparte código ni backend. Ver `docs-eca/04_ARQUITECTURA_OBJETIVO.md` §5 y §9.

## Estado — ECA-005

Login funcional, guard de ruta por token válido + expiración, store `auth` (Pinia) con
permisos efectivos, interceptor de Axios que refresca el token en 401, layout base con
menú por permiso, pantalla "Inicio". Las pantallas de administración (usuarios, geografía,
ECA, ámbitos, asignaciones, catálogos, actividades) llegan en **ECA-006…ECA-010, ECA-019**.

## Stack

- Vue 3 + Vue Router 4 + Pinia
- Axios
- Vite 5 + `@vitejs/plugin-vue` 5
- Vitest + `@vue/test-utils` (pruebas de store e interceptor)

> El scaffold de ECA-001 fijó Vite 4 por compatibilidad con Node 16 (única versión disponible
> en ese momento). ECA-005 sube a Vite 5 aprovechando Node ≥ 20, ya disponible en este entorno.

## Requisitos

- Node ≥ 20

## Puesta en marcha

```bash
npm install
cp .env.example .env.local   # define VITE_API_URL (apunta a backend-eca)
npm run dev
npm run build     # genera dist/
npm run preview
npm test          # vitest
```

## Estructura

```
admin-eca/
├── index.html
├── vite.config.js
├── public/
└── src/
    ├── main.js
    ├── App.vue
    ├── router/      # guard de token + permiso
    ├── layouts/      # DefaultLayout.vue (header, menú por permiso, logout)
    ├── stores/       # auth.js (Pinia)
    ├── services/     # api.js (axios + interceptor refresh), jwt.js
    └── views/        # LoginView.vue, InicioView.vue
```

## Convenciones

Ver `docs-eca/07_CONVENCIONES_CODIGO_ECA.md`.
