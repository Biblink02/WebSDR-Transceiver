<script setup lang="ts">
// No additional logic needed
</script>

<template>
  <footer class="mt-12 py-8 border-t border-gray-200 dark:border-gray-700">
    <div class="w-full">
      <div class="flex flex-col md:flex-row justify-between items-center space-y-6 md:space-y-0">

        <!-- Left section: Project name and description -->
        <div class="text-center md:text-left">
          <h2 class="font-serif text-2xl font-bold text-gray-800 dark:text-gray-100">
            SatCom Project
          </h2>
          <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
            Developed with passion by the <span class="font-semibold">PRI05</span> team
          </p>
        </div>

        <!-- Center section: Useful links -->
        <div class="flex space-x-6">
          <router-link
            to="/"
            class="font-serif font-semibold text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100 transition-colors"
          >
            Home
          </router-link>
          <router-link
            to="/sdr"
            class="font-serif font-semibold text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100 transition-colors"
          >
            SDR
          </router-link>
          <router-link
            to="/about"
            class="font-serif font-semibold text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100 transition-colors"
          >
            About
          </router-link>
          <router-link
            to="/resources"
            class="font-serif font-semibold text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100 transition-colors"
          >
            Resources
          </router-link>
        </div>

        <!-- Right section: Copyright and legal notice -->
        <div class="text-sm text-gray-500 dark:text-gray-400 text-center md:text-right">
          <p>© {{ new Date().getFullYear() }} PRI05. All rights reserved.</p>
          <router-link
            to="/legal-notice"
            class="hover:underline transition-colors"
          >
            Legal Notice
          </router-link>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
/* Specific styles if needed */
footer {
  width: 100%;
}
</style>



