import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import DefaultLayout from '../layouts/DefaultLayout.vue'
import LoginView from '../views/LoginView.vue'
import InicioView from '../views/InicioView.vue'
import GeografiaView from '../views/GeografiaView.vue'
import EcasView from '../views/EcasView.vue'
import EcaImportarView from '../views/EcaImportarView.vue'
import AmbitosView from '../views/AmbitosView.vue'
import AsignacionesView from '../views/AsignacionesView.vue'
import CatalogosView from '../views/CatalogosView.vue'
import ActividadesView from '../views/ActividadesView.vue'
import ActividadDetalleView from '../views/ActividadDetalleView.vue'
import SolicitudesAccesoView from '../views/SolicitudesAccesoView.vue'
import TecnicosView from '../views/TecnicosView.vue'

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
      { path: '', name: 'inicio', component: InicioView },
      { path: 'geografia', name: 'geografia', component: GeografiaView },
      { path: 'ecas', name: 'ecas', component: EcasView, meta: { requierePermiso: 'ecas.ver' } },
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
        meta: { requierePermiso: 'ambitos.gestionar' },
      },
      {
        path: 'asignaciones',
        name: 'asignaciones',
        component: AsignacionesView,
        meta: { requierePermiso: 'asignaciones.gestionar' },
      },
      { path: 'catalogos', name: 'catalogos', component: CatalogosView },
      {
        path: 'tecnicos',
        name: 'tecnicos',
        component: TecnicosView,
        meta: { requierePermiso: 'usuarios.gestionar' },
      },
      {
        path: 'actividades',
        name: 'actividades',
        component: ActividadesView,
        meta: { requierePermiso: 'actividades.ver_todas' },
      },
      {
        path: 'actividades/:uuid',
        name: 'actividad-detalle',
        component: ActividadDetalleView,
        meta: { requierePermiso: 'actividades.ver_todas' },
      },
      {
        path: 'solicitudes-acceso',
        name: 'solicitudes-acceso',
        component: SolicitudesAccesoView,
        meta: { requierePermiso: 'usuarios.gestionar' },
      },
    ],
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

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.publica) {
    if (to.name === 'login' && auth.estaAutenticado) {
      return { name: 'inicio' }
    }
    return true
  }

  if (!auth.estaAutenticado) {
    return { name: 'login', query: { redirigir: to.fullPath } }
  }

  const permisoRequerido = to.meta.requierePermiso
  if (permisoRequerido && !auth.tienePermiso(permisoRequerido)) {
    return { name: 'inicio' }
  }

  return true
})

export default router
