<!-- pwa-eca — fondo animado en <canvas> para los héroes de Inicio: manchas
     suaves a la deriva (movimiento orbital lento, no rebote), muy
     desvanecidas para no competir con el texto. Se posiciona desde fuera
     (ver InicioView.vue) para no quedar debajo del medio círculo. Se
     redibuja con requestAnimationFrame y se limpia al desmontar; respeta
     prefers-reduced-motion dibujando un solo cuadro estático. -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  colores: {
    type: Array,
    default: () => ['rgba(255, 255, 255, 0.16)', 'rgba(255, 255, 255, 0.1)', 'rgba(255, 255, 255, 0.13)'],
  },
})

const lienzo = ref(null)
let idAnimacion = null
let manchas = []
let ancho = 0
let alto = 0
let t = 0

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

function crearManchas() {
  manchas = props.colores.map((color, i) => ({
    cx: Math.random() * ancho,
    cy: Math.random() * alto,
    orbita: (0.18 + Math.random() * 0.14) * Math.max(ancho, alto),
    velocidad: 0.12 + i * 0.05,
    fase: i * 2.1,
    r: (0.3 + Math.random() * 0.16) * Math.max(ancho, alto),
    color,
  }))
}

function dibujar() {
  const el = lienzo.value
  if (!el) return
  const ctx = el.getContext('2d')
  ctx.clearRect(0, 0, ancho, alto)
  t += 0.01

  for (const m of manchas) {
    const angulo = m.fase + t * m.velocidad
    const x = m.cx + Math.cos(angulo) * m.orbita
    const y = m.cy + Math.sin(angulo * 1.2) * m.orbita

    const gradiente = ctx.createRadialGradient(x, y, 0, x, y, m.r)
    gradiente.addColorStop(0, m.color)
    gradiente.addColorStop(1, 'rgba(255,255,255,0)')
    ctx.fillStyle = gradiente
    ctx.beginPath()
    ctx.arc(x, y, m.r, 0, Math.PI * 2)
    ctx.fill()
  }
  idAnimacion = requestAnimationFrame(dibujar)
}

onMounted(() => {
  redimensionar()
  crearManchas()
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
  <canvas ref="lienzo" class="canvas-fondo"></canvas>
</template>

<style scoped>
.canvas-fondo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>
