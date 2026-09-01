<!-- pwa-eca — layout compartido de Login/Registro (ECA-020).
     Misma estructura visual que `pwasuper`: mesh de fondo + columna de
     marca en escritorio + tarjeta con vidrio esmerilado. -->
<template>
  <div class="au-root">
    <div class="au-mesh" aria-hidden="true">
      <span class="b1"></span><span class="b2"></span>
      <span class="b3"></span><span class="b4"></span>
    </div>

    <div class="au-dust" aria-hidden="true">
      <i></i><i></i><i></i><i></i><i></i>
      <i></i><i></i><i></i><i></i><i></i>
    </div>

    <div class="au-shell" :class="{ 'au-shell-wide': wide }">
      <aside class="au-brand">
        <div class="au-brand-inner">
          <div class="au-brand-badge">
            <i></i>{{ badge }}
          </div>

          <span class="au-wordmark on-dark au-brand-mark">
            <b>ECA</b>
            <small>Escuelas de Campo</small>
          </span>

          <p class="au-brand-desc">{{ desc }}</p>

          <ul class="au-brand-list">
            <li v-for="f in features" :key="f">
              <span class="au-brand-check">
                <AuthIcon name="check" />
              </span>
              {{ f }}
            </li>
          </ul>
        </div>
      </aside>

      <main class="au-pane">
        <div class="au-card-wrap" :style="{ maxWidth: maxWidth }">
          <div class="au-card">
            <span class="au-card-mark">
              <img src="/logo.png" alt="ECA" class="au-card-logo" />
            </span>
            <slot />
          </div>
        </div>

        <p class="au-copy au-pane-copy">© 2026 ECA · Escuelas de Campo</p>
      </main>
    </div>
  </div>
</template>

<script setup>
import AuthIcon from './AuthIcon.vue'

defineProps({
  wide: { type: Boolean, default: false },
  maxWidth: { type: String, default: '410px' },
  badge: { type: String, default: 'Sistema de Escuelas de Campo' },
  desc: {
    type: String,
    default: 'Plataforma de registro de actividades en campo para técnicos de Escuelas de Campo, con soporte para trabajar sin conexión.',
  },
  features: {
    type: Array,
    default: () => ['Geolocalización de actividades', 'Evidencia fotográfica', 'Funciona sin conexión'],
  },
})
</script>
