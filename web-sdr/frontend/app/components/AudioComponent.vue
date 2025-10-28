<script setup lang="ts">
import { ref } from 'vue';
import { startAudioPlayback, stopAudioPlayback } from "@/AudioPlayer";

const emits = defineEmits(['toggleAudio']);
const isPlaying = ref(false);

function toggle() {
    isPlaying.value = !isPlaying.value;

    isPlaying.value ? startAudioPlayback() : stopAudioPlayback();

    emits('toggleAudio', isPlaying.value);
}
</script>

<template>
    <Button class="cursor-pointer mt-6 mx-auto" @click="toggle">
        {{ isPlaying ? 'Stop Audio' : 'Play Audio' }}
    </Button>
</template>

<style scoped>
</style>
