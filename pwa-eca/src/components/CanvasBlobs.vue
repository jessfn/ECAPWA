<!-- pwa-eca — fondo animado en <canvas>: "flow field" con ruido tipo
     Perlin — la técnica estándar para este tipo de fondo moderno (grid de
     direcciones que varía suave y continuamente; partículas que la siguen
     dejando una estela tenue, como hojas en el viento). Implementación
     propia y ligera (sin librería externa), inspirada en el enfoque de
     "Particles in a Simplex Noise Flow Field" (Johan Karlsson, CodePen:
     https://codepen.io/DonKarlssonSan/post/particles-in-simplex-noise-flow-field)
     y "Flow Fields" (Keith Peters, Medium:
     https://medium.com/@bit101/flow-fields-part-ii-f3c24c1b777d).
     Velocidad deliberadamente baja (pedido explícito: "no tan rápido").
     Se redibuja con requestAnimationFrame y se limpia al desmontar; respeta
     prefers-reduced-motion dibujando un solo cuadro estático. -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  colorTrazo: { type: String, default: 'rgba(255, 255, 255, 0.5)' },
  colorDesvanecido: { type: String, default: 'rgba(30, 58, 138, 0.09)' },
})

const lienzo = ref(null)
let idAnimacion = null
let particulas = []
let ancho = 0
let alto = 0
let t = 0

// Ruido de valor 2D suavizado (hash + interpolación coseno): barato de
// calcular por partícula/cuadro y suficiente para un flow field discreto,
// sin traer una librería de simplex-noise solo para esto.
function hash(x, y) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453
  return s - Math.floor(s)
}
function suavizar(a) {
  return a * a * (3 - 2 * a)
}
function ruido2D(x, y) {
  const x0 = Math.floor(x)
  const y0 = Math.floor(y)
  const xf = suavizar(x - x0)
  const yf = suavizar(y - y0)
  const a = hash(x0, y0)
  const b = hash(x0 + 1, y0)
  const c = hash(x0, y0 + 1)
  const d = hash(x0 + 1, y0 + 1)
  return a + (b - a) * xf + (c - a) * yf + (a - b - c + d) * xf * yf
}

function redimensionar() {
  const el = lienzo.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  ancho = rect.width
  alto = rect.height
  el.width = ancho * dpr
  el.height = alto * dpr
  const ctx = el.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function crearParticulas() {
  const n = 70
  particulas = Array.from({ length: n }, () => ({
    x: Math.random() * ancho,
    y: Math.random() * alto,
  }))
}

const ESCALA = 0.006 // tamaño del "remolino" del campo — más chico = curvas más amplias
const VELOCIDAD_DERIVA = 0.0009 // qué tan rápido cambia el campo con el tiempo
const VELOCIDAD_PARTICULA = 0.55 // avance por cuadro — bajo a propósito

function dibujar() {
  const el = lienzo.value
  if (!el) return
  const ctx = el.getContext('2d')

  // En vez de limpiar el cuadro, se pinta encima con muy baja opacidad:
  // así el trazo anterior se desvanece gradualmente y queda una estela,
  // en vez de un punto que salta de golpe.
  ctx.fillStyle = props.colorDesvanecido
  ctx.fillRect(0, 0, ancho, alto)

  ctx.strokeStyle = props.colorTrazo
  ctx.lineWidth = 1.1
  t += VELOCIDAD_DERIVA

  for (const p of particulas) {
    const angulo = ruido2D(p.x * ESCALA, p.y * ESCALA + t) * Math.PI * 4
    const nx = p.x + Math.cos(angulo) * VELOCIDAD_PARTICULA
    const ny = p.y + Math.sin(angulo) * VELOCIDAD_PARTICULA

    ctx.beginPath()
    ctx.moveTo(p.x, p.y)
    ctx.lineTo(nx, ny)
    ctx.stroke()

    p.x = nx
    p.y = ny
    if (p.x < 0 || p.x > ancho || p.y < 0 || p.y > alto) {
      p.x = Math.random() * ancho
      p.y = Math.random() * alto
    }
  }
  idAnimacion = requestAnimationFrame(dibujar)
}

onMounted(() => {
  redimensionar()
  crearParticulas()
  const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reducido) {
    dibujar()
    cancelAnimationFrame(idAnimacion)
  } else {
    dibujar()
  }
  window.addEventListener('resize', redimensionar)
})
onUnmounted(() => {
  if (idAnimacion) cancelAnimationFrame(idAnimacion)
  window.removeEventListener('resize', redimensionar)
})
</script>

<template>
  <canvas ref="lienzo" class="canvas-blobs"></canvas>
</template>

<style scoped>
.canvas-blobs {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>
