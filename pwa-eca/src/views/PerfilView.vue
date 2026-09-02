<!-- pwa-eca — pantalla "Mi perfil" (ECA-011). Rediseño pedido explícito:
     mismo lenguaje visual que el perfil de pwasuper — tarjeta de cabecera
     con esquina doblada decorativa, avatar circular con iniciales, badge
     de rol, tarjeta de "Información de mi cuenta" con filas de icono +
     dato, y tarjeta de ajustes con el cambio de contraseña como flujo
     modal de 2 pasos (contraseña actual → nueva + confirmar, con
     mostrar/ocultar y validación en vivo). pwasuper tiene además datos
     que este proyecto no maneja (CURP, cargo, territorio, supervisor,
     edición de perfil) — el schema de usuario de ECA es más simple
     (`nombre`/`apellido_paterno`/`apellido_materno`/`correo`/`telefono`/
     `roles`), así que se copia el DISEÑO con los campos reales
     disponibles, no los campos de pwasuper que no existen aquí. -->
<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useConectividad } from '../services/conectividad'
import { api } from '../services/api'
import BackButton from '../components/BackButton.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'
import AvisoModal from '../components/AvisoModal.vue'

const router = useRouter()
const auth = useAuthStore()
const { enLinea } = useConectividad()

const iniciales = computed(() => {
  const n = auth.usuario?.nombre?.[0] || ''
  const a = auth.usuario?.apellido_paterno?.[0] || ''
  return (n + a).toUpperCase() || 'TE'
})

const nombreCompleto = computed(() => {
  const u = auth.usuario
  if (!u) return 'Técnico'
  return [u.nombre, u.apellido_paterno, u.apellido_materno].filter(Boolean).join(' ')
})

const ETIQUETAS_ROL = {
  ADMIN: 'Administrador',
  TECNICO: 'Técnico de campo',
}
const rolEtiqueta = computed(() => {
  const clave = auth.usuario?.roles?.[0]
  return ETIQUETAS_ROL[clave] || 'Técnico de campo'
})

const ultimoAcceso = computed(() => {
  const iso = auth.usuario?.ultimo_acceso_en
  if (!iso) return null
  return new Date(iso).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })
})

const datos = computed(() => [
  { icono: 'mail', color: 'perfil-dato__icono--azul', etiqueta: 'Correo electrónico', valor: auth.usuario?.correo },
  { icono: 'phone', color: 'perfil-dato__icono--verde', etiqueta: 'Teléfono', valor: auth.usuario?.telefono || 'No registrado' },
  { icono: 'shield-check', color: 'perfil-dato__icono--morado', etiqueta: 'Rol', valor: rolEtiqueta.value },
  { icono: 'clock', color: 'perfil-dato__icono--ambar', etiqueta: 'Último acceso', valor: ultimoAcceso.value || 'Sin registro' },
])

// ---- Cambio de contraseña: modal de 2 pasos, calcado del flujo de
// pwasuper (verificar actual → nueva + confirmar), adaptado a que el
// backend de ECA valida ambas contraseñas en UNA sola llamada (no hay
// endpoint de "solo verificar"): el paso 1 solo avanza la UI; si el
// envío final del paso 2 rechaza la contraseña actual, se regresa al
// paso 1 mostrando el error ahí, en vez de fingir una verificación que
// no ocurrió de verdad.
const modalAbierto = ref(false)
const paso = ref(1)
const contrasenaActual = ref('')
const contrasenaNueva = ref('')
const contrasenaConfirmar = ref('')
const verActual = ref(false)
const verNueva = ref(false)
const verConfirmar = ref(false)
const errorActual = ref('')
const errorNueva = ref('')
const guardando = ref(false)
const avisoExito = ref(false)

const requisitoLargo = computed(() => contrasenaNueva.value.length >= 10)
const requisitoMixto = computed(() => /[a-zA-Z]/.test(contrasenaNueva.value) && /\d/.test(contrasenaNueva.value))
const requisitoCoincide = computed(() => Boolean(contrasenaConfirmar.value) && contrasenaNueva.value === contrasenaConfirmar.value)

function abrirModal() {
  modalAbierto.value = true
  paso.value = 1
  contrasenaActual.value = ''
  contrasenaNueva.value = ''
  contrasenaConfirmar.value = ''
  errorActual.value = ''
  errorNueva.value = ''
  verActual.value = false
  verNueva.value = false
  verConfirmar.value = false
}
function cerrarModal() {
  modalAbierto.value = false
}
function irAPaso2() {
  errorActual.value = ''
  if (!contrasenaActual.value) {
    errorActual.value = 'Escribe tu contraseña actual.'
    return
  }
  paso.value = 2
}

async function guardarContrasena() {
  errorNueva.value = ''
  if (!requisitoLargo.value || !requisitoMixto.value) {
    errorNueva.value = 'La contraseña nueva no cumple los requisitos de arriba.'
    return
  }
  if (!requisitoCoincide.value) {
    errorNueva.value = 'Las contraseñas no coinciden.'
    return
  }

  guardando.value = true
  try {
    await api.post('/auth/password', {
      contrasena_actual: contrasenaActual.value,
      contrasena_nueva: contrasenaNueva.value,
    })
    modalAbierto.value = false
    avisoExito.value = true
  } catch (err) {
    const mensaje = err.response?.data?.error?.message || 'No se pudo cambiar la contraseña.'
    // El backend valida la contraseña ACTUAL y la fortaleza de la nueva
    // en la misma llamada — si el mensaje habla de la actual, se
    // regresa al paso 1 con el error ahí (donde el usuario lo espera);
    // cualquier otro motivo (p. ej. fortaleza) se muestra en el paso 2.
    if (/actual/i.test(mensaje)) {
      paso.value = 1
      errorActual.value = mensaje
    } else {
      errorNueva.value = mensaje
    }
  } finally {
    guardando.value = false
  }
}

// Cambiar la contraseña revoca TODAS las sesiones del usuario en el
// servidor (medida de seguridad real del backend) — incluida la propia
// sesión activa. Seguir usando la app con el token viejo produciría 401
// constantes; lo correcto es cerrar sesión aquí mismo y pedir que vuelva
// a entrar con la contraseña nueva, en vez de dejar que el usuario se
// tope con errores confusos más adelante.
async function cerrarAvisoYRelogin() {
  avisoExito.value = false
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <!-- Cabecera: avatar + nombre + badge de rol, esquina decorativa. -->
    <div class="perfil-cabecera eca-entrar" style="--eca-delay: 0.06s">
      <span class="perfil-cabecera__esquina"></span>
      <span class="perfil-avatar">{{ iniciales }}</span>
      <h1 class="perfil-cabecera__nombre">{{ nombreCompleto }}</h1>
      <span class="perfil-cabecera__rol">
        <AuthIcon name="shield-check" />
        {{ rolEtiqueta }}
      </span>
    </div>

    <!-- Información de la cuenta. -->
    <div class="eca-card perfil-card eca-entrar" style="--eca-delay: 0.1s">
      <h2 class="perfil-card__titulo">
        <span class="perfil-card__titulo-icono"><AuthIcon name="user" /></span>
        Información de mi cuenta
      </h2>

      <ul class="perfil-datos">
        <li v-for="dato in datos" :key="dato.etiqueta" class="perfil-dato">
          <span class="perfil-dato__icono" :class="dato.color">
            <AuthIcon :name="dato.icono" />
          </span>
          <span class="perfil-dato__texto">
            <span class="perfil-dato__etiqueta">{{ dato.etiqueta }}</span>
            <span class="perfil-dato__valor">{{ dato.valor }}</span>
          </span>
        </li>
      </ul>
    </div>

    <!-- Más ajustes: cambiar contraseña. -->
    <div class="eca-card perfil-card eca-entrar" style="--eca-delay: 0.14s">
      <h2 class="perfil-card__titulo">
        <span class="perfil-card__titulo-icono"><AuthIcon name="lock" /></span>
        Más ajustes
      </h2>

      <button type="button" class="perfil-boton-contrasena" :disabled="!enLinea" @click="abrirModal">
        <AuthIcon name="lock" />
        Cambiar contraseña
      </button>
      <p v-if="!enLinea" class="eca-alerta-aviso perfil-card__aviso-offline">
        Sin conexión: no puedes cambiar la contraseña ahora.
      </p>
    </div>

    <!-- Modal de cambio de contraseña: 2 pasos. -->
    <Teleport to="body">
      <div v-if="modalAbierto" class="perfil-modal__overlay" @click.self="cerrarModal">
        <div class="perfil-modal">
          <div class="perfil-modal__cabecera">
            <h2>Cambiar contraseña</h2>
            <button type="button" class="perfil-modal__cerrar" aria-label="Cerrar" @click="cerrarModal">
              <AuthIcon name="close" />
            </button>
          </div>

          <!-- Paso 1: contraseña actual. -->
          <form v-if="paso === 1" class="perfil-modal__form" @submit.prevent="irAPaso2">
            <label class="perfil-modal__campo">
              Contraseña actual
              <div class="perfil-modal__input-conojo">
                <input :type="verActual ? 'text' : 'password'" v-model="contrasenaActual" autofocus />
                <button type="button" class="perfil-modal__ojo" :aria-label="verActual ? 'Ocultar' : 'Mostrar'" @click="verActual = !verActual">
                  <AuthIcon :name="verActual ? 'eye-off' : 'eye'" />
                </button>
              </div>
            </label>
            <p v-if="errorActual" class="eca-alerta-error" role="alert">{{ errorActual }}</p>

            <div class="perfil-modal__botones">
              <button type="button" class="eca-btn eca-btn-secundario" @click="cerrarModal">Cancelar</button>
              <button type="submit" class="eca-btn eca-btn-primary">Continuar</button>
            </div>
          </form>

          <!-- Paso 2: nueva contraseña + confirmar. -->
          <form v-else class="perfil-modal__form" @submit.prevent="guardarContrasena">
            <label class="perfil-modal__campo">
              Contraseña nueva
              <div class="perfil-modal__input-conojo">
                <input :type="verNueva ? 'text' : 'password'" v-model="contrasenaNueva" autofocus />
                <button type="button" class="perfil-modal__ojo" :aria-label="verNueva ? 'Ocultar' : 'Mostrar'" @click="verNueva = !verNueva">
                  <AuthIcon :name="verNueva ? 'eye-off' : 'eye'" />
                </button>
              </div>
            </label>

            <ul class="perfil-modal__requisitos">
              <li :class="{ 'perfil-modal__requisito--ok': requisitoLargo }">
                <AuthIcon :name="requisitoLargo ? 'check' : 'close'" /> Mínimo 10 caracteres
              </li>
              <li :class="{ 'perfil-modal__requisito--ok': requisitoMixto }">
                <AuthIcon :name="requisitoMixto ? 'check' : 'close'" /> Letras y números
              </li>
            </ul>

            <label class="perfil-modal__campo">
              Confirmar contraseña nueva
              <div class="perfil-modal__input-conojo">
                <input :type="verConfirmar ? 'text' : 'password'" v-model="contrasenaConfirmar" />
                <button type="button" class="perfil-modal__ojo" :aria-label="verConfirmar ? 'Ocultar' : 'Mostrar'" @click="verConfirmar = !verConfirmar">
                  <AuthIcon :name="verConfirmar ? 'eye-off' : 'eye'" />
                </button>
              </div>
            </label>
            <p v-if="contrasenaConfirmar && !requisitoCoincide" class="perfil-modal__no-coincide">Las contraseñas no coinciden.</p>

            <p v-if="errorNueva" class="eca-alerta-error" role="alert">{{ errorNueva }}</p>

            <div class="perfil-modal__botones">
              <button type="button" class="eca-btn eca-btn-secundario" :disabled="guardando" @click="paso = 1">Atrás</button>
              <button type="submit" class="eca-btn eca-btn-primary" :disabled="guardando">
                {{ guardando ? 'Guardando…' : 'Guardar cambios' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <AvisoModal
      v-if="avisoExito"
      tipo="exito"
      titulo="Contraseña actualizada"
      mensaje="Tu contraseña se cambió correctamente. Por seguridad, vuelve a iniciar sesión con tu nueva contraseña."
      texto-boton="Iniciar sesión"
      @cerrar="cerrarAvisoYRelogin"
    />
  </main>
</template>

<style scoped>
/* ---- Cabecera: calca la tarjeta de pwasuper (esquina doblada, avatar,
   badge de rol) con la paleta verde propia de esta app. ---- */
.perfil-cabecera {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  background: #fff;
  border-radius: var(--eca-r-lg);
  box-shadow: var(--eca-shadow-card);
  padding: 2rem 1.5rem 1.5rem;
  margin-bottom: 0.9rem;
  text-align: center;
}
.perfil-cabecera__esquina {
  position: absolute;
  top: 0;
  left: 0;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 3.5rem 3.5rem 0 0;
  border-color: var(--eca-green-600) transparent transparent transparent;
}
.perfil-cabecera__esquina::after {
  content: '';
  position: absolute;
  top: -3.5rem;
  left: -3.5rem;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 2.4rem 2.4rem 0 0;
  border-color: var(--eca-green-400) transparent transparent transparent;
}
.perfil-avatar {
  width: 4.5rem;
  height: 4.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.4rem;
  color: #fff;
  background: linear-gradient(145deg, var(--eca-green-400) 0%, var(--eca-green-600) 100%);
  box-shadow: 0 6px 16px rgba(21, 128, 61, 0.32);
  border: 2px solid var(--eca-green-200);
  z-index: 1;
}
.perfil-cabecera__nombre {
  margin: 0;
  font-size: 1.15rem;
  color: var(--eca-green-900);
  z-index: 1;
}
.perfil-cabecera__rol {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  background: var(--eca-green-600);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  z-index: 1;
}
.perfil-cabecera__rol svg {
  width: 12px;
  height: 12px;
}

/* ---- Tarjetas de información / ajustes ---- */
.perfil-card + .perfil-card {
  margin-top: 0.9rem;
}
.perfil-card__titulo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.9rem;
  font-size: 1rem;
  color: var(--eca-green-900);
}
.perfil-card__titulo-icono {
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--eca-green-100);
  color: var(--eca-green-700);
  flex-shrink: 0;
}
.perfil-card__titulo-icono svg {
  width: 0.95rem;
  height: 0.95rem;
}

.perfil-datos {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.perfil-dato {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.65rem 0.75rem;
  border-radius: var(--eca-r-sm);
  background: var(--eca-surface);
}
.perfil-dato__icono {
  flex-shrink: 0;
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.perfil-dato__icono svg {
  width: 1rem;
  height: 1rem;
}
.perfil-dato__icono--azul {
  background: linear-gradient(160deg, #38bdf8 0%, #0284c7 100%);
}
.perfil-dato__icono--verde {
  background: linear-gradient(160deg, #30d158 0%, #16a34a 100%);
}
.perfil-dato__icono--morado {
  background: linear-gradient(160deg, #a78bfa 0%, #7c3aed 100%);
}
.perfil-dato__icono--ambar {
  background: linear-gradient(160deg, #fbbf24 0%, #d97706 100%);
}
.perfil-dato__texto {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  min-width: 0;
}
.perfil-dato__etiqueta {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--eca-ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.perfil-dato__valor {
  font-size: 0.9rem;
  color: var(--eca-ink);
  overflow-wrap: anywhere;
}

/* Botón "Cambiar contraseña" — mismo espíritu del botón "neón" de
   pwasuper (glow pulsante), en verde en vez de su paleta glass. */
.perfil-boton-contrasena {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.9rem 1.1rem;
  border-radius: var(--eca-r-md);
  border: 2px solid var(--eca-green-500);
  background: linear-gradient(135deg, var(--eca-green-100) 0%, #fff 100%);
  color: var(--eca-green-800);
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: box-shadow 0.25s ease, transform 0.15s ease;
  animation: perfil-glow 2.4s ease-in-out infinite;
}
.perfil-boton-contrasena:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  animation: none;
}
.perfil-boton-contrasena:not(:disabled):active {
  transform: scale(0.98);
}
.perfil-boton-contrasena svg {
  width: 1.1rem;
  height: 1.1rem;
}
@keyframes perfil-glow {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.25);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(22, 163, 74, 0);
  }
}
.perfil-card__aviso-offline {
  margin: 0.75rem 0 0;
}

/* ---- Modal de cambio de contraseña ---- */
.perfil-modal__overlay {
  position: fixed;
  inset: 0;
  background: rgba(4, 28, 14, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
  padding: 1rem;
}
.perfil-modal {
  width: 100%;
  max-width: 360px;
  background: #fff;
  border-radius: var(--eca-r-lg);
  box-shadow: 0 30px 60px rgba(2, 20, 10, 0.35);
  padding: 1.5rem;
  animation: aviso-modal-entrar 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes aviso-modal-entrar {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(12px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.perfil-modal__cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.perfil-modal__cabecera h2 {
  margin: 0;
  color: var(--eca-green-900);
  font-size: 1.1rem;
}
.perfil-modal__cerrar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: none;
  background: var(--eca-surface);
  color: var(--eca-ink-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.perfil-modal__cerrar svg {
  width: 16px;
  height: 16px;
}
.perfil-modal__form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.perfil-modal__campo {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--eca-ink-soft);
}
.perfil-modal__input-conojo {
  position: relative;
  display: flex;
  align-items: center;
}
.perfil-modal__input-conojo input {
  width: 100%;
  padding: 0.65rem 2.5rem 0.65rem 0.8rem;
  border-radius: var(--eca-r-sm);
  border: 1.5px solid var(--eca-surface-border);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 400;
  color: var(--eca-ink);
  background: #fff;
}
.perfil-modal__input-conojo input:focus {
  outline: none;
  border-color: var(--eca-green-500);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.18);
}
.perfil-modal__ojo {
  position: absolute;
  right: 0.6rem;
  border: none;
  background: none;
  color: var(--eca-ink-faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.2rem;
}
.perfil-modal__ojo svg {
  width: 1.05rem;
  height: 1.05rem;
}
.perfil-modal__requisitos {
  list-style: none;
  margin: -0.35rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.78rem;
  color: var(--eca-ink-faint);
}
.perfil-modal__requisitos li {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.perfil-modal__requisitos svg {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}
.perfil-modal__requisito--ok {
  color: var(--eca-green-700);
  font-weight: 600;
}
.perfil-modal__no-coincide {
  margin: -0.5rem 0 0;
  font-size: 0.78rem;
  color: var(--eca-danger);
}
.perfil-modal__botones {
  display: flex;
  gap: 0.6rem;
  margin-top: 0.2rem;
}
.perfil-modal__botones .eca-btn {
  flex: 1;
}
</style>
