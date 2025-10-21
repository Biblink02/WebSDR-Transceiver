<script setup lang="ts">
import AppLayout from '&/layouts/AppLayout.vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const hovered = ref(false)

function goToSdr() {
  router.push('/sdr')
}
</script>

<template>
  <AppLayout>
    <section class="relative w-full min-h-[70vh] max-h-[80vh] flex items-center justify-center overflow-hidden rounded-lg shadow-lg select-text font-serif text-white">
      <!-- Background image cropped and centered -->
      <div
        class="absolute inset-0 bg-center bg-cover bg-no-repeat transition-opacity duration-500 rounded-lg"
        :class="hovered ? 'opacity-100' : 'opacity-40 dark:opacity-30'"
        style="background-image: url('https://www.faulhaber.com/fileadmin/_processed_/9/b/csm_aerospace-satellite_c6b0316004.jpg');"
        aria-hidden="true"
      ></div>
      <!-- Overlay for contrast -->
      <div
        class="absolute inset-0 bg-black bg-opacity-50 dark:bg-opacity-60 transition-opacity duration-500 rounded-lg"
        :class="hovered ? 'opacity-20' : 'opacity-70'"
      ></div>

      <!-- Content on top -->
      <div class="relative z-10 max-w-4xl px-6 text-center space-y-10">
        <h1 class="text-5xl font-bold drop-shadow-md">
          SatCom project
        </h1>
        <p class="text-xl drop-shadow-md">
          This project, developed by group PRI05, aims to create software for a ground station capable of sending and receiving data from the QO-100 geostationary satellite. The software displays both the transmitted signals and the demodulated received signals, with the additional feature of hearing the received audio.
        </p>
        <button
          @mouseenter="hovered = true"
          @mouseleave="hovered = false"
          @click="goToSdr"
          class="bg-nightblue hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500 focus:ring-opacity-50 rounded-lg px-20 py-5 text-2xl font-semibold shadow-lg transition-colors duration-300 mx-auto"
        >
          Start
        </button>
      </div>

    </section>
  </AppLayout>
</template>

<style scoped>
.bg-nightblue {
  background-color: #001f3f;
}
.bg-nightblue:hover {
  background-color: #003366;
}
</style>
