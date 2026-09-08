import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import DefaultLayout from '../layouts/DefaultLayout.vue'
import LoginView from '../views/LoginView.vue'
import InicioView from '../views/InicioView.vue'
import VisorSeguimientoView from '../views/VisorSeguimientoView.vue'
import EcasView from '../views/EcasView.vue'
import EcaImportarView from '../views/EcaImportarView.vue'
import AmbitosView from '../views/AmbitosView.vue'
import AsignacionesView from '../views/AsignacionesView.vue'
import CatalogosView from '../views/CatalogosView.vue'
import ActividadesView from '../views/ActividadesView.vue'
import ActividadDetalleView from '../views/ActividadDetalleView.vue'
import TecnicosView from '../views/TecnicosView.vue'
import PermisosAdministrativosView from '../views/PermisosAdministrativosView.vue'

// admin-eca — rutas (ECA-005 + ECA-006 + ECA-007 + ECA-008 + ECA-009).
// Guard por token válido + expiración (no por sola presencia en
// localStorage, `04_ARQUITECTURA_OBJETIVO.md` §2) y, cuando la ruta lo pide,
// por permiso — solo UX: el backend ya impone la autorización real.
const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { publica: true } },
  {
    path: '/',
    component: DefaultLayout,
    children: [
      { path: '', name: 'inicio', component: InicioView, meta: { requierePermiso: 'vista.inicio' } },
      {
        path: 'visor-seguimiento',
        name: 'visor-seguimiento',
        component: VisorSeguimientoView,
        meta: { requierePermiso: 'vista.visor_seguimiento' },
      },
      { path: 'ecas', name: 'ecas', component: EcasView, meta: { requierePermiso: 'vista.ecas' } },
      {
        path: 'ecas/importar',
        name: 'ecas-importar',
        component: EcaImportarView,
        meta: { requierePermiso: 'ecas.importar' },
      },
      {
        path: 'ambitos',
        name: 'ambitos',
        component: AmbitosView,
        meta: { requierePermiso: 'vista.ambitos' },
      },
      {
        path: 'asignaciones',
        name: 'asignaciones',
        component: AsignacionesView,
        meta: { requierePermiso: 'vista.asignaciones' },
      },
      {
        path: 'catalogos',
        name: 'catalogos',
        component: CatalogosView,
        meta: { requierePermiso: 'vista.catalogos' },
      },
      {
        path: 'tecnicos',
        name: 'tecnicos',
        component: TecnicosView,
        meta: { requierePermiso: 'vista.tecnicos' },
      },
      {
        path: 'actividades',
        name: 'actividades',
        component: ActividadesView,
        meta: { requierePermiso: 'vista.actividades' },
      },
      {
        path: 'actividades/:uuid',
        name: 'actividad-detalle',
        component: ActividadDetalleView,
        meta: { requierePermiso: 'vista.actividades' },
      },
      {
        path: 'permisos-administrativos',
        name: 'permisos-administrativos',
        component: PermisosAdministrativosView,
        meta: { requierePermiso: 'vista.permisos_administrativos' },
      },
    ],
  },
  // Sin `meta.requierePermiso`: red de seguridad para una cuenta USUARIO
  // que (por lo que sea) no tiene ningún `vista.*` activo — sin esto,
  // `primeraRutaAccesible()` no tendría a dónde mandarla y el guard
  // volvería a caer en un bucle.
  {
    path: '/sin-acceso',
    name: 'sin-acceso',
    component: DefaultLayout,
    children: [{ path: '', name: 'sin-acceso-vista', component: () => import('../views/SinAccesoView.vue') }],
  },
  // Cualquier URL que no coincida con una ruta conocida (p. ej. escrita a
  // mano, o un enlace de otra app como `/registro` de pwa-eca) no debe
  // dejar la pantalla en blanco: se manda a inicio/login según corresponda.
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Mismo orden que el sidebar — el primer `vista.*` que el usuario sí tiene
// es a donde lo mandamos tras login o cuando pierde acceso a la ruta
// actual. Antes se asumía `{ name: 'inicio' }` a secas: un usuario creado
// con un solo permiso distinto a `vista.inicio` quedaba en un bucle
// infinito (inicio exige `vista.inicio` → lo rebota a inicio → ...), que es
// justo lo que colgó el panel al loguear la cuenta de prueba.
const ORDEN_VISTAS = [
  'inicio',
  'visor-seguimiento',
  'ecas',
  'ambitos',
  'asignaciones',
  'catalogos',
  'tecnicos',
  'actividades',
  'permisos-administrativos',
]
const PERMISO_DE_RUTA = { inicio: 'vista.inicio', 'visor-seguimiento': 'vista.visor_seguimiento', ecas: 'vista.ecas', ambitos: 'vista.ambitos', asignaciones: 'vista.asignaciones', catalogos: 'vista.catalogos', tecnicos: 'vista.tecnicos', actividades: 'vista.actividades', 'permisos-administrativos': 'vista.permisos_administrativos' }

function primeraRutaAccesible(auth) {
  const nombre = ORDEN_VISTAS.find((n) => auth.tienePermiso(PERMISO_DE_RUTA[n]))
  return nombre ? { name: nombre } : { name: 'sin-acceso-vista' }
}

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.publica) {
    if (to.name === 'login' && auth.estaAutenticado) {
      return primeraRutaAccesible(auth)
    }
    return true
  }

  if (!auth.estaAutenticado) {
    return { name: 'login', query: { redirigir: to.fullPath } }
  }

  const permisoRequerido = to.meta.requierePermiso
  if (permisoRequerido && !auth.tienePermiso(permisoRequerido)) {
    // Nunca mandar de vuelta a `to` ni a un destino fijo que el usuario
    // tampoco pueda ver — eso es lo que producía el bucle.
    if (to.name === 'sin-acceso-vista') return true
    return primeraRutaAccesible(auth)
  }

  return true
})

export { primeraRutaAccesible }
export default router
