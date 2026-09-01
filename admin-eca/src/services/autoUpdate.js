// admin-eca — auto-actualización sin recarga manual.
//
// admin-eca es una SPA plana (sin service worker): sondea `version.json`
// (siempre pedido con `cache: 'no-store'`) cada `INTERVALO_SONDEO_MS` y,
// en cuanto el `buildId` publicado ya no es el que esta pestaña cargó,
// recarga sola. Cubre exactamente el pedido: "cada vez que se haga una
// deployada debe actualizarse inmediatamente la app aunque no se
// refresque el navegador".
const INTERVALO_SONDEO_MS = 30_000

export function iniciarAutoActualizacion() {
  setInterval(async () => {
    try {
      const respuesta = await fetch(`/version.json?t=${Date.now()}`, { cache: 'no-store' })
      if (!respuesta.ok) return
      const { buildId } = await respuesta.json()
      if (buildId && buildId !== __BUILD_ID__) {
        window.location.reload()
      }
    } catch {
      // Sin red: no interrumpir, se reintenta en el próximo ciclo.
    }
  }, INTERVALO_SONDEO_MS)
}
