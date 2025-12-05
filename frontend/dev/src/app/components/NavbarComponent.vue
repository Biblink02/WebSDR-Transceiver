<script lang="ts" setup>

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

                    <Button label="About Us" target="_blank" variant="text" @click="router.push('/about-us')"/>

                    <Button as="a" href="https://github.com/Biblink02/WebSDR-Transceiver" icon="pi pi-github" label="Github"
                            target="_blank" variant="text"/>

                    <Button label="Web SDR" variant="text" @click="router.push('/')"/>

                    <Button aria-label="Activity" icon="pi pi-chart-line" plain rounded text/>
                </div>
            </div>
        </div>
    </nav>
</template>

<style scoped>

</style>
