<script lang="ts" setup>
import {items} from "&/router";
</script>

<template>
    <footer class="mt-16 py-12 w-full border-t border-white/20 bg-black/30">
        <div class="w-full max-w-[1400px] mx-auto px-8">
            <div class="flex flex-col items-center justify-between gap-8 md:flex-row">

                <!-- Left -->
                <div class="text-center md:text-left md:flex-1">
                    <h2 class="font-mono text-2xl font-bold uppercase text-white tracking-[2px] m-0">
                        SatCom Project
                    </h2>
                    <p class="font-mono text-[0.95rem] uppercase text-white/80 mt-2 tracking-wide">
                        Developed by <span class="font-semibold text-white">PRI05</span>
                    </p>
                </div>

                <!-- Center -->
                <div
                    class="flex flex-wrap md:flex-nowrap justify-center gap-x-10 gap-y-4 md:flex-1 md:justify-center text-center"
                >
                    <router-link
                        v-for="item in items"
                        :key="item.to"
                        :to="item.to"
                        class="font-mono text-base uppercase text-white/80 no-underline whitespace-nowrap transition-colors tracking-wide hover:text-white hover:underline"
                    >
                        {{ item.label }}
                    </router-link>
                </div>


                <!-- Right -->
                <div class="text-center md:text-right md:flex-1">
                    <p class="font-mono text-sm uppercase text-white/70 tracking-wide m-0">
                        © {{ new Date().getFullYear() }} PRI05
                    </p>
                </div>

            </div>
        </div>
    </footer>
</template>
