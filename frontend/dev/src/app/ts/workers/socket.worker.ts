import { io, Socket } from 'socket.io-client';

let socket: Socket | null = null;
let processAudio = false;

// Event names fixed by backend protocol
const EVENTS = {
    GRAPHICS: 'graphics_data',
    AUDIO: 'audio_data',
    ASSIGNED: 'worker_assigned',
    RELEASED: 'worker_released',
    FULL: 'server_full',
    // Outgoing
    REQUEST_WORKER: 'request_audio_worker',
    RELEASE_WORKER: 'release_audio_worker',
    TUNE: 'tune'
};

function connectSocket(url: string) {
    if (socket) {
        socket.disconnect();
    }

    socket = io(url, {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        postStatus('CONNECTED', true);
        console.log('Worker: Socket connected');
    });

    socket.on('disconnect', () => {
        postStatus('DISCONNECTED', false);
        console.log('Worker: Socket disconnected');
    });

    socket.on('connect_error', (err) => {
        postStatus('ERROR', false);
        self.postMessage({ type: 'error', payload: err.message });
    });

    // --- High Frequency Streams ---

    socket.on(EVENTS.GRAPHICS, (rawData: ArrayBuffer) => {
        try {
            if (!rawData) return;
            // Transferable object for performance
            const data = new Float32Array(rawData);
            self.postMessage(
                { type: 'graphicData', payload: data },
                { transfer: [data.buffer] }
            );
        } catch (e) {
            console.error("Worker: Graphics error", e);
        }
    });

    socket.on(EVENTS.AUDIO, (rawData: ArrayBuffer) => {

        try {
            if (!rawData || !processAudio) return;
            // Transferable object
            const data = new Float32Array(rawData);
            console.log("Right Audio");
            self.postMessage(
                { type: 'audioData', payload: data },
                { transfer: [data.buffer] }
            );
        } catch (e) {
            console.error("Worker: Audio error", e);
        }
    });

    // --- Control Events ---

    socket.on(EVENTS.ASSIGNED, (data) => {
        self.postMessage({ type: 'workerAssigned', payload: data });
    });

    socket.on(EVENTS.RELEASED, () => {
        self.postMessage({ type: 'workerReleased' });
    });

    socket.on(EVENTS.FULL, () => {
        self.postMessage({ type: 'serverFull' });
    });
}

function postStatus(status: string, isConnected: boolean) {
    self.postMessage({
        type: 'status',
        payload: { status, isConnected }
    });
}

self.onmessage = (event: MessageEvent) => {
    const { type, payload } = event.data;

    switch (type) {
        case 'init':
            postStatus('CONNECTING', false);
            connectSocket(payload.wsUrl);
            break;

        case 'disconnect':
            socket?.disconnect();
            break;

        case 'toggleAudio':
            processAudio = payload; // payload is boolean
            break;

        // --- Outgoing Commands ---

        case 'requestWorker':
            // payload: { freq: number, bw: number }
            socket?.emit(EVENTS.REQUEST_WORKER, payload);
            processAudio = true;
            break;

        case 'releaseWorker':
            socket?.emit(EVENTS.RELEASE_WORKER);
            processAudio = false;
            break;

        case 'tune':
            // payload is { freq: number, bw: number }
            socket?.emit(EVENTS.TUNE, payload);
            break;
    }
};

export {};
