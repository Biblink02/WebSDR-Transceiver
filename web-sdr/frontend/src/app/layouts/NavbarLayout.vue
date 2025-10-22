<script setup lang="ts">
</script>

<template>
  <nav class="fixed top-0 left-0 w-full text-white font-serif font-semibold text-2xl px-6 py-4 z-50">
    <div class="max-w-7xl w-full mx-auto flex items-center">
      <div class="w-64 flex justify-center">
        <img src="/resources/images/logo.ico" alt="Logo" class="h-20" />
      </div>
      <div class="flex space-x-12 ml-8">
        <router-link
        to="/"
        class="px-4 py-2 transition-transform duration-300 hover:scale-125"
        exact-active-class="scale-125"
      >
        Our project
      </router-link>
      <router-link
        to="/sdr"
        class="px-4 py-2 transition-transform duration-300 hover:scale-125"
        active-class="scale-125"
      >
        SDR
      </router-link>
      <router-link
        to="/about"
        class="px-4 py-2 transition-transform duration-300 hover:scale-125"
        active-class="scale-125"
      >
        About us
      </router-link>
      <router-link
        to="/ressources"
        class="px-4 py-2 transition-transform duration-300 hover:scale-125"
        active-class="scale-125"
      >
        Resources
      </router-link>
      </div>
    </div>
  </nav>
</template>

