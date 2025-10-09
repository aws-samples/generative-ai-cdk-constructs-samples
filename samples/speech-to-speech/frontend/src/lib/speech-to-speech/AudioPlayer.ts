/**
 * Audio player for speech-to-speech functionality
 */

import ObjectExt from "./ObjectsExt";

// AudioPlayerProcessor worklet code as a string
const audioPlayerProcessorCode = `
class AudioPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.isPlaying = false;
    this.port.onmessage = this.handleMessage.bind(this);
  }

  handleMessage(event) {
    const data = event.data;
    switch (data.type) {
      case "audio":
        this.buffer.push(...data.audioData);
        if (!this.isPlaying) {
          this.isPlaying = true;
        }
        break;
      case "barge-in":
        this.buffer = [];
        this.isPlaying = false;
        break;
      case "initial-buffer-length":
        // Optional: Set initial buffer length
        break;
      default:
        console.error("Unknown message type:", data.type);
    }
  }

  process(inputs, outputs) {
    const output = outputs[0];
    const channel = output[0];
    
    if (this.isPlaying && this.buffer.length > 0) {
      const samplesToProcess = Math.min(channel.length, this.buffer.length);
      
      for (let i = 0; i < samplesToProcess; i++) {
        channel[i] = this.buffer.shift();
      }
      
      // Fill remaining samples with silence if buffer is depleted
      if (samplesToProcess < channel.length) {
        for (let i = samplesToProcess; i < channel.length; i++) {
          channel[i] = 0;
        }
      }
    } else {
      // Output silence when not playing
      for (let i = 0; i < channel.length; i++) {
        channel[i] = 0;
      }
    }
    
    return true;
  }
}

registerProcessor("audio-player-processor", AudioPlayerProcessor);
`;

export default class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private recorderNode: ScriptProcessorNode | null = null;
  private onAudioPlayedListeners: ((samples: Float32Array) => void)[] = [];
  private initialized: boolean = false;

  constructor() {
    this.onAudioPlayedListeners = [];
    this.initialized = false;
  }

  addEventListener(event: string, callback: (samples: Float32Array) => void): void {
    switch (event) {
      case "onAudioPlayed":
        this.onAudioPlayedListeners.push(callback);
        break;
      default:
        console.error(`Listener registered for event type: ${event} which is not supported`);
    }
  }

  async start(): Promise<void> {
    this.audioContext = new AudioContext({ sampleRate: 24000 });
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 512;

    // Create a Blob URL for the worklet code
    const blob = new Blob([audioPlayerProcessorCode], { type: 'application/javascript' });
    const workletUrl = URL.createObjectURL(blob);

    try {
      // Register the audio worklet
      await this.audioContext.audioWorklet.addModule(workletUrl);
      
      // Create and connect nodes
      this.workletNode = new AudioWorkletNode(this.audioContext, "audio-player-processor");
      this.workletNode.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      
      // Create recorder node for monitoring audio output
      this.recorderNode = this.audioContext.createScriptProcessor(512, 1, 1);
      this.recorderNode.onaudioprocess = (event) => {
        // Pass the input along as-is
        const inputData = event.inputBuffer.getChannelData(0);
        const outputData = event.outputBuffer.getChannelData(0);
        outputData.set(inputData);
        
        // Notify listeners that the audio was played
        const samples = new Float32Array(outputData.length);
        samples.set(outputData);
        this.onAudioPlayedListeners.forEach(listener => listener(samples));
      };
      
      this.maybeOverrideInitialBufferLength();
      this.initialized = true;
    } finally {
      // Clean up the Blob URL
      URL.revokeObjectURL(workletUrl);
    }
  }

  bargeIn(): void {
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: "barge-in",
      });
    }
  }

  stop(): void {
    if (ObjectExt.exists(this.audioContext)) {
      this.audioContext?.close();
    }

    if (ObjectExt.exists(this.analyser)) {
      this.analyser?.disconnect();
    }

    if (ObjectExt.exists(this.workletNode)) {
      this.workletNode?.disconnect();
    }

    if (ObjectExt.exists(this.recorderNode)) {
      this.recorderNode?.disconnect();
    }

    this.initialized = false;
    this.audioContext = null;
    this.analyser = null;
    this.workletNode = null;
    this.recorderNode = null;
  }

  private maybeOverrideInitialBufferLength(): void {
    // Read a user-specified initial buffer length from the URL parameters to help with tinkering
    const params = new URLSearchParams(window.location.search);
    const value = params.get("audioPlayerInitialBufferLength");
    if (value === null) {
      return; // No override specified
    }
    
    const bufferLength = parseInt(value);
    if (isNaN(bufferLength)) {
      console.error("Invalid audioPlayerInitialBufferLength value:", value);
      return;
    }
    
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: "initial-buffer-length",
        bufferLength: bufferLength,
      });
    }
  }

  playAudio(samples: Float32Array): void {
    if (!this.initialized) {
      console.error("The audio player is not initialized. Call start() before attempting to play audio.");
      return;
    }
    
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: "audio",
        audioData: samples,
      });
    }
  }

  getSamples(): number[] | null {
    if (!this.initialized || !this.analyser) {
      return null;
    }
    
    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    this.analyser.getByteTimeDomainData(dataArray);
    return Array.from(dataArray).map(e => e / 128 - 1);
  }

  getVolume(): number {
    if (!this.initialized || !this.analyser) {
      return 0;
    }
    
    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    this.analyser.getByteTimeDomainData(dataArray);
    const normSamples = Array.from(dataArray).map(e => e / 128 - 1);
    
    let sum = 0;
    for (let i = 0; i < normSamples.length; i++) {
      sum += normSamples[i] * normSamples[i];
    }
    
    return Math.sqrt(sum / normSamples.length);
  }
}