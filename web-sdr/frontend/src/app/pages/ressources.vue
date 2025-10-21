<script setup lang="ts">
import AppLayout from '&/layouts/AppLayout.vue'

const resources = [
  {
    id: 1,
    title: "Es'hail NB (Narrow Band)",
    url: "https://eshail.batc.org.uk/nb/",
    description: `This site provides an example of a ground station and a GUI to configure the transmitter in the 2.4 GHz band with features like bandwidth control 
      (max 7.35 kHz). A practical source for designing the SSB modulation transmitter the France team must build.`,
    thumbnail: "https://wiki.batc.org.uk/images/thumb/5/50/GH_view.JPG/600px-GH_view.JPG"
  },
  {
    id: 2,
    title: "Es'hail-2 Ground Station Wiki",
    url: "https://wiki.batc.org.uk/Es%27hail-2_Ground_Station",
    description: `Detailed wiki describing the Es'hail-2 ground station. Very useful to understand the full architecture and used components, 
      including SSB modulation, reception, and transmission. A key reference for software and hardware design.`,
    thumbnail: "https://wiki.batc.org.uk/images/thumb/4/40/GHY_Software_Block_V1.jpg/900px-GHY_Software_Block_V1.jpg"
  },
  {
    id: 3,
    title: "QO-100 WebSDR Overview (AMSAT-DL Wiki)",
    url: "https://wiki.amsat-dl.org/doku.php?id=en:qo100websdr:overview",
    description: `Comprehensive documentation on WebSDR for QO-100 reception. Helps understand real-time reception functionalities and the desired web interface 
      (waterfall plot, frequency control, sound, etc.) to develop.`,
    thumbnail: "https://wiki.amsat-dl.org/lib/exe/fetch.php?w=400&tok=c96144&media=de:qo100websdr:c4.png"
  },
  {
    id: 4,
    title: "QO100 Transceiver GitHub",
    url: "https://github.com/dj0abr/QO100_Transceiver",
    description: `Source code of a QO-100 transceiver developed for Raspberry Pi. Useful to understand which Linux libraries are used, modular code, 
      and SSB functions implemented on Linux platforms.`,
    thumbnail: "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
  },
  {
    id: 5,
    title: "Linux Setup Scripts for PlutoSDR",
    url: "https://github.com/dj0abr/QO100_Transceiver/blob/main/scripts/prepare_ubuntu_pluto",
    description: `Installation script for preparing an Ubuntu system with PlutoSDR for transmission and reception. Facilitates software deployment and lists dependencies.`,
    thumbnail: "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
  }
]
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto p-15 space-y-10 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <h1 class="text-5xl font-bold mb-14 text-center select-none">
        Resources
      </h1>

      <div v-for="resource in resources" :key="resource.id" class="flex items-center space-x-6 bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <a :href="resource.url" target="_blank" class="flex-shrink-0 w-40 h-28 overflow-hidden rounded-md border border-gray-300 dark:border-gray-700">
          <img :src="resource.thumbnail" alt="Thumbnail" class="object-cover w-full h-full" />
        </a>
        <div class="flex-1">
          <a :href="resource.url" target="_blank" class="text-2xl font-semibold hover:underline text-dark-blue">
            {{ resource.title }}
          </a>
          <p class="mt-2 text-gray-700 dark:text-gray-300 leading-relaxed">
            {{ resource.description }}
          </p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.text-favourite_yellow {
  color: #dbb01f;
}
</style>
