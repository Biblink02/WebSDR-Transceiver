<script setup lang="ts">
import { ref } from "vue";
import Drawer from "primevue/drawer";
import {items} from "&/router";
const menuOpen = ref(false);
import logo from "~/images/logo.ico"
</script>

<template>
    <nav
        class="fixed top-0 left-0 w-full text-white font-mono font-semibold text-2xl px-2 py-4 z-50 bg-transparent"
    >
        <div class="w-full mx-auto flex items-center justify-between md:justify-center">

            <!-- Logo -->
            <div class="flex items-center gap-3 md:absolute md:left-4">
                <img :src="logo" alt="Logo" class="h-16" />
            </div>

            <!-- Desktop Menu -->
            <div class="hidden md:flex items-center space-x-6">
                <router-link
                    v-for="item in items"
                    :key="item.to"
                    :to="item.to"
                    class="px-3 py-2 transition-transform duration-300 hover:scale-125 whitespace-nowrap"
                    active-class="scale-125"
                >
                    {{ item.label }}
                </router-link>
            </div>

            <!-- Mobile Hamburger (only mobile) -->
            <button
                class="md:hidden text-white text-4xl"
                @click="menuOpen = true"
            >
                <i class="pi pi-bars"></i>
            </button>

        </div>

        <!-- Drawer -->
        <Drawer
            v-model:visible="menuOpen"
            position="right"
            :dismissable="true"
            :showCloseIcon="true"
            class="!bg-black/40 backdrop-blur-md"
        >
            <div class="flex flex-col mt-10 space-y-8 px-6">

                <router-link
                    v-for="item in items"
                    :key="item.to"
                    :to="item.to"
                    class="font-mono font-semibold text-2xl text-white px-2 py-1 transition-transform duration-200 hover:scale-110"
                    @click="menuOpen = false"
                >
                    {{ item.label }}
                </router-link>

            </div>
        </Drawer>

    </nav>
</template>
