<script setup lang="ts">
import {ref, onMounted, watch} from 'vue';
import {playAudio} from "@/AudioPlayer";


// --- Props ---
const props = defineProps({
    samples: {
        type: [Float32Array, Array],
        default: () => null
    }
});


watch(() => props.samples, (newSamples) => {
    playAudio(newSamples, 1024);
});



</script>

<template>
<div></div>
</template>

<style scoped>

</style>
