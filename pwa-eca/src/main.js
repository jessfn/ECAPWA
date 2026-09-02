import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import './styles/auth.css'
import { useAuthStore } from './stores/auth'
import { armarAutoSync, sincronizarOportunista } from './services/sync'
import { iniciarAutoActualizacion } from './services/autoUpdate'

// pwa-eca — punto de entrada (ECA-011: Pinia + router; ECA-017: dispara
// sincronización automática al recuperar red; auto-actualización sin
// recarga manual del usuario).
iniciarAutoActualizacion()

const app = createApp(App)
app.use(createPinia())
app.use(router)
armarAutoSync(useAuthStore())
app.mount('#app')

// Antes solo se sincronizaba al recuperar red (evento `online`) o al
// presionar "Sincronizar ahora": un dispositivo que nunca pierde la
// señal podía dejar jornadas/actividades pendientes indefinidamente sin
// que el usuario lo notara. Se agrega un intento al abrir la app y un
// respaldo periódico cada 2 minutos — ambos mejor esfuerzo, nunca
// bloquean ni arriesgan datos (el outbox ya los tiene a salvo).
sincronizarOportunista()
setInterval(sincronizarOportunista, 2 * 60 * 1000)
