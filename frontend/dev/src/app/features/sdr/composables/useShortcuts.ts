import { onUnmounted } from 'vue'
import { useSdrStore } from '../store'

export function useShortcuts(audio: () => void, recording: () => void) {
    const store = useSdrStore()
    function key(event: KeyboardEvent) {
        if (event.ctrlKey || event.metaKey || event.altKey || (event.target instanceof Element &&
            event.target.closest('input,select,textarea,button,[contenteditable="true"]'))) return
        const step = store.tuningStep * (event.shiftKey ? 10 : 1)
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault(); store.manualTune(store.tuneFreq + (event.key === 'ArrowRight' ? step : -step)); return
        }
        if (event.repeat) return
        switch (event.key.toLowerCase()) {
            case ' ': if (store.isConnected) { event.preventDefault(); audio() } break
            case 'r': recording(); break
            case 'b': store.saveBookmark(); break
            case 'f': store.frozen = !store.frozen; break
        }
    }
    window.addEventListener('keydown', key)
    onUnmounted(() => window.removeEventListener('keydown', key))
}
