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
import CanvasFondo from '../components/CanvasFondo.vue'

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

const nombreCompleto = computed(() => {
  const u = auth.usuario
  if (!u) return 'Técnico'
  return [u.nombre, u.apellido_paterno].filter(Boolean).join(' ')
})

const jornadaTexto = computed(() => {
  if (!jornada.actual) {
    return { desc: 'Registra la hora y el lugar en que inicia tu jornada laboral.' }
  }
  if (jornada.abierta) {
    return { desc: 'Tu jornada está activa. Registra la hora y el lugar de tu salida al finalizar.' }
  }
  return { desc: 'Jornada laboral registrada correctamente para hoy.' }
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
          <span class="inicio-saludo__saludo">¡{{ saludo }}!</span>
          <h1 class="inicio-saludo__titulo">
            <span class="inicio-saludo__nombre">{{ nombreCompleto }}</span>
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

    <RouterLink :to="{ name: 'jornada' }" class="inicio-hero inicio-hero--jornada eca-entrar" style="--eca-delay: 0.06s">
      <CanvasFondo
        class="inicio-hero__canvas inicio-hero__canvas--izquierda"
        :colores="['rgba(191, 219, 254, 0.4)', 'rgba(255, 255, 255, 0.26)', 'rgba(147, 197, 253, 0.32)']"
      />
      <span class="inicio-hero__medio-circulo inicio-hero__medio-circulo--izquierda">
        <span class="inicio-hero__icono">
          <AuthIcon name="briefcase" />
        </span>
      </span>
      <span class="inicio-hero__texto inicio-hero__texto--izquierda">
        <strong class="inicio-hero__titulo">Registro de jornada laboral</strong>
        <span class="inicio-hero__descripcion">{{ jornadaTexto.desc }}</span>
      </span>
    </RouterLink>

    <RouterLink :to="{ name: 'nueva-actividad' }" class="inicio-hero inicio-hero--actividad eca-entrar" style="--eca-delay: 0.09s">
      <CanvasFondo
        class="inicio-hero__canvas inicio-hero__canvas--derecha"
        :colores="['rgba(233, 213, 255, 0.4)', 'rgba(255, 255, 255, 0.26)', 'rgba(216, 180, 254, 0.32)']"
      />
      <span class="inicio-hero__texto inicio-hero__texto--derecha">
        <strong class="inicio-hero__titulo">Registro de actividades</strong>
        <span class="inicio-hero__descripcion">
          Documenta la actividad realizada: modalidad, tema y evidencia fotográfica.
        </span>
      </span>
      <span class="inicio-hero__medio-circulo inicio-hero__medio-circulo--derecha">
        <span class="inicio-hero__icono">
          <AuthIcon name="camera" />
        </span>
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
        <span class="eca-icon-badge inicio-acceso__icono" :class="acceso.color">
          <AuthIcon :name="acceso.icono" />
        </span>
        <span class="inicio-acceso__texto">
          <strong>{{ acceso.titulo }}</strong>
          <span class="eca-ayuda">{{ acceso.ayuda }}</span>
        </span>
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
  display: flex;
  flex-direction: column;
}
/* "¡Buenas tardes!" arriba, en verde — pedido explícito, con signos de
   exclamación (arriba y abajo, como corresponde en español). */
.inicio-saludo__saludo {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--eca-green-600);
  letter-spacing: 0.02em;
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

/* ---- Héroes (Jornada / Actividad): medio círculo "pegado" al borde,
   de esquina a esquina verticalmente — sin canvas, sin animación, pedido
   explícito. El círculo mide el 100% del alto del botón y se posiciona
   con `left/right: 0` + `translateX(±50%)`: como el porcentaje de un
   `transform` es relativo al propio tamaño del elemento, queda centrado
   exactamente sobre el borde de la tarjeta sin importar el alto real
   (responsive, sin medir nada por JS). El ícono va en un círculo pequeño
   y estático, dentro de la mitad visible. */
.inicio-hero {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 176px;
  margin-bottom: 0.9rem;
  padding: 1.5rem 1.7rem;
  border-radius: var(--eca-r-lg);
  overflow: hidden;
  text-decoration: none;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}
.inicio-hero:hover {
  transform: translateY(-3px);
}
.inicio-hero:active {
  transform: scale(0.98);
}
.inicio-hero--jornada {
  padding-left: 6.75rem;
  background: linear-gradient(160deg, #1d4ed8 0%, #1e3a8a 100%);
  box-shadow: 0 16px 36px rgba(29, 78, 216, 0.3);
}
.inicio-hero--jornada:hover {
  box-shadow: 0 22px 44px rgba(29, 78, 216, 0.38);
}
.inicio-hero--actividad {
  padding-right: 6.75rem;
  background: linear-gradient(160deg, #7e22ce 0%, #4c1d95 100%);
  box-shadow: 0 16px 36px rgba(126, 34, 206, 0.3);
}
.inicio-hero--actividad:hover {
  box-shadow: 0 22px 44px rgba(126, 34, 206, 0.38);
}

/* Canvas de fondo: solo cubre la zona del texto (desde donde empieza el
   padding, que es justo donde termina la mitad visible del círculo) —
   pedido explícito: "que no quede abajo de los medios círculos". */
.inicio-hero__canvas {
  position: absolute;
  top: 0;
  bottom: 0;
  z-index: 0;
  pointer-events: none;
}
.inicio-hero__canvas--izquierda {
  left: 6.75rem;
  right: 0;
  /* Desvanecido en ambos bordes: sin esto, el corte recto del canvas se
     nota como una línea contra el degradado del botón. */
  -webkit-mask-image: linear-gradient(to right, transparent, black 2.5rem, black calc(100% - 1.5rem), transparent);
  mask-image: linear-gradient(to right, transparent, black 2.5rem, black calc(100% - 1.5rem), transparent);
}
.inicio-hero__canvas--derecha {
  left: 0;
  right: 6.75rem;
  -webkit-mask-image: linear-gradient(to left, transparent, black 2.5rem, black calc(100% - 1.5rem), transparent);
  mask-image: linear-gradient(to left, transparent, black 2.5rem, black calc(100% - 1.5rem), transparent);
}

.inicio-hero__medio-circulo {
  position: absolute;
  top: 0;
  height: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.12);
  border: 1.5px solid rgba(255, 255, 255, 0.28);
  z-index: 2;
}
.inicio-hero__medio-circulo--izquierda {
  left: 0;
  transform: translateX(-50%);
  /* El ícono se centra dentro de la mitad VISIBLE del círculo (no del
     círculo completo) — así se ve entero, sin que el borde de la tarjeta
     le recorte la mitad. */
  justify-content: flex-end;
  padding-right: 1.5rem;
}
.inicio-hero__medio-circulo--derecha {
  right: 0;
  transform: translateX(50%);
  justify-content: flex-start;
  padding-left: 1.5rem;
}

.inicio-hero__icono {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.inicio-hero__icono svg {
  width: 2.4rem;
  height: 2.4rem;
}

.inicio-hero__texto {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
  flex: 1;
}
.inicio-hero__texto--derecha {
  align-items: flex-end;
  text-align: right;
}
.inicio-hero__titulo {
  color: #fff;
  font-size: 1.15rem;
}
.inicio-hero__descripcion {
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.82rem;
  line-height: 1.4;
}

/* ---- Sincronización / Historial: dos columnas, tarjetas compactas ---- */
.inicio-accesos {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.inicio-acceso {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.6rem;
  padding: 1.1rem 0.9rem;
  text-decoration: none;
  color: var(--eca-ink);
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease;
}
.inicio-acceso:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 32px rgba(2, 20, 10, 0.14), 0 4px 10px rgba(2, 20, 10, 0.08);
}
.inicio-acceso:hover .inicio-acceso__icono {
  transform: scale(1.08) rotate(-4deg);
}
.inicio-acceso:active {
  transform: scale(0.98);
}
.inicio-acceso__icono {
  width: 2.4rem;
  height: 2.4rem;
}
.inicio-acceso__icono svg {
  width: 1.15rem;
  height: 1.15rem;
}
.inicio-acceso__texto {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
  width: 100%;
}
.inicio-acceso__texto strong {
  font-size: 0.85rem;
}
.inicio-acceso__texto .eca-ayuda {
  font-size: 0.72rem;
  line-height: 1.3;
}

@media (max-width: 360px) {
  .inicio-hero {
    min-height: 150px;
  }
  .inicio-hero--jornada {
    padding: 1.2rem 1.1rem 1.2rem 5.75rem;
  }
  .inicio-hero--actividad {
    padding: 1.2rem 5.75rem 1.2rem 1.1rem;
  }
  .inicio-hero__canvas--izquierda {
    left: 5.75rem;
  }
  .inicio-hero__canvas--derecha {
    right: 5.75rem;
  }
  .inicio-hero__titulo {
    font-size: 1.02rem;
  }
}
</style>
