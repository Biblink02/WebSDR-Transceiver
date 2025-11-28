import {io, Socket} from 'socket.io-client';

let socket: Socket | null = null;
let wsUrl = '';
let processAudio = false;

let wsEventGraphics = 'graphics_data';
let wsEventAudio = 'update_audio';
let wsEventFrequency = 'update_frequency';

function connectSocket() {
    if (socket) {
        socket.disconnect();
    }

    socket = io(wsUrl, {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        self.postMessage({
            type: 'status',
            payload: {status: 'CONNECTED', isConnected: true}
        });
        console.log('Worker: Socket.IO connected');
    });

    socket.on('disconnect', () => {
        self.postMessage({
            type: 'status',
            payload: {status: 'DISCONNECTED', isConnected: false}
        });
        console.log('Worker: Socket.IO disconnected');
    });

    socket.on('connect_error', (err) => {
        self.postMessage({
            type: 'status',
            payload: {status: 'ERROR', isConnected: false}
        });
        self.postMessage({type: 'error', payload: err.message});
        console.error('Worker: Socket.IO connection error:', err.message);
    });

    socket.on(wsEventGraphics, (rawData: ArrayBuffer) => {
        try {
            if (!rawData) return;
            const graphicData = new Float32Array(rawData);
            self.postMessage(
                {type: 'graphicData', payload: graphicData},
                {transfer: [graphicData.buffer]}
            );
        } catch (e) {
            self.postMessage({type: 'error', payload: (e as Error).message});
            console.error("Worker: Error processing graphics data:", e);
        }
    });

    socket.on(wsEventAudio, (rawData: ArrayBuffer) => {
        try {
            if (!rawData || !processAudio) return;
            const audioData = new Float32Array(rawData);
            self.postMessage(
                {type: 'audioData', payload: audioData},
                {transfer: [audioData.buffer]}
            );
        } catch (e) {
            self.postMessage({type: 'error', payload: (e as Error).message});
            console.error("Worker: Error processing audio data:", e);
        }
    });
}


self.onmessage = (event: MessageEvent) => {
    const {type, payload} = event.data;

    switch (type) {
        case 'init':
            wsUrl = payload.wsUrl;
            wsEventAudio = payload.wsEventAudio || 'update_audio';
            wsEventGraphics = payload.wsEventGraphics || 'update_graphics'
            wsEventFrequency = payload.wsEventFrequency || 'update_frequency'
            self.postMessage({
                type: 'status',
                payload: {status: 'CONNECTING', isConnected: false}
            });
            connectSocket();
            break;

        case 'toggleConnection':
            socket?.connected ? socket.disconnect() : connectSocket();
            break;

        case 'disconnect':
            socket?.disconnect();
            break;

        case 'toggleAudio':
            processAudio = !processAudio;
            break;

        case 'updateFrequency':
            socket?.emit(wsEventFrequency, payload)
            break;
    }
};

export {};
