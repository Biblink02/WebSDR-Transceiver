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
      <div class="relative flex-1 w-full min-h-screen">
        <div class="flex items-center justify-center min-h-screen p-4">
          <div class="max-w-4xl w-full text-center space-y-8">
            <h1 class="text-5xl font-bold text-white drop-shadow-lg">
              SatCom project
            </h1>
            <p class="text-xl text-white drop-shadow-md leading-relaxed">
              This project, developed by group PRI05, aims to create software for a ground station capable of sending and receiving data from the QO-100 geostationary satellite. The software displays both the transmitted signals and the demodulated received signals, with the additional feature of hearing the received audio.
            </p>
            <button
              @mouseenter="hovered = true"
              @mouseleave="hovered = false"
              @click="goToSdr"
              class="mt-8 bg-blue-600/50 hover:bg-blue-700/70 text-white focus:outline-none focus:ring-4 focus:ring-blue-500/50 rounded-lg px-12 py-4 text-2xl font-semibold shadow-lg transition-all duration-300 backdrop-blur-sm"
            >
              Start
            </button>
          </div>
        </div>
    </div>
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
