<script setup lang="ts">
</script>

<template>
  <nav class="fixed top-0 left-0 w-full text-white font-serif font-semibold text-2xl px-1 py-4 z-50">
    <div class="max-w-full w-full mx-auto flex items-center">
      <div class="w-48 flex justify-center">
        <img src="/resources/images/logo.ico" alt="Logo" class="h-16" />
      </div>
      <div class="flex space-x-6 ml-0 flex-1 justify-center">
        <router-link
        to="/"
        class="px-3 py-2 transition-transform duration-300 hover:scale-125 whitespace-nowrap"
        exact-active-class="scale-125"
      >
        Our project
      </router-link>
      <router-link
        to="/sdr"
        class="px-3 py-2 transition-transform duration-300 hover:scale-125 whitespace-nowrap"
        active-class="scale-125"
      >
        SDR
      </router-link>
      <router-link
        to="/about"
        class="px-3 py-2 transition-transform duration-300 hover:scale-125 whitespace-nowrap"
        active-class="scale-125"
      >
        About us
      </router-link>
      <router-link
        to="/ressources"
        class="px-3 py-2 transition-transform duration-300 hover:scale-125 whitespace-nowrap"
        active-class="scale-125"
      >
        Resources
      </router-link>
      <router-link
        to="/satellite-tracker"
        class="px-3 py-2 transition-transform duration-300 hover:scale-125 whitespace-nowrap"
        active-class="scale-125"
      >
        Satellite Tracker
      </router-link>
      </div>
    </div>
  </nav>
</template>