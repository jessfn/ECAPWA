<!-- pwa-eca — pantalla "Inicio" (ECA-011, rediseño visual pedido
     explícitamente: fondo blanco, iconos, animaciones; y luego: el acceso a
     "Jornada" es un botón grande con animación y fondo en <canvas>, que
     explica para qué sirve y refleja el estado real del día). -->
<script setup>
import { onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useJornadaStore } from '../stores/jornada'
import { useConectividad } from '../services/conectividad'
import AuthIcon from '../components/auth/AuthIcon.vue'
import CanvasBlobs from '../components/CanvasBlobs.vue'
import CanvasConstelacion from '../components/CanvasConstelacion.vue'

const auth = useAuthStore()
const jornada = useJornadaStore()
const { enLinea } = useConectividad()

onMounted(() => {
  jornada.cargarHoy()
})

const saludo = computed(() => {
  const hora = new Date().getHours()
  if (hora < 12) return 'Buenos días'
  if (hora < 19) return 'Buenas tardes'
  return 'Buenas noches'
})

const iniciales = computed(() => {
  const n = auth.usuario?.nombre?.[0] || ''
  const a = auth.usuario?.apellido_paterno?.[0] || ''
  return (n + a).toUpperCase() || 'TE'
})

const jornadaTexto = computed(() => {
  if (!jornada.actual) {
    return { icono: 'calendar', desc: 'Registra la hora y el lugar en que inicia tu jornada laboral.' }
  }
  if (jornada.abierta) {
    return { icono: 'logout', desc: 'Tu jornada está activa. Registra la hora y el lugar de tu salida al finalizar.' }
  }
  return { icono: 'check', desc: 'Jornada laboral registrada correctamente para hoy.' }
})

const accesos = [
  {
    ruta: 'sincronizacion',
    icono: 'sync',
    color: 'eca-icon-badge--ambar',
    titulo: 'Sincronización',
    ayuda: 'Ver lo pendiente por enviar',
  },
  {
    ruta: 'historial',
    icono: 'clock',
    color: 'eca-icon-badge--morado',
    titulo: 'Historial',
    ayuda: 'Ver tus actividades registradas',
  },
]
</script>

<template>
  <div class="eca-contenido">
    <div class="inicio-saludo eca-entrar">
      <AuthIcon name="leaf" class="inicio-saludo__marca-agua" />
      <div class="inicio-saludo__fila">
        <span class="inicio-saludo__avatar">
          <span class="inicio-saludo__avatar-iniciales">{{ iniciales }}</span>
          <span class="inicio-saludo__avatar-anillo"></span>
        </span>
        <div class="inicio-saludo__texto">
          <h1 class="inicio-saludo__titulo">
            {{ saludo }}, <span class="inicio-saludo__nombre">{{ auth.usuario?.nombre || 'técnico' }}</span>
          </h1>
          <p class="inicio-saludo__sub">
            <AuthIcon name="map-pin" />
            <span>Jornada y actividades en campo</span>
          </p>
        </div>
      </div>

      <p v-if="!enLinea && !auth.sesionServidorValida" class="inicio-saludo__alerta">
        <AuthIcon name="wifi-off" />
        Trabajando sin conexión con tu sesión local (vigente)
      </p>
      <p v-else-if="!enLinea" class="inicio-saludo__alerta">
        <AuthIcon name="wifi-off" />
        Sin conexión, pero tu sesión sigue activa
      </p>
    </div>

    <RouterLink :to="{ name: 'jornada' }" class="inicio-jornada eca-entrar" style="--eca-delay: 0.06s">
      <CanvasBlobs class="inicio-jornada__canvas" />
      <span class="inicio-jornada__icono" :class="{ 'inicio-jornada__icono--listo': !jornada.abierta && jornada.actual }">
        <AuthIcon :name="jornadaTexto.icono" />
      </span>
      <strong class="inicio-jornada__titulo">Registro de jornada laboral</strong>
      <span class="inicio-jornada__descripcion">{{ jornadaTexto.desc }}</span>
    </RouterLink>

    <RouterLink :to="{ name: 'nueva-actividad' }" class="inicio-actividad eca-entrar" style="--eca-delay: 0.09s">
      <CanvasConstelacion class="inicio-actividad__canvas" />
      <span class="inicio-actividad__icono">
        <AuthIcon name="plus-circle" />
      </span>
      <strong class="inicio-actividad__titulo">Registro de actividades de campo</strong>
      <span class="inicio-actividad__descripcion">
        Documenta la actividad realizada: modalidad, tema y evidencia fotográfica.
      </span>
    </RouterLink>

    <nav class="inicio-accesos">
      <RouterLink
        v-for="(acceso, i) in accesos"
        :key="acceso.ruta"
        :to="{ name: acceso.ruta }"
        class="eca-card inicio-acceso eca-entrar"
        :style="{ '--eca-delay': `${0.12 + i * 0.05}s` }"
      >
        <span class="eca-icon-badge" :class="acceso.color">
          <AuthIcon :name="acceso.icono" />
        </span>
        <span class="inicio-acceso__texto">
          <strong>{{ acceso.titulo }}</strong>
          <span class="eca-ayuda">{{ acceso.ayuda }}</span>
        </span>
        <AuthIcon name="arrow-right" class="inicio-acceso__flecha" />
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
/* ---- Saludo: compacto, horizontal, con textura de marca ---- */
.inicio-saludo {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #ffffff 0%, #eefaf1 100%);
  border: 1px solid rgba(21, 128, 61, 0.1);
  border-radius: var(--eca-r-lg);
  box-shadow: var(--eca-shadow-card);
  padding: 0.9rem 1.1rem;
  margin-bottom: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.inicio-saludo__marca-agua {
  position: absolute;
  top: -1.2rem;
  right: -1rem;
  width: 6rem;
  height: 6rem;
  color: var(--eca-green-600);
  opacity: 0.08;
  transform: rotate(12deg);
  pointer-events: none;
}
.inicio-saludo__fila {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.inicio-saludo__avatar {
  position: relative;
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(145deg, var(--eca-green-400) 0%, var(--eca-green-600) 100%);
  box-shadow: 0 6px 16px rgba(21, 128, 61, 0.32);
}
.inicio-saludo__avatar-iniciales {
  position: relative;
  z-index: 1;
  font-size: 1.15rem;
  font-weight: 300;
  letter-spacing: 0.04em;
}
.inicio-saludo__avatar-anillo {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 1.5px solid var(--eca-green-400);
  animation: inicio-avatar-pulso 2.4s ease-out infinite;
}
@keyframes inicio-avatar-pulso {
  0% {
    transform: scale(0.92);
    opacity: 0.9;
  }
  100% {
    transform: scale(1.28);
    opacity: 0;
  }
}
.inicio-saludo__texto {
  min-width: 0;
}
.inicio-saludo__titulo {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--eca-green-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Nombre en degradado dorado, más oscuro/intenso que el brillo pastel del
   logo "ECA" del header — pedido explícito: "dorado más oscuro fuerte". */
.inicio-saludo__nombre {
  background: linear-gradient(100deg, #b45309 0%, #d97706 22%, #f59e0b 42%, #fbbf24 58%, #d97706 78%, #92400e 100%);
  background-size: 220% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow: 0 1px 1px rgba(146, 64, 14, 0.15);
  animation: inicio-nombre-dorado 5s ease infinite;
}
@keyframes inicio-nombre-dorado {
  0%, 100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}
.inicio-saludo__sub {
  margin: 0.1rem 0 0;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  color: var(--eca-ink-soft);
}
.inicio-saludo__sub svg {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}
.inicio-saludo__alerta {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.4rem 0.7rem;
  border-radius: 999px;
  width: fit-content;
  background: var(--eca-warn-bg);
  color: var(--eca-warn);
}
.inicio-saludo__alerta svg {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
}

/* ---- Jornada: acceso grande, con canvas animado ---- */
.inicio-jornada {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 190px;
  margin-bottom: 0.9rem;
  padding: 1.6rem 1.5rem;
  border-radius: var(--eca-r-lg);
  overflow: hidden;
  text-align: center;
  text-decoration: none;
  background: linear-gradient(160deg, #1d4ed8 0%, #1e3a8a 100%);
  box-shadow: 0 16px 36px rgba(29, 78, 216, 0.3);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}
.inicio-jornada:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 44px rgba(29, 78, 216, 0.38);
}
.inicio-jornada:active {
  transform: scale(0.98);
}
.inicio-jornada__canvas {
  z-index: 0;
}
.inicio-jornada__icono {
  position: relative;
  z-index: 1;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.16);
  border: 1.5px solid rgba(255, 255, 255, 0.35);
  color: #fff;
  animation: inicio-jornada-pulso 2.2s ease-in-out infinite;
}
.inicio-jornada__icono--listo {
  animation: none;
  background: rgba(255, 255, 255, 0.28);
}
.inicio-jornada__icono svg {
  width: 1.5rem;
  height: 1.5rem;
}
@keyframes inicio-jornada-pulso {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.28);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(255, 255, 255, 0);
  }
}
.inicio-jornada__titulo {
  position: relative;
  z-index: 1;
  color: #fff;
  font-size: 1.2rem;
}
.inicio-jornada__descripcion {
  position: relative;
  z-index: 1;
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.82rem;
  line-height: 1.4;
  max-width: 32ch;
}

/* ---- Actividad: acceso grande, con canvas de constelación ---- */
.inicio-actividad {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 190px;
  margin-bottom: 0.9rem;
  padding: 1.6rem 1.5rem;
  border-radius: var(--eca-r-lg);
  overflow: hidden;
  text-align: center;
  text-decoration: none;
  background: linear-gradient(160deg, #7e22ce 0%, #4c1d95 100%);
  box-shadow: 0 16px 36px rgba(126, 34, 206, 0.3);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}
.inicio-actividad:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 44px rgba(126, 34, 206, 0.38);
}
.inicio-actividad:active {
  transform: scale(0.98);
}
.inicio-actividad__canvas {
  z-index: 0;
}
.inicio-actividad__icono {
  position: relative;
  z-index: 1;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.16);
  border: 1.5px solid rgba(255, 255, 255, 0.35);
  color: #fff;
  animation: inicio-actividad-pulso 2.2s ease-in-out infinite;
}
.inicio-actividad__icono svg {
  width: 1.5rem;
  height: 1.5rem;
}
@keyframes inicio-actividad-pulso {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.28);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(255, 255, 255, 0);
  }
}
.inicio-actividad__titulo {
  position: relative;
  z-index: 1;
  color: #fff;
  font-size: 1.2rem;
}
.inicio-actividad__descripcion {
  position: relative;
  z-index: 1;
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.82rem;
  line-height: 1.4;
  max-width: 32ch;
}

.inicio-accesos {
  display: grid;
  gap: 0.75rem;
}
.inicio-acceso {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  text-decoration: none;
  color: var(--eca-ink);
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease;
}
.inicio-acceso:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 32px rgba(2, 20, 10, 0.14), 0 4px 10px rgba(2, 20, 10, 0.08);
}
.inicio-acceso:hover .eca-icon-badge {
  transform: scale(1.08) rotate(-4deg);
}
.inicio-acceso:active {
  transform: scale(0.98);
}
.inicio-acceso__texto {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
  flex: 1;
}
.inicio-acceso__flecha {
  width: 16px;
  height: 16px;
  color: var(--eca-ink-faint);
  flex-shrink: 0;
  transition: transform 0.15s ease;
}
.inicio-acceso:hover .inicio-acceso__flecha {
  transform: translateX(3px);
  color: var(--eca-green-600);
}

@media (max-width: 360px) {
  .inicio-jornada,
  .inicio-actividad {
    min-height: 170px;
    padding: 1.3rem 1.1rem;
  }
  .inicio-jornada__titulo,
  .inicio-actividad__titulo {
    font-size: 1.05rem;
  }
}
</style>
