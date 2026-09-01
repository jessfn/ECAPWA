// pwa-eca — arranque de Vitest (ECA-011), mismo ajuste que admin-eca.
if (typeof window !== 'undefined') {
  globalThis.localStorage = window.localStorage
}
