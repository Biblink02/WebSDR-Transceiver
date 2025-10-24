<script setup lang="ts">
import {ref, onMounted, watch} from 'vue';
import {playAudio} from "@/AudioPlayer";


// --- Props ---
const props = defineProps({
    samples: {
        type: [Float32Array, Array],
        default: () => null
    },
});
const emits = defineEmits(['toggleAudio']);

watch(() => props.samples, (newSamples) => {
    playAudio(newSamples, 1024);
});



</script>

<template>
    <Button class="cursor-pointer mt-6 mx-auto" @click="emits('toggleAudio')">Toggle Audio</Button>
</template>

<style scoped>

</style>
