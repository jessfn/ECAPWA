import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import './styles/auth.css'
import { useAuthStore } from './stores/auth'
import { armarAutoSync } from './services/sync'
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
