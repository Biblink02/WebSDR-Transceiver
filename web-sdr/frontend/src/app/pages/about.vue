<script setup lang="ts">
import AppLayout from '&/layouts/AppLayout.vue'

const teamMembers = [
  {
    id: 1,
    name: "Alberto",
    country: "italy",
    role: "Computer Science Student",
    description: "Alice builds and tests the 2.4 GHz SSB Modulated transmitter and develops signal visualization.",
    thumbnail: "https://fr.web.img5.acsta.net/c_310_420/pictures/19/06/05/12/04/5240675.jpg"},
  {
    id: 2,
    name: "vedant",
    country: "germany",
    role: "Computer Science Student",
    description: "Bob develops the receiver and WebSDR frontend for real-time waterfall and audio streaming.",
    thumbnail: "https://fr.web.img5.acsta.net/c_310_420/pictures/19/06/05/12/04/5240675.jpg"
  },
  {
    id: 3,
    name: "Alexandre",
    country: "france",
    role: "Computer Science Student",
    description: "Claire implements real-time signal processing and integration between receiver and web interface.",
    thumbnail: "https://fr.web.img5.acsta.net/c_310_420/pictures/19/06/05/12/04/5240675.jpg"
  },
  {
    id: 4,
    name: "Lorenzo",
    country: "italy",
    role: "Computer Science Student",
    description: "David designs the intuitive frontend for carrier frequency configuration and filter bandwidth control.",
    thumbnail: "https://fr.web.img5.acsta.net/c_310_420/pictures/19/06/05/12/04/5240675.jpg"
  },
  {
    id: 5,
    name: "Fatemah",
    country: "italy",
    role: "Computer Science Student",
    description: "Elena ensures the reliability of transmitter and receiver with PlutoSDR devices via thorough testing.",
    thumbnail: "data:image/jpeg;base64,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"
  },
  {
    id: 6,
    name: "Mihir",
    country: "germany",
    role: "Computer Science Student",
    description: "Firas manages deployment and integration between hardware and software components for the ground station.",
    thumbnail: "https://fr.web.img5.acsta.net/c_310_420/pictures/19/06/05/12/04/5240675.jpg"
  },
  {
    id: 7,
    name: "Clément",
    country: "france",
    role: "Computer Science Student",
    description: "Grace documents the project progress and supports communication between teams.",
    thumbnail: "https://fr.web.img5.acsta.net/c_310_420/pictures/19/06/05/12/04/5240675.jpg"
  }
]

// Map country codes to flag image URLs
const flagUrls = {
  italy: 'https://flagcdn.com/w40/it.png',
  germany: 'https://flagcdn.com/w40/de.png',
  france: 'https://flagcdn.com/w40/fr.png',
}
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto p-6 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-serif">
      <h1 class="text-5xl font-bold mb-14 text-center select-none">
        Meet Our Team
      </h1>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-12">
        <div
          v-for="member in teamMembers"
          :key="member.id"
          class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 flex flex-col items-center text-center transform transition-transform hover:scale-105 motion-safe:animate-fadeIn"
          style="animation-delay: calc(var(--delay) * 100ms)"
          :style="{'--delay': member.id}"
        >
          <img
            :src="member.thumbnail"
            :alt="`Photo of ${member.name}`"
            class="w-48 h-48 rounded-full object-cover mb-6 border-4 border-favourite_yellow shadow-md"
          />
          <div class="flex items-center justify-center space-x-3 mb-1">
            <h2 class="text-2xl font-semibold text-favourite_yellow select-text">
              {{ member.name }}
            </h2>
            <img
              v-if="flagUrls[member.country]"
              :src="flagUrls[member.country]"
              alt="Country flag"
              class="w-8 h-6 rounded-sm shadow-md"
              :title="member.country.charAt(0).toUpperCase() + member.country.slice(1)"
              loading="lazy"
            />
          </div>
          <h3 class="italic text-lg mb-3 text-gray-700 dark:text-gray-300 select-text">
            {{ member.role }}
          </h3>
          <p class="text-gray-700 dark:text-gray-300 leading-relaxed select-text max-w-md">
            {{ member.description }}
          </p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.motion-safe\:animate-fadeIn {
  animation-name: fadeIn;
  animation-duration: 0.6s;
  animation-fill-mode: both;
  animation-timing-function: ease-in-out;
}

.text-favourite_yellow {
  color: #dbb01f;
}
</style>
