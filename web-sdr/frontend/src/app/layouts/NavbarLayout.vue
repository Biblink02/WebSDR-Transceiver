<script setup lang="ts">
</script>

<template>
  <nav class="fixed top-0 left-0 w-full z-50 bg-transparent px-6 py-4">
    <div class="max-w-[87.5rem] w-full mx-auto flex items-center">
      <!-- Logo -->
      <div class="w-40 flex justify-center">
        <img src="/resources/images/logo.ico" alt="Logo" class="h-20" />
      </div>

      <!-- Liens -->
      <div class="flex gap-x-10 ml-8">
        <router-link
          to="/"
          class="px-4 py-2 font-mono text-lg uppercase font-bold text-white/80 no-underline transition-all duration-200 hover:scale-125 hover:text-white hover:underline tracking-wider"
          exact-active-class="scale-125 text-white underline"
        >
          Our Project
        </router-link>
        <router-link
          to="/sdr"
          class="px-4 py-2 font-mono text-lg uppercase font-bold text-white/80 no-underline transition-all duration-200 hover:scale-125 hover:text-white hover:underline tracking-wider"
          active-class="scale-125 text-white underline"
        >
          SDR
        </router-link>
        <router-link
          to="/about"
          class="px-4 py-2 font-mono text-lg uppercase font-bold text-white/80 no-underline transition-all duration-200 hover:scale-125 hover:text-white hover:underline tracking-wider"
          active-class="scale-125 text-white underline"
        >
          About Us
        </router-link>
        <router-link
          to="/ressources"
          class="px-4 py-2 font-mono text-lg uppercase font-bold text-white/80 no-underline transition-all duration-200 hover:scale-125 hover:text-white hover:underline tracking-wider"
          active-class="scale-125 text-white underline"
        >
          Resources
        </router-link>
      </div>
    </div>
  </nav>
</template>


