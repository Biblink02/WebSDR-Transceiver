<script setup lang="ts">
</script>

<template>
  <nav class="fixed top-0 left-0 w-full bg-nightblue text-white font-serif font-semibold text-2xl px-6 py-4 z-50 shadow-md">
    <div class="max-w-7xl w-full mx-auto flex space-x-12">
      <router-link
        to="/"
        class="px-4 py-2 rounded-md border-2 border-transparent hover:border-blue-400 transition-colors duration-300"
        exact-active-class="border-blue-400"
      >
        Our project
      </router-link>
      <router-link
        to="/sdr"
        class="px-4 py-2 rounded-md border-2 border-transparent hover:border-blue-400 transition-colors duration-300"
        active-class="border-blue-400"
      >
        SDR
      </router-link>
      <router-link
        to="/about"
        class="px-4 py-2 rounded-md border-2 border-transparent hover:border-blue-400 transition-colors duration-300"
        active-class="border-blue-400"
      >
        About us
      </router-link>
      <router-link
        to="/ressources"
        class="px-4 py-2 rounded-md border-2 border-transparent hover:border-blue-400 transition-colors duration-300"
        active-class="border-blue-400"
      >
        Resources
      </router-link>
    </div>
  </nav>
</template>

<style scoped>
.bg-nightblue {
  background-color: #001f3f;
}
</style>
