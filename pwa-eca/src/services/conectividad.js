// pwa-eca — detección de conectividad (ECA-011).
//
// `navigator.onLine` es una señal de "hay una interfaz de red", no de
// "el backend es alcanzable" — es deliberadamente conservador: se usa solo
// para UX (mostrar el indicador `EstadoConexion`), nunca como única prueba
// de que una petición va a funcionar. Las peticiones reales siguen
// intentándose y fallando por su cuenta si no hay backend de verdad.
import { ref, onMounted, onUnmounted } from 'vue'

export function estaEnLinea() {
  return typeof navigator === 'undefined' ? true : navigator.onLine
}

export function useConectividad() {
  const enLinea = ref(estaEnLinea())

  function _actualizar() {
    enLinea.value = estaEnLinea()
  }

  onMounted(() => {
    window.addEventListener('online', _actualizar)
    window.addEventListener('offline', _actualizar)
  })

  onUnmounted(() => {
    window.removeEventListener('online', _actualizar)
    window.removeEventListener('offline', _actualizar)
  })

  return { enLinea }
}
