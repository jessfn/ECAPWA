// pwa-eca — store de ECA offline (ECA-018). Es el subconjunto que ya trajo
// `bootstrap`/`pull` (REGLA DE ECA) — nunca el catálogo completo.
import { defineStore } from 'pinia'
import { leerEcasLocal, ejecutarBootstrap } from '../services/bootstrap'

export const useEcasStore = defineStore('ecas', {
  state: () => ({
    items: [],
    cargando: false,
  }),

  actions: {
    async cargar() {
      this.cargando = true
      try {
        this.items = await leerEcasLocal()
        if (!this.items.length && navigator.onLine) {
          await ejecutarBootstrap().catch(() => {})
          this.items = await leerEcasLocal()
        }
      } finally {
        this.cargando = false
      }
      return this.items
    },

    buscar(texto) {
      const q = texto.trim().toLowerCase()
      if (!q) return this.items
      return this.items.filter((e) => e.eca_nombre.toLowerCase().includes(q))
    },
  },
})
