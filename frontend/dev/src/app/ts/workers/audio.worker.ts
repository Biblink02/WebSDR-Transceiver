// NOTE: CANNOT BE USED IN HTTP BECAUSE AUDIOWORKLET NEEDS SECURECONTEXT!
//       This works well and it's tested in local.


declare class AudioWorkletProcessor {
    port: MessagePort;

    constructor(options?: { processorOptions?: Record<string, any> });

    process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>): boolean;
}

declare function registerProcessor(name: string, processorCtor: (new (options?: any) => AudioWorkletProcessor)): void;

class PCMWorkletProcessor extends AudioWorkletProcessor {
    private queue: Float32Array[];
    private offset: number;
    private isBuffering: boolean;
    private readonly bufferThreshold: number;
    private readonly maxQueueSize: number;

    constructor(options?: { processorOptions?: Record<string, any> }) {
        super(options);
        this.queue = [];
        this.offset = 0;
        this.isBuffering = true;

        // Read config passed from Main Thread via processorOptions
        const config = options?.processorOptions || {};
        this.bufferThreshold = config.bufferThreshold || 4; // Default fallback
        this.maxQueueSize = config.maxQueueSize || 50;      // Default fallback

        this.port.onmessage = (e: MessageEvent) => {
            if (e.data) {
                this.queue.push(e.data);

                // Latency protection
                if (this.queue.length > this.maxQueueSize) {
                    this.queue = this.queue.slice(-10);
                    this.offset = 0;
                }
            }
        };
    }

    process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>): boolean {
        const output = outputs[0];
        const channel = output[0];
        const outputLength = channel.length;
        let outputIndex = 0;

        // Initial Buffering (Jitter Buffer)
        if (this.isBuffering) {
            if (this.queue.length >= this.bufferThreshold) {
                this.isBuffering = false;
            } else {
                return true;
            }
        }

        // FIFO Playback Logic
        while (this.queue.length > 0 && outputIndex < outputLength) {
            const currentChunk = this.queue[0];
            const remainingInChunk = currentChunk.length - this.offset;
            const neededForOutput = outputLength - outputIndex;

            const copyAmount = Math.min(remainingInChunk, neededForOutput);

            channel.set(
                currentChunk.subarray(this.offset, this.offset + copyAmount),
                outputIndex
            );

            outputIndex += copyAmount;
            this.offset += copyAmount;

            if (this.offset >= currentChunk.length) {
                this.queue.shift();
                this.offset = 0;
            }
        }

        // Underrun Handling
        if (outputIndex < outputLength) {
            channel.fill(0, outputIndex);

            if (this.queue.length === 0) {
                this.isBuffering = true;
            }
        }

        return true;
    }
}

registerProcessor('pcm-processor', PCMWorkletProcessor);
