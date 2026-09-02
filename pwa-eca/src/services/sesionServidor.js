// pwa-eca — helper compartido: asegura una sesión de servidor vigente
// (refrescando el access_token si ya venció) antes de llamar a un
// endpoint protegido. Evita el 401-refresh-reintento del interceptor de
// `api.js` para llamadas *opcionales* (mejor esfuerzo, como la hidratación
// de `stores/jornada.js: cargarHoy` o el motor de sync) — con un
// access_token vencido de antemano, ese roundtrip 401 es 100% predecible
// y evitable llamando `/auth/refresh` directamente en vez de esperar el
// rechazo. Antes vivía duplicado dentro de `services/sync.js`.
export async function asegurarSesionDeServidor(auth) {
  if (auth.sesionServidorValida) return true
  try {
    await auth.refrescar()
    return true
  } catch {
    return false
  }
}
