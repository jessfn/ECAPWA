<!-- admin-eca — "Solicitudes de acceso" (ECA-020b). Cierra el hueco entre lo
     que promete `pwa-eca` ("el administrador la revisará") y lo que existía
     antes: `POST /solicitudes-acceso` solo escribía en la bitácora, sin
     ningún lugar para verla. Aquí se lista y se resuelve; "Aprobar" abre el
     alta real de usuario (`POST /usuarios`, ECA-004) con los datos
     precargados — la cuenta la sigue creando el administrador desde el
     panel, no esta pantalla por sí sola. -->
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../services/api'

const solicitudes = ref([])
const cargando = ref(false)
const error = ref('')

const solicitudEnAlta = ref(null)
const alta = ref({ apellidoPaterno: '', apellidoMaterno: '', telefono: '', rol: 'TECNICO' })
const dandoAlta = ref(false)
const resultadoAlta = ref(null)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await api.get('/solicitudes-acceso', { params: { estado: 'pendiente' } })
    solicitudes.value = data
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudieron cargar las solicitudes.'
  } finally {
    cargando.value = false
  }
}

function abrirAlta(solicitud) {
  solicitudEnAlta.value = solicitud
  alta.value = { apellidoPaterno: '', apellidoMaterno: '', telefono: solicitud.telefono || '', rol: 'TECNICO' }
  resultadoAlta.value = null
}

function cerrarAlta() {
  solicitudEnAlta.value = null
  resultadoAlta.value = null
}

async function confirmarAlta() {
  if (!solicitudEnAlta.value || !alta.value.apellidoPaterno.trim()) return
  dandoAlta.value = true
  error.value = ''
  try {
    const { data } = await api.post('/usuarios', {
      nombre: solicitudEnAlta.value.nombre,
      apellido_paterno: alta.value.apellidoPaterno.trim(),
      apellido_materno: alta.value.apellidoMaterno.trim() || null,
      correo: solicitudEnAlta.value.correo,
      telefono: alta.value.telefono.trim() || null,
      roles: [alta.value.rol],
    })
    await api.patch(`/solicitudes-acceso/${solicitudEnAlta.value.id}`, { estado: 'aprobada' })
    resultadoAlta.value = data
    await cargar()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo crear la cuenta.'
  } finally {
    dandoAlta.value = false
  }
}

async function rechazar(solicitud) {
  error.value = ''
  try {
    await api.patch(`/solicitudes-acceso/${solicitud.id}`, { estado: 'rechazada' })
    await cargar()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo rechazar la solicitud.'
  }
}

onMounted(cargar)
</script>

<template>
  <section class="eca-card">
    <h1 class="eca-titulo">Solicitudes de acceso</h1>
    <p class="eca-ayuda">
      Personas que pidieron acceso desde la app de técnicos. Aprobar abre el alta de usuario con sus
      datos precargados; rechazar solo cierra la solicitud, sin crear nada.
    </p>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

    <p v-if="cargando" class="eca-ayuda">Cargando…</p>
    <p v-else-if="!solicitudes.length" class="eca-ayuda">No hay solicitudes pendientes.</p>

    <table v-else class="eca-tabla">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Correo</th>
          <th>Teléfono</th>
          <th>Notas</th>
          <th>Fecha</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in solicitudes" :key="s.id">
          <td>{{ s.nombre }}</td>
          <td>{{ s.correo }}</td>
          <td>{{ s.telefono || '—' }}</td>
          <td>{{ s.notas || '—' }}</td>
          <td>{{ new Date(s.creado_en).toLocaleDateString('es-MX') }}</td>
          <td class="solicitudes__acciones">
            <button type="button" class="eca-btn eca-btn-primary" @click="abrirAlta(s)">Aprobar</button>
            <button type="button" class="eca-btn eca-btn-peligro" @click="rechazar(s)">Rechazar</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="solicitudEnAlta" class="solicitudes__modal-overlay" @click.self="cerrarAlta">
      <div class="solicitudes__modal eca-card">
        <template v-if="!resultadoAlta">
          <h2 class="eca-titulo">Crear cuenta para {{ solicitudEnAlta.nombre }}</h2>
          <p class="eca-ayuda">Correo: {{ solicitudEnAlta.correo }}</p>

          <form class="eca-form" @submit.prevent="confirmarAlta">
            <label>
              Apellido paterno
              <input v-model="alta.apellidoPaterno" type="text" required />
            </label>
            <label>
              Apellido materno
              <input v-model="alta.apellidoMaterno" type="text" />
            </label>
            <label>
              Teléfono
              <input v-model="alta.telefono" type="text" />
            </label>
            <label>
              Rol
              <select v-model="alta.rol">
                <option value="TECNICO">Técnico</option>
                <option value="ADMIN">Administrador</option>
              </select>
            </label>

            <div class="solicitudes__modal-botones">
              <button type="button" class="eca-btn eca-btn-secundario" @click="cerrarAlta">Cancelar</button>
              <button type="submit" class="eca-btn eca-btn-primary" :disabled="dandoAlta">
                {{ dandoAlta ? 'Creando…' : 'Crear cuenta' }}
              </button>
            </div>
          </form>
        </template>

        <template v-else>
          <h2 class="eca-titulo">Cuenta creada</h2>
          <p class="eca-alerta-ok">
            {{ resultadoAlta.usuario.nombre }} {{ resultadoAlta.usuario.apellido_paterno }} ya puede
            iniciar sesión.
          </p>
          <p class="eca-ayuda">
            Contraseña temporal (compártela por un canal seguro; se le pedirá cambiarla al entrar):
          </p>
          <p class="solicitudes__password">{{ resultadoAlta.contrasena_temporal }}</p>
          <button type="button" class="eca-btn eca-btn-primary" @click="cerrarAlta">Listo</button>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.solicitudes__acciones {
  display: flex;
  gap: 0.5rem;
}
.solicitudes__modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}
.solicitudes__modal {
  width: 100%;
  max-width: 420px;
}
.solicitudes__modal-botones {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 0.4rem;
}
.solicitudes__password {
  font-family: 'Courier New', monospace;
  font-size: 1.1rem;
  font-weight: 700;
  background: var(--eca-surface);
  border: 1px solid var(--eca-surface-border);
  border-radius: var(--eca-r-sm);
  padding: 0.6rem 0.9rem;
  text-align: center;
  letter-spacing: 0.05em;
}
</style>
