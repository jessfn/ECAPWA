// pwa-eca — caché en memoria de catálogos de actividad (ECA-013 + ECA-018).
//
// Desde ECA-018 lee de IndexedDB (poblada por `bootstrap`/`pull`) — funciona
// offline. Si aún no hubo ningún bootstrap y hay red, lo dispara sobre la
// marcha para no dejar la pantalla vacía. Sigue cacheado en memoria una vez
// por sesión de la app, igual que antes.
import { leerCatalogosLocal, ejecutarBootstrap } from './bootstrap'

let cache = null
let promesaEnCurso = null

async function _cargar() {
  let catalogos = await leerCatalogosLocal()
  if (!catalogos.modalidades.length && navigator.onLine) {
    await ejecutarBootstrap().catch(() => {})
    catalogos = await leerCatalogosLocal()
  }
  return catalogos
}

export async function obtenerCatalogos({ forzar = false } = {}) {
  if (cache && !forzar) return cache
  if (!promesaEnCurso || forzar) {
    promesaEnCurso = _cargar()
      .then((resultado) => {
        cache = resultado
        return resultado
      })
      .finally(() => {
        promesaEnCurso = null
      })
  }
  return promesaEnCurso
}

export function subtemasDelTema(catalogos, temaId) {
  return catalogos.subtemas.filter((s) => s.tema_id === temaId)
}

export function _reiniciarCatalogosCacheParaPruebas() {
  cache = null
  promesaEnCurso = null
}
