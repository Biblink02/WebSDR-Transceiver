<script setup lang="ts">
import { useSdrStore } from '../store'
const store = useSdrStore()
</script>
<template>
    <section class="panel bookmark-panel">
        <div class="section-title">SAVED FREQUENCIES <span>THIS BROWSER</span></div>
        <p class="muted fine-print" v-if="!store.bookmarks.length">Save a frequency from the tuning panel to return to it later.</p>
        <div class="bookmark-row" v-for="(item, index) in store.bookmarks" :key="item.frequency">
            <button @click="store.selectBand(item.band, item.frequency); store.setMode(item.mode); store.manualTune(item.frequency, item.bandwidth, item.side)">
                {{ ((item.frequency + store.settings.lnb_lo_freq) / 1e6).toFixed(5) }} MHz
                <small>{{ item.mode === 'cw' ? 'CW' : item.side > 0 ? 'USB' : 'LSB' }} · {{ item.bandwidth }} Hz</small>
            </button>
            <button :aria-label="'Remove saved frequency ' + (index + 1)" @click="store.bookmarks.splice(index, 1)"><i aria-hidden="true" class="pi pi-times"/></button>
        </div>
    </section>
</template>
<style scoped>
.bookmark-panel { padding:20px; }
p { margin-top:14px; }
.bookmark-row { display:flex; justify-content:space-between; align-items:center; gap:10px; margin-top:10px; }
.bookmark-row button:first-child { flex:1; text-align:left; font:12px monospace; }
.bookmark-row small { display:block; font:10px sans-serif; color:var(--muted); margin-top:4px; }
</style>
