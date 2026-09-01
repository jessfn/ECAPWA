<!-- pwa-eca — fondo animado en <canvas>: partículas a la deriva que se
     conectan con una línea tenue cuando están cerca ("constelación"),
     estilo distinto al flow-field usado en el botón de Jornada. Movimiento
     lento y continuo, sin oscilación rápida. Se redibuja con
     requestAnimationFrame y se limpia al desmontar; respeta
     prefers-reduced-motion dibujando un solo cuadro estático. -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  colorPunto: { type: String, default: 'rgba(233, 213, 255, 0.9)' },
  colorLinea: { type: String, default: 'rgba(216, 180, 254, 0.35)' },
})

const lienzo = ref(null)
let idAnimacion = null
let puntos = []
let ancho = 0
let alto = 0

const N_PUNTOS = 42
const VELOCIDAD = 0.16
const DISTANCIA_MAX = 110

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

function crearPuntos() {
  puntos = Array.from({ length: N_PUNTOS }, () => ({
    x: Math.random() * ancho,
    y: Math.random() * alto,
    vx: (Math.random() - 0.5) * VELOCIDAD,
    vy: (Math.random() - 0.5) * VELOCIDAD,
    r: 1 + Math.random() * 1.3,
  }))
}

function dibujar() {
  const el = lienzo.value
  if (!el) return
  const ctx = el.getContext('2d')
  ctx.clearRect(0, 0, ancho, alto)

  for (const p of puntos) {
    p.x += p.vx
    p.y += p.vy
    if (p.x < 0 || p.x > ancho) p.vx *= -1
    if (p.y < 0 || p.y > alto) p.vy *= -1
  }

  ctx.lineWidth = 1
  for (let i = 0; i < puntos.length; i += 1) {
    for (let j = i + 1; j < puntos.length; j += 1) {
      const a = puntos[i]
      const b = puntos[j]
      const dx = a.x - b.x
      const dy = a.y - b.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < DISTANCIA_MAX) {
        ctx.globalAlpha = 1 - dist / DISTANCIA_MAX
        ctx.strokeStyle = props.colorLinea
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
      }
    }
  }
  ctx.globalAlpha = 1

  ctx.fillStyle = props.colorPunto
  for (const p of puntos) {
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fill()
  }

  idAnimacion = requestAnimationFrame(dibujar)
}

onMounted(() => {
  redimensionar()
  crearPuntos()
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
  <canvas ref="lienzo" class="canvas-constelacion"></canvas>
</template>

<style scoped>
.canvas-constelacion {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>
