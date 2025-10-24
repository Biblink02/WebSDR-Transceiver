<script setup lang="ts">

import {useRouter} from "vue-router";
const router = useRouter()
</script>

<template>
    <nav class="z-100 mx-auto  w-full max-w-6xl pt-4">
        <div class="rounded-lg shadow-lg px-6 py-3">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i class="pi pi-wifi text-xl text-primary"></i>
                    <span class="font-semibold text-lg">SDR</span>
                </div>
                <div class="flex items-center gap-6">

                    <Button @click="router.push('/about-us')" target="_blank" label="About Us" variant="text"/>

                    <Button as="a" href="https://github.com/Biblink02/WebSDR-Transceiver" target="_blank" label="Github" icon="pi pi-github" variant="text"/>

                    <Button @click="router.push('/')" label="Web SDR" variant="text"/>

                    <Button icon="pi pi-chart-line" rounded text plain aria-label="Activity" />
                </div>
            </div>
        </div>
    </nav>
</template>

<style scoped>

</style>
