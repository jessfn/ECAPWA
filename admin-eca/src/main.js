import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import './styles/auth.css'
import { iniciarAutoActualizacion } from './services/autoUpdate'

// admin-eca — punto de entrada (ECA-001 + ECA-005: Pinia y router con
// guard; auto-actualización sin recarga manual del usuario).
iniciarAutoActualizacion()

createApp(App).use(createPinia()).use(router).mount('#app')
