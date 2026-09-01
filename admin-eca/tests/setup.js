// admin-eca — arranque de Vitest (ECA-005).
// Node 20+ trae su propio `localStorage` global experimental, que puede
// pisar al de jsdom según el orden de carga. Forzamos explícitamente el de
// jsdom (el real "navegador" de las pruebas) para que las pruebas del store
// de sesión (que usa `localStorage`) sean deterministas.
if (typeof window !== 'undefined') {
  globalThis.localStorage = window.localStorage
}
