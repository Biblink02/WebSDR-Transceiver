import { io, Socket } from 'socket.io-client';

let socket: Socket | null = null;
let processAudio = false;
let EVENTS: Record<string, string> = {};

function connectSocket(url: string) {
    if (socket) {
        socket.disconnect();
    }

    socket = io(url, {
        transports: ['websocket', 'polling']
    });

    socket.on(EVENTS.WS_CONNECT_EVENT, () => {
        postStatus('CONNECTED', true);
        console.log('Worker: Socket connected');
    });

    socket.on(EVENTS.WS_DISCONNECT_EVENT, () => {
        postStatus('DISCONNECTED', false);
        console.log('Worker: Socket disconnected');
    });

    socket.on('connect_error', (err) => {
        postStatus('ERROR', false);
        self.postMessage({ type: 'error', payload: err.message });
    });

    socket.on(EVENTS.WS_GRAPHICS_EVENT, (rawData: ArrayBuffer) => {
        try {
            if (!rawData) return;
            const data = new Float32Array(rawData);
            self.postMessage(
                { type: 'graphicData', payload: data },
                { transfer: [data.buffer] }
            );
        } catch (e) {
            console.error("Worker: Graphics error", e);
        }
    });

    socket.on(EVENTS.WS_AUDIO_EVENT, (rawData: ArrayBuffer) => {
        try {
            if (!rawData || !processAudio) return;
            const data = new Float32Array(rawData);
            self.postMessage(
                { type: 'audioData', payload: data },
                { transfer: [data.buffer] }
            );
        } catch (e) {
            console.error("Worker: Audio error", e);
        }
    });

    socket.on(EVENTS.WS_WORKER_ASSIGNED_EVENT, (data) => {
        self.postMessage({ type: 'workerAssigned', payload: data });
    });

    socket.on(EVENTS.WS_WORKER_RELEASED_EVENT, () => {
        self.postMessage({ type: 'workerReleased' });
    });

    socket.on(EVENTS.WS_SERVER_FULL_EVENT, () => {
        self.postMessage({ type: 'serverFull' });
    });

    socket.on(EVENTS.WS_CORRECTION_EVENT, (data) => {
        self.postMessage({ type: 'correctionApplied', payload: data });
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
            EVENTS = payload.events;
            postStatus('CONNECTING', false);
            connectSocket(payload.wsUrl);
            break;

        case 'disconnect':
            socket?.disconnect();
            break;

        case 'toggleAudio':
            processAudio = payload;
            break;

        case 'requestWorker':
            socket?.emit(EVENTS.WS_REQUEST_WORKER_EVENT, payload);
            processAudio = true;
            break;

        case 'releaseWorker':
            socket?.emit(EVENTS.WS_DISMISS_WORKER_EVENT);
            processAudio = false;
            break;

        case 'tune':
            socket?.emit(EVENTS.WS_TUNE_EVENT, payload);
            break;
    }
};

export {};
