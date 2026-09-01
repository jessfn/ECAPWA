// pwa-eca — store del contador/listado de pendientes del outbox (ECA-016).
import { defineStore } from 'pinia'
import { contarPendientes, listarTodo } from '../services/outbox'

export const useOutboxStore = defineStore('outbox', {
  state: () => ({
    pendientes: 0,
    items: [],
  }),

  actions: {
    async refrescar() {
      const [pendientes, items] = await Promise.all([contarPendientes(), listarTodo()])
      this.pendientes = pendientes
      this.items = items
    },
  },
})
