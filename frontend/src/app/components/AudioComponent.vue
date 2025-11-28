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
    <Button
        @click="toggle"
        :label="isPlaying ? 'Play Audio' : 'Stop Audio'"
        :severity="isPlaying ? 'success' : 'danger'"
    />
</template>

<style scoped>
</style>
