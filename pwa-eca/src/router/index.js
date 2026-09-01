import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import InicioView from '../views/InicioView.vue'
import PerfilView from '../views/PerfilView.vue'
import JornadaView from '../views/JornadaView.vue'
import NuevaActividadView from '../views/NuevaActividadView.vue'
import SincronizacionView from '../views/SincronizacionView.vue'
import HistorialView from '../views/HistorialView.vue'
import RegistroView from '../views/RegistroView.vue'

// pwa-eca — rutas y guard (ECA-011).
//
// El guard exige **sesión de servidor válida O sesión local offline
// vigente** (§2.2) — no solo la primera, a diferencia del guard más simple
// de admin-eca. Un `access_token` expirado sin red no debe sacar de la app
// a un técnico en campo mientras su marca local siga vigente.
const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { publica: true } },
  { path: '/registro', name: 'registro', component: RegistroView, meta: { publica: true } },
  { path: '/', name: 'inicio', component: InicioView },
  { path: '/perfil', name: 'perfil', component: PerfilView },
  { path: '/jornada', name: 'jornada', component: JornadaView },
  { path: '/actividades/nueva', name: 'nueva-actividad', component: NuevaActividadView },
  { path: '/sincronizacion', name: 'sincronizacion', component: SincronizacionView },
  { path: '/historial', name: 'historial', component: HistorialView },
  // Cualquier URL desconocida no debe dejar la pantalla en blanco (mismo
  // caso que se encontró y corrigió en `admin-eca`).
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

  return true
})

export default router
