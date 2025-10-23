import { io, Socket } from 'socket.io-client';
import { fft } from '@thi.ng/dsp';

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
    const N = timeDomainData.length / 2; // N = 1024

    const real = new Float32Array(N);
    const imag = new Float32Array(N);

    for (let i = 0; i < N; i++) {
        real[i] = timeDomainData[i * 2];
        imag[i] = timeDomainData[i * 2 + 1];
    }
    const fftData = fft([real, imag]);
    self.postMessage(
        {type:'fftData', payload: fftData},
        {transfer: fftData}
    )

}
function processForAudio(timeDomainData: Float32Array): void {
    //TODO
}


// Worker listener
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
