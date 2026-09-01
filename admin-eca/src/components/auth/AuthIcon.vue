<!-- pwa-eca — iconos de línea para las pantallas de autenticación (ECA-020).
     Trazo vectorial, sin emojis, mismo set visual que `pwasuper`. -->
<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"
       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'mail'">
      <rect x="2" y="4" width="20" height="16" rx="2.5" />
      <path d="M2.5 7 12 13.2 21.5 7" />
    </template>
    <template v-else-if="name === 'lock'">
      <rect x="3.5" y="10.5" width="17" height="11" rx="2.5" />
      <path d="M7.5 10.5V7a4.5 4.5 0 0 1 9 0v3.5" />
    </template>
    <template v-else-if="name === 'user'">
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 20.5a7.5 7.5 0 0 1 15 0" />
    </template>
    <template v-else-if="name === 'phone'">
      <rect x="6" y="2.5" width="12" height="19" rx="3" />
      <path d="M11 18.5h2" />
    </template>
    <template v-else-if="name === 'edit'">
      <path d="M11 4.5H5.5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V13" />
      <path d="M17.9 3.1a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4z" />
    </template>
    <template v-else-if="name === 'check'">
      <circle cx="12" cy="12" r="9.2" />
      <path d="M8.2 12.2l2.6 2.6 5-5" />
    </template>
    <template v-else-if="name === 'alert'">
      <circle cx="12" cy="12" r="9.2" />
      <path d="M12 7.6v5M12 16.2h.01" />
    </template>
    <template v-else-if="name === 'eye'">
      <path d="M1.8 12S6 4.5 12 4.5 22.2 12 22.2 12 18 19.5 12 19.5 1.8 12 1.8 12z" />
      <circle cx="12" cy="12" r="3" />
    </template>
    <template v-else-if="name === 'eye-off'">
      <path d="M17.9 17.9A10 10 0 0 1 12 19.5C6 19.5 1.8 12 1.8 12a18.4 18.4 0 0 1 5-5.9M9.9 4.8A9.1 9.1 0 0 1 12 4.5c6 0 10.2 7.5 10.2 7.5a18.5 18.5 0 0 1-2.1 3.2m-6.7-1.1a3 3 0 0 1-4.2-4.2" />
      <path d="M2 2l20 20" />
    </template>
    <template v-else-if="name === 'arrow-right'">
      <path d="M4.5 12h15M13 5.5l6.5 6.5-6.5 6.5" stroke-width="2.2" />
    </template>
    <template v-else-if="name === 'arrow-left'">
      <path d="M19.5 12h-15M11 5.5 4.5 12l6.5 6.5" stroke-width="2.2" />
    </template>
    <template v-else-if="name === 'wifi-off'">
      <path d="M2 2l20 20" />
      <path d="M8.8 15.6a4.6 4.6 0 0 1 6.4 0M5.2 12a9.4 9.4 0 0 1 3.4-2.2M18.8 12a9.4 9.4 0 0 0-3-2.1M2.2 8.5A14.6 14.6 0 0 1 7 5.6M21.8 8.5a14.6 14.6 0 0 0-8.4-3" />
      <path d="M12 19.2h.01" />
    </template>
    <template v-else-if="name === 'map-pin'">
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
      <circle cx="12" cy="10" r="2.8" />
    </template>
    <template v-else-if="name === 'clipboard'">
      <rect x="5.5" y="4.5" width="13" height="17" rx="2.2" />
      <path d="M9 4.5V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1.5" />
      <path d="M9 12h6M9 16h6" />
    </template>
    <template v-else-if="name === 'shield-check'">
      <path d="M12 21.5s7.5-3.6 7.5-9.3V5.4L12 2.5 4.5 5.4v6.8c0 5.7 7.5 9.3 7.5 9.3z" />
      <path d="M9 12l2.2 2.2L15.2 10" />
    </template>
    <template v-else-if="name === 'home'">
      <path d="M3.5 11 12 3.5 20.5 11" />
      <path d="M5.5 9.5V20a1 1 0 0 0 1 1H9v-5.5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1V21h2.5a1 1 0 0 0 1-1V9.5" />
    </template>
    <template v-else-if="name === 'map'">
      <path d="M9 4.5 4 6.3v13.2l5-1.8 6 1.8 5-1.8V4.5l-5 1.8-6-1.8z" />
      <path d="M9 4.5v13.2M15 6.3v13.2" />
    </template>
    <template v-else-if="name === 'school'">
      <path d="M12 3 2 8l10 5 10-5-10-5z" />
      <path d="M6 10.3V16c0 1.5 2.7 3.5 6 3.5s6-2 6-3.5v-5.7" />
      <path d="M22 8v6" />
    </template>
    <template v-else-if="name === 'shield'">
      <path d="M12 21.5s7.5-3.6 7.5-9.3V5.4L12 2.5 4.5 5.4v6.8c0 5.7 7.5 9.3 7.5 9.3z" />
    </template>
    <template v-else-if="name === 'check-circle'">
      <circle cx="12" cy="12" r="9.2" />
      <path d="M8.2 12.2l2.6 2.6 5-5" />
    </template>
    <template v-else-if="name === 'book'">
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5v-16z" />
      <path d="M4 19a2.5 2.5 0 0 1 2.5-2.5H20" />
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="12" cy="12" r="9.2" />
      <path d="M12 7.5V12l3.2 2" />
    </template>
    <template v-else-if="name === 'user-plus'">
      <circle cx="9.5" cy="8" r="4" />
      <path d="M2.5 20.5a7 7 0 0 1 14 0" />
      <path d="M18.5 8v6M15.5 11h6" />
    </template>
    <template v-else-if="name === 'logout'">
      <path d="M9 21H5.5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2H9" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </template>
    <template v-else-if="name === 'close'">
      <path d="M18 6 6 18M6 6l12 12" />
    </template>
    <template v-else-if="name === 'inbox'">
      <path d="M3 12h4.5l1.2 3h6.6l1.2-3H21" />
      <path d="M5.5 5h13l2.5 7v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-7z" />
    </template>
  </svg>
</template>

<script setup>
defineProps({ name: { type: String, required: true } })
</script>

<style scoped>
svg { display: block; }
</style>
