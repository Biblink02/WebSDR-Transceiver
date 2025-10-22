import { io, Socket } from 'socket.io-client';
import { fft, magDb } from '@thi.ng/dsp';

let socket: Socket | null = null;
let wsUrl = '';
let wsEvent = '';


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
            payload: { status: 'CONNECTED', isConnected: true }
        });
        console.log('Worker: Socket.IO connected');
    });

    socket.on('disconnect', () => {
        self.postMessage({
            type: 'status',
            payload: { status: 'DISCONNECTED', isConnected: false }
        });
        console.log('Worker: Socket.IO disconnected');
    });

    socket.on('connect_error', (err) => {
        self.postMessage({
            type: 'status',
            payload: { status: 'ERROR', isConnected: false }
        });
        self.postMessage({ type: 'error', payload: err.message });
        console.error('Worker: Socket.IO connection error:', err.message);
    });

    socket.on(wsEvent, (rawData) => {
        if (!rawData) return;

        try {
            let timeDomainData: Float32Array;
            if (rawData instanceof ArrayBuffer) {
                timeDomainData = new Float32Array(rawData);
            } else if (Array.isArray(rawData)) {
                timeDomainData = Float32Array.from(rawData);
            } else {
                return;
            }

            if (timeDomainData.length === 0) return;

            processForGraphic(timeDomainData);
            processForAudio(timeDomainData);

        } catch (e) {
            self.postMessage({ type: 'error', payload: (e as Error).message });
            console.error("Worker: Error processing raw data:", e);
        }
    });
}

function processForGraphic(timeDomainData: Float32Array): void {
    // No check for the
    const spectrum = fft(timeDomainData);
    const magnitudesDb = magDb(spectrum);
    const fftResult = magnitudesDb.slice(0, magnitudesDb.length / 2);

    self.postMessage({
        type: 'fftData',
        payload: fftResult
    }, [fftResult.buffer]);
}

//TODO lorenzo

function processForAudio(timeDomainData: Float32Array): void {
    const audioSamples = null; //TODO
    self.postMessage({
        type: 'audioData',
        payload: audioSamples
    }, [audioSamples.buffer]);
}


// Listener principale del Worker: gestisce i COMANDI dal Main Thread
self.onmessage = (event: MessageEvent) => {
    const { type, payload } = event.data;

    switch (type) {
        case 'init':
            wsUrl = payload.wsUrl;
            wsEvent = payload.wsEvent;
            self.postMessage({
                type: 'status',
                payload: { status: 'CONNECTING', isConnected: false }
            });
            connectSocket();
            break;

        case 'toggleConnection':
            if (socket?.connected) {
                socket.disconnect();
            } else {
                connectSocket();
            }
            break;

        case 'disconnect':
            socket?.disconnect();
            break;
    }
};

// Export for being treated as a module
export {};
