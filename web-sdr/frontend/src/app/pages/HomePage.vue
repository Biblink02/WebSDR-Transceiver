<script setup lang="ts">
import AppLayout from '&/layouts/AppLayout.vue'
</script>

<template>
  <AppLayout>
    <div class="p-6 md:px-20 lg:px-40 xl:px-60 max-w-6xl mx-auto text-center">
      <h1 class="font-serif text-4xl md:text-5xl font-bold text-gray-800 dark:text-gray-100 mb-4">
        SatCom project
    </h1>
      <p class="text-lg text-gray-600 dark:text-gray-300">
      This project, developed by group PRI05, aims to create software for a
      ground station capable of sending and receiving data from the QO-100
      geostationary satellite. The software displays both the transmitted
      signals and the demodulated received signals, with the additional feature
      of hearing the received audio.      
    </p>
    </div>
  </AppLayout>
</template>
