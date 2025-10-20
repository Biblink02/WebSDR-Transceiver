<script setup lang="ts">
import { RouterView } from 'vue-router'
import {useHead} from "@unhead/vue";
import {computed} from "vue";
import darkModeFavicon from "~/images/favicon/TODO";
import favicon from "~/images/favicon/TODO";
import {useDark} from "@vueuse/core";

const isDarkMode = useDark()
const faviconHref = computed(() =>
    isDarkMode.value ? darkModeFavicon : favicon
)
useHead({
    title: "WebSDR",
    link: [
        {
            rel: 'icon',
            type: 'image/png',
            href: faviconHref
        },
    ],
    script: [
        {
            type: 'application/ld+json',
            children: {TODO
            },
        },
    ],
})
</script>

<template>
    <RouterView />
</template>
