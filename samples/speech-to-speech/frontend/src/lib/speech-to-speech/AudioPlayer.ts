/**
 * Audio player for speech-to-speech functionality
 */

import ObjectExt from "./ObjectsExt";


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


    const workletUrl = new URL('./AudioPlayerProcessor.worklet.js', import.meta.url);
    // Register the audio worklet
    await this.audioContext.audioWorklet.addModule(workletUrl);
    
    // Create and connect nodes
    this.workletNode = new AudioWorkletNode(this.audioContext, "audio-player-processor");
    // Create recorder node for monitoring audio output
    this.recorderNode = this.audioContext.createScriptProcessor(512, 1, 1);

    this.workletNode.connect(this.analyser);
    this.analyser.connect(this.recorderNode);
    this.recorderNode.connect(this.audioContext.destination);

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
