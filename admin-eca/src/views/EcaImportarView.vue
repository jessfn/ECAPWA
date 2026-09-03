<!-- admin-eca — pantalla "Importar ECA" (ECA-007).
     Flujo en dos pasos: 1) subir y validar (nada se escribe todavía),
     2) revisar la previsualización y confirmar o cancelar. Si el archivo
     no trae columna identificador estable, el backend responde 422 y aquí
     se bloquea la confirmación — nunca se deduplica por nombre/municipio
     (DP-2, ver docs-eca/06 ticket ECA-007). -->
<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { iniciarImportacion, confirmarImportacion } from '../services/ecasService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const archivo = ref(null)
const columnaIdentificador = ref('')
const validando = ref(false)
const confirmando = ref(false)
const error = ref('')
const sinIdentificador = ref(false)
const resultadoValidacion = ref(null)
const resultadoConfirmacion = ref(null)

function onArchivoSeleccionado(evento) {
  archivo.value = evento.target.files?.[0] || null
  resultadoValidacion.value = null
  resultadoConfirmacion.value = null
  error.value = ''
  sinIdentificador.value = false
}

async function validar() {
  if (!archivo.value) return
  validando.value = true
  error.value = ''
  sinIdentificador.value = false
  resultadoValidacion.value = null
  resultadoConfirmacion.value = null
  try {
    resultadoValidacion.value = await iniciarImportacion(
      archivo.value,
      columnaIdentificador.value || undefined,
    )
  } catch (err) {
    if (err.response?.status === 422) {
      sinIdentificador.value = true
      error.value =
        err.response?.data?.error?.message ||
        'El archivo no tiene una columna identificador estable. Indícala arriba y vuelve a intentar.'
    } else {
      error.value = 'No se pudo validar el archivo.'
    }
  } finally {
    validando.value = false
  }
}

async function confirmar() {
  if (!resultadoValidacion.value) return
  confirmando.value = true
  error.value = ''
  try {
    resultadoConfirmacion.value = await confirmarImportacion(resultadoValidacion.value.lote_uuid)
  } catch (err) {
    error.value = 'No se pudo confirmar la importación.'
  } finally {
    confirmando.value = false
  }
}

function cancelar() {
  resultadoValidacion.value = null
  archivo.value = null
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'ecas' }" class="detalle__volver">
      <AuthIcon name="arrow-left" /> Volver a ECA
    </RouterLink>

    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="school" /></span>
      <div class="eca-page-header__texto">
        <h1>Importar ECA</h1>
        <p>Carga masiva por CSV/XLSX, con validación previa antes de confirmar.</p>
      </div>
    </div>
    <div class="eca-card eca-panel-fusionado importar">
    <p class="eca-ayuda importar__ayuda">
      El archivo (CSV o XLSX) debe traer, además de la columna identificador estable
      (<code>clave_fuente</code>, <code>id_eca</code>, <code>folio</code> o <code>clave</code> —
      se detecta sola si usa alguno de esos nombres), las columnas <code>nombre</code>,
      <code>estado_clave_inegi</code> y <code>municipio_clave_inegi</code>.
    </p>

    <div class="importar__formulario">
      <input type="file" accept=".csv,.xlsx" @change="onArchivoSeleccionado" />
      <input
        v-model="columnaIdentificador"
        type="text"
        placeholder="Columna identificador (opcional si el archivo ya trae una reconocible)"
      />
      <button type="button" class="eca-btn eca-btn-primary" :disabled="!archivo || validando" @click="validar">
        {{ validando ? 'Validando…' : 'Validar archivo' }}
      </button>
    </div>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>
    <p v-if="sinIdentificador" class="eca-alerta-aviso">
      La confirmación queda bloqueada hasta que el archivo tenga un identificador estable válido.
    </p>

    <div v-if="resultadoValidacion" class="importar__previsualizacion">
      <h2 class="eca-titulo">Previsualización</h2>
      <p>
        Total: {{ resultadoValidacion.total }} · Válidas: {{ resultadoValidacion.validas }} ·
        Con error: {{ resultadoValidacion.con_error }}
      </p>

      <table v-if="resultadoValidacion.errores.length" class="eca-tabla importar__tabla-errores">
        <thead>
          <tr>
            <th>Fila</th>
            <th>Campo</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(err, i) in resultadoValidacion.errores" :key="i">
            <td>{{ err.fila }}</td>
            <td>{{ err.campo || '—' }}</td>
            <td>{{ err.mensaje }}</td>
          </tr>
        </tbody>
      </table>

      <div class="importar__acciones">
        <button type="button" class="eca-btn eca-btn-primary" :disabled="confirmando" @click="confirmar">
          {{ confirmando ? 'Confirmando…' : `Confirmar (${resultadoValidacion.validas} filas)` }}
        </button>
        <button type="button" class="eca-btn eca-btn-secundario" @click="cancelar">Cancelar</button>
      </div>
    </div>

    <div v-if="resultadoConfirmacion" class="importar__resultado">
      <h2 class="eca-titulo">Importación confirmada</h2>
      <p class="eca-alerta-ok">Altas: {{ resultadoConfirmacion.creadas }} · Actualizaciones: {{ resultadoConfirmacion.actualizadas }}</p>
    </div>
    </div>
  </section>
</template>

<style scoped>
.detalle__volver {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--eca-purple-700);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}
.detalle__volver svg {
  width: 14px;
  height: 14px;
}
.importar__ayuda {
  max-width: 60ch;
}
.importar__formulario {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 1rem 0;
}
.importar__formulario input {
  padding: 0.5rem 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
}
.importar__acciones {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
</style>
