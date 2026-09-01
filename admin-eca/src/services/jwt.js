// admin-eca — decodificación de JWT sin verificar firma (ECA-005).
//
// Solo para leer `exp` en el cliente y decidir si el access token ya
// caducó; la verificación real de la firma la hace siempre el backend.
// Nunca confiar en el contenido de este payload para autorización — eso
// es responsabilidad exclusiva del servidor (04_ARQUITECTURA_OBJETIVO.md §6).

export function decodificarJwt(token) {
  const partes = token.split('.')
  if (partes.length !== 3) {
    return null
  }
  try {
    const base64 = partes[1].replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join(''),
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

export function tokenExpirado(token, margenSegundos = 5) {
  const payload = decodificarJwt(token)
  if (!payload?.exp) {
    return true
  }
  const ahoraSegundos = Date.now() / 1000
  return payload.exp - margenSegundos <= ahoraSegundos
}
