// pwa-eca — store de catálogos offline (ECA-018). Lee de IndexedDB
// (poblada por `bootstrap`/`pull`); si aún no hay nada local y hay red,
// dispara un bootstrap sobre la marcha.
import { defineStore } from 'pinia'
import { leerCatalogosLocal, ejecutarBootstrap } from '../services/bootstrap'

export const useCatalogosStore = defineStore('catalogos', {
  state: () => ({
    datos: null,
    cargando: false,
  }),

  actions: {
    async cargar() {
      this.cargando = true
      try {
        this.datos = await leerCatalogosLocal()
        if (!this.datos.modalidades.length && navigator.onLine) {
          await ejecutarBootstrap().catch(() => {})
          this.datos = await leerCatalogosLocal()
        }
      } finally {
        this.cargando = false
      }
      return this.datos
    },
  },
})
