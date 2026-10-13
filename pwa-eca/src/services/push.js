// pwa-eca — suscripción a Web Push (avisos al dispositivo con la app cerrada).
//
// Reglas de plataforma que condicionan el flujo:
// - iOS/iPadOS (16.4+) solo permite Web Push si la PWA está INSTALADA en la
//   pantalla de inicio, y el permiso debe pedirse desde un gesto del usuario
//   (un toque a un botón), nunca automáticamente.
// - La suscripción es por dispositivo/navegador; el servidor la liga a la
//   cuenta que la registra (si se comparte el celular, pasa a la última).
import { api } from './api'

export function pushSoportado() {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

export function esIos() {
  const ua = navigator.userAgent || ''
  return /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

export function estaInstalada() {
  return window.matchMedia?.('(display-mode: standalone)').matches || navigator.standalone === true
}

// 'no_soportado' | 'requiere_instalar' | 'bloqueado' | 'inactivo' | 'activo'
export async function estadoPush() {
  if (esIos() && !estaInstalada()) return 'requiere_instalar'
  if (!pushSoportado()) return 'no_soportado'
  if (Notification.permission === 'denied') return 'bloqueado'
  if (Notification.permission !== 'granted') return 'inactivo'
  try {
    const reg = await navigator.serviceWorker.ready
    return (await reg.pushManager.getSubscription()) ? 'activo' : 'inactivo'
  } catch {
    return 'inactivo'
  }
}

function base64UrlABytes(base64) {
  const relleno = '='.repeat((4 - (base64.length % 4)) % 4)
  const crudo = atob((base64 + relleno).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(crudo, (c) => c.charCodeAt(0))
}

async function enviarSuscripcion(sub) {
  const j = sub.toJSON()
  await api.post('/notificaciones/push/suscribir', { endpoint: j.endpoint, keys: j.keys })
}

// Debe llamarse desde un gesto del usuario (clic/toque).
export async function activarPush() {
  if (!pushSoportado()) throw new Error('Tu navegador no admite avisos push.')
  const permiso = await Notification.requestPermission()
  if (permiso !== 'granted') throw new Error('Los avisos están bloqueados en este dispositivo.')

  const { data } = await api.get('/notificaciones/push/clave')
  if (!data.clave) throw new Error('Los avisos push aún no están habilitados en el servidor.')

  const reg = await navigator.serviceWorker.ready
  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: base64UrlABytes(data.clave) })
  }
  await enviarSuscripcion(sub)
}

// Al abrir la app con el permiso ya concedido: re-registra la suscripción en
// el servidor (la liga a la cuenta actual y la reactiva si se había dado de baja).
export async function sincronizarPushSilencioso() {
  try {
    if (!pushSoportado() || Notification.permission !== 'granted') return
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    if (sub) await enviarSuscripcion(sub)
  } catch {
    // mejor esfuerzo
  }
}

// Al cerrar sesión: este dispositivo deja de recibir los avisos de esa cuenta.
export async function desligarPushEnServidor() {
  try {
    if (!pushSoportado()) return
    const reg = await navigator.serviceWorker.getRegistration()
    const sub = await reg?.pushManager.getSubscription()
    if (sub) await api.post('/notificaciones/push/desuscribir', { endpoint: sub.endpoint })
  } catch {
    // mejor esfuerzo
  }
}
