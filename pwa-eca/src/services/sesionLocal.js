// pwa-eca — sesión local offline (ECA-011, §2.2 de `04_ARQUITECTURA_OBJETIVO.md`).
//
// Un JWT de acceso corto no debe impedir trabajar offline cuando expira sin
// red. Tras un login + `GET /auth/me` exitosos (con red), se guarda una
// marca local: identidad, permisos efectivos y la fecha de esa validación.
// Mientras esa marca esté "vigente" (validez configurable — **DP-1**, nunca
// un valor fijo en código: `VITE_OFFLINE_SESSION_DIAS`, que debe coincidir
// con `OFFLINE_SESSION_DIAS` del backend), el guard de rutas deja abrir y
// navegar la app aunque el `access_token` haya caducado y no haya red.
//
// Esta marca **nunca** se borra por expirar: solo deja de habilitar nueva
// captura (`sesionLocalVigente() === false`); cualquier pendiente ya creado
// en el outbox se conserva y se sincroniza cuando vuelva la red.
const CLAVE_SESION_LOCAL = 'eca_tecnico_sesion_local'

function _validezDias() {
  const valor = Number(import.meta.env.VITE_OFFLINE_SESSION_DIAS)
  return Number.isFinite(valor) && valor > 0 ? valor : 30
}

export function guardarSesionLocal({ usuario, permisos }) {
  const marca = {
    usuario,
    permisos,
    validada_en: new Date().toISOString(),
  }
  localStorage.setItem(CLAVE_SESION_LOCAL, JSON.stringify(marca))
  return marca
}

export function leerSesionLocal() {
  try {
    const crudo = localStorage.getItem(CLAVE_SESION_LOCAL)
    return crudo ? JSON.parse(crudo) : null
  } catch {
    return null
  }
}

export function limpiarSesionLocal() {
  localStorage.removeItem(CLAVE_SESION_LOCAL)
}

// Vigente = existe una marca Y no ha pasado su validez configurable desde
// que se guardó. Una marca inexistente (nunca hubo login+bootstrap) o
// vencida no es "vigente", pero seguirá presente en `localStorage` — no se
// borra aquí, solo se deja de considerar habilitante para nueva captura.
export function sesionLocalVigente() {
  const marca = leerSesionLocal()
  if (!marca?.validada_en) {
    return false
  }
  const validadaEn = new Date(marca.validada_en).getTime()
  if (Number.isNaN(validadaEn)) {
    return false
  }
  const limiteMs = _validezDias() * 24 * 60 * 60 * 1000
  return Date.now() - validadaEn < limiteMs
}
