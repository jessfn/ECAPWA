import { describe, it, expect } from 'vitest'
import { decodificarJwt, tokenExpirado } from '../src/services/jwt'

function crearJwt(payload) {
  const base64Url = (obj) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${base64Url({ alg: 'HS256' })}.${base64Url(payload)}.firma-falsa`
}

describe('decodificarJwt', () => {
  it('lee el payload sin verificar firma', () => {
    const token = crearJwt({ sub: '42', exp: 123 })
    expect(decodificarJwt(token)).toEqual({ sub: '42', exp: 123 })
  })

  it('devuelve null ante un token mal formado', () => {
    expect(decodificarJwt('no-es-un-jwt')).toBeNull()
  })
})

describe('tokenExpirado', () => {
  it('es true si `exp` ya pasó', () => {
    const token = crearJwt({ exp: Math.floor(Date.now() / 1000) - 60 })
    expect(tokenExpirado(token)).toBe(true)
  })

  it('es false si `exp` sigue vigente', () => {
    const token = crearJwt({ exp: Math.floor(Date.now() / 1000) + 900 })
    expect(tokenExpirado(token)).toBe(false)
  })
})
