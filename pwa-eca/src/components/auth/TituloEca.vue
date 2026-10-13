<!-- pwa-eca — título animado "ECA" del login (pedido explícito). Cada letra
     está hecha de FRAGMENTOS (una cuadrícula de piezas recortadas de la
     propia letra) que vuelan desde abajo, girando y , y encajan
     uno a uno hasta formar la letra completa — primero los de abajo, luego
     los de arriba, con un frenado suave y fluido (curva "expo-out"). Una
     letra tras otra (E, C, A). Al terminar, una luz dorada recorre las
     letras y titilan estrellitas. Debajo, "Aplicación de Seguimiento" se
     despliega entre líneas doradas. `oscuro` = sobre fondo verde oscuro
     (columna de marca de escritorio). Respeta `prefers-reduced-motion`:
     sin animaciones, ya armado. -->
<script setup>
// Tipografía moderna y profesional (Outfit), empaquetada con la app
// (@fontsource) — no desde un CDN, así también se ve sin conexión.
import '@fontsource/outfit/800.css'
import '@fontsource/outfit/600.css'

defineProps({ oscuro: { type: Boolean, default: false } })

const LETRAS = ['E', 'C', 'A']

// Fragmentos: cada letra se parte en una cuadrícula COLS x FILAS de piezas.
// Todo determinista (sin Math.random: el título se ve igual en cada carga y
// no parpadea al re-renderizar). Cada pieza es una copia de la letra recortada
// con clip-path a su celda (con 0.6px de traslape para que no queden
// costuras al encajar) y sale de abajo con su propia distancia, giro y retraso.
const COLS = 8
const FILAS = 12
const FRAGMENTOS = Array.from({ length: COLS * FILAS }, (_, n) => {
  const r = Math.floor(n / COLS)
  const c = n % COLS
  const arriba = (r / FILAS) * 100
  const abajo = 100 - ((r + 1) / FILAS) * 100
  const izq = (c / COLS) * 100
  const der = 100 - ((c + 1) / COLS) * 100
  const filaDesdeAbajo = FILAS - 1 - r
  const azar = (k) => ((r * 31 + c * 17 + k * 13) % 100) / 100
  return {
    clip: `inset(calc(${arriba}% - 0.6px) calc(${der}% - 0.6px) calc(${abajo}% - 0.6px) calc(${izq}% - 0.6px))`,
    dx: ((azar(1) - 0.5) * 0.7).toFixed(2) + 'em',
    dy: (0.7 + azar(2) * 1.0).toFixed(2) + 'em',
    rot: Math.round((azar(3) - 0.5) * 120) + 'deg',
    // los de abajo primero, con un poco de desorden
    delay: (filaDesdeAbajo * 0.045 + azar(4) * 0.26).toFixed(2) + 's',
  }
})
</script>

<template>
  <div class="titulo-eca" :class="{ 'titulo-eca--oscuro': oscuro }" role="img" aria-label="ECA, Aplicación de Seguimiento">
    <div class="titulo-eca__letras" aria-hidden="true">
      <span v-for="(letra, i) in LETRAS" :key="letra" class="titulo-eca__celda" :style="{ '--i': i }">
        <!-- Letra "fantasma": solo da el tamaño a la celda -->
        <span class="titulo-eca__base">{{ letra }}</span>
        <span
          v-for="(f, k) in FRAGMENTOS"
          :key="k"
          class="titulo-eca__fragmento"
          :style="{ clipPath: f.clip, '--dx': f.dx, '--dy': f.dy, '--rot': f.rot, '--d': f.delay }"
        >{{ letra }}</span>
      </span>

      <!-- Estrellitas que titilan alrededor de las letras -->
      <i class="titulo-eca__estrella titulo-eca__estrella--1"></i>
      <i class="titulo-eca__estrella titulo-eca__estrella--2"></i>
      <i class="titulo-eca__estrella titulo-eca__estrella--3"></i>
      <i class="titulo-eca__estrella titulo-eca__estrella--4"></i>
      <i class="titulo-eca__estrella titulo-eca__estrella--5"></i>
    </div>

    <div class="titulo-eca__subtitulo" aria-hidden="true">
      <span class="titulo-eca__linea"></span>
      <span class="titulo-eca__subtitulo-texto">Aplicación de Seguimiento</span>
      <span class="titulo-eca__linea"></span>
    </div>
  </div>
</template>

<style scoped>
.titulo-eca {
  --verde-a: #15803d;
  --verde-b: #22c55e;
  --dorado: #f5c451;
  --dorado-hondo: #d99a2b;
  --polvo: #f5c451;
  --sub: var(--au-ink-soft, #4d7360);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  user-select: none;
}
.titulo-eca--oscuro {
  --verde-a: #86efac;
  --verde-b: #4ade80;
  --sub: rgba(255, 255, 255, 0.78);
}

/* ---------------- Letras ---------------- */
.titulo-eca__letras {
  position: relative;
  display: flex;
  gap: 0.06em;
  font-size: clamp(4.2rem, 21vw, 5.6rem);
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: 0.04em;
  font-family: 'Outfit', var(--au-font, system-ui, sans-serif);
}
.titulo-eca--oscuro .titulo-eca__letras {
  font-size: clamp(5.5rem, 8vw, 7.5rem);
}

/* Celda de cada letra */
.titulo-eca__celda {
  position: relative;
  display: inline-block;
  /* retraso de arranque de esta letra: 1.ª, 2.ª y 3.ª una tras otra */
  --inicio: calc(0.25s + var(--i) * 0.75s);
  filter: drop-shadow(0 4px 10px rgba(21, 128, 61, 0.35));
}
.titulo-eca--oscuro .titulo-eca__celda {
  filter: drop-shadow(0 4px 18px rgba(74, 222, 128, 0.45));
}

.titulo-eca__base {
  visibility: hidden;
}

/* Cada fragmento = la letra completa recortada a su celda (clip-path inline).
   Todos comparten el mismo degradado y la misma fase, así al encajar forman
   una sola letra continua. */
.titulo-eca__fragmento {
  position: absolute;
  inset: 0;
  display: block;
  background: linear-gradient(
    115deg,
    var(--verde-a) 0%,
    var(--verde-b) 28%,
    var(--dorado) 46%,
    var(--dorado-hondo) 52%,
    var(--verde-b) 70%,
    var(--verde-a) 100%
  );
  background-size: 320% 100%;
  background-position: calc(var(--i, 0) * 34%) 50%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  opacity: 0;
  will-change: transform, opacity;
  animation:
    titulo-eca-encaja 1.25s cubic-bezier(0.16, 1, 0.3, 1) calc(var(--inicio) + var(--d)) both,
    titulo-eca-brillo 4.5s ease-in-out calc(var(--inicio) + 2.2s) infinite;
}

/* El fragmento vuela desde abajo (con su propio giro y desenfoque) y frena
   suave al encajar: curva expo-out = movimiento fluido, sin rebote brusco. */
@keyframes titulo-eca-encaja {
  0% {
    opacity: 0;
    transform: translate(var(--dx), var(--dy)) rotate(var(--rot)) scale(0.3);
  }
  35% {
    opacity: 1;
  }
  100% {
    opacity: 1;
    transform: translate(0, 0) rotate(0) scale(1);
  }
}
@keyframes titulo-eca-brillo {
  0%, 18%, 100% { background-position: calc(var(--i, 0) * 34%) 50%; }
  55% { background-position: calc(var(--i, 0) * 34% + 100%) 50%; }
}

/* ---------------- Estrellitas ---------------- */
.titulo-eca__estrella {
  position: absolute;
  width: 0.2em;
  height: 0.2em;
  background: var(--dorado);
  clip-path: polygon(50% 0, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0 50%, 38% 38%);
  filter: drop-shadow(0 0 4px rgba(245, 196, 81, 0.9));
  opacity: 0;
  pointer-events: none;
  animation: titulo-eca-titila 3.2s ease-in-out infinite;
}
.titulo-eca__estrella--1 { left: -0.12em; top: 0.08em; animation-delay: 3.6s; }
.titulo-eca__estrella--2 { left: 38%; top: -0.14em; width: 0.15em; height: 0.15em; animation-delay: 4.5s; }
.titulo-eca__estrella--3 { right: -0.1em; top: 0.18em; width: 0.26em; height: 0.26em; animation-delay: 4.0s; }
.titulo-eca__estrella--4 { left: 14%; bottom: -0.05em; width: 0.13em; height: 0.13em; animation-delay: 5.1s; }
.titulo-eca__estrella--5 { right: 20%; bottom: 0.02em; width: 0.16em; height: 0.16em; animation-delay: 5.5s; }

@keyframes titulo-eca-titila {
  0%, 100% { opacity: 0; transform: scale(0) rotate(0deg); }
  20% { opacity: 1; transform: scale(1) rotate(45deg); }
  40% { opacity: 0; transform: scale(0.3) rotate(90deg); }
}

/* ---------------- Subtítulo ---------------- */
.titulo-eca__subtitulo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  max-width: 100%;
  opacity: 0;
  animation: titulo-eca-sub-entra 1.1s cubic-bezier(0.22, 1, 0.36, 1) 3.1s forwards;
}
.titulo-eca__subtitulo-texto {
  font-family: 'Outfit', var(--au-font, system-ui, sans-serif);
  font-size: clamp(0.62rem, 2.9vw, 0.8rem);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.22em;
  color: var(--sub);
  white-space: nowrap;
}
.titulo-eca--oscuro .titulo-eca__subtitulo-texto {
  font-size: 0.95rem;
}
.titulo-eca__linea {
  flex: 0 0 1.6rem;
  height: 1.5px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--dorado-hondo));
}
.titulo-eca__linea:last-child {
  background: linear-gradient(270deg, transparent, var(--dorado-hondo));
}
@keyframes titulo-eca-sub-entra {
  0% { opacity: 0; letter-spacing: 0.7em; transform: translateY(8px); filter: blur(5px); }
  100% { opacity: 1; letter-spacing: 0.22em; transform: translateY(0); filter: blur(0); }
}

/* Sin animaciones: todo ya armado y visible. */
@media (prefers-reduced-motion: reduce) {
  .titulo-eca__fragmento { animation: none; opacity: 1; }
  .titulo-eca__subtitulo { animation: none; opacity: 1; filter: none; }
  .titulo-eca__estrella { display: none; }
}
</style>
