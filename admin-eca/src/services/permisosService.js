// admin-eca — catálogo de roles/permisos y asignación directa de permisos
// por usuario (ECA-021 "Permisos administrativos").
import { api } from './api'

export async function listarRoles() {
  const { data } = await api.get('/roles')
  return data
}

export async function listarPermisos() {
  const { data } = await api.get('/permisos')
  return data
}

export async function asignarPermisos(usuarioId, permisos) {
  const { data } = await api.put(`/usuarios/${usuarioId}/permisos`, { permisos })
  return data
}
