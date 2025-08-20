/**
 * Copyright 2025 Amazon.com, Inc. and its affiliates. All Rights Reserved.
 *
 * Licensed under the Amazon Software License (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *   http://aws.amazon.com/asl/
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */

// Audio sample buffer to minimize reallocations
class ExpandableBuffer {
  constructor() {
    // Start with one second's worth of buffered audio capacity before needing to expand
    this.buffer = new Float32Array(24000);
    this.readIndex = 0;
    this.writeIndex = 0;
    this.underflowedSamples = 0;
    this.isInitialBuffering = true;
    this.initialBufferLength = 24000; // One second
    this.lastWriteTime = 0;
  }

  logTimeElapsedSinceLastWrite() {
    const now = Date.now();
    if (this.lastWriteTime !== 0) {
      const elapsed = now - this.lastWriteTime;
      // console.log(`Elapsed time since last audio buffer write: ${elapsed} ms`);
    }
    this.lastWriteTime = now;
  }

  write(samples) {
    this.logTimeElapsedSinceLastWrite();
    if (this.writeIndex + samples.length <= this.buffer.length) {
      // Enough space to append the new samples
    } else {
      // Not enough space ...
      if (samples.length <= this.readIndex) {
        // ... but we can shift samples to the beginning of the buffer
        const subarray = this.buffer.subarray(this.readIndex, this.writeIndex);
        console.log(
          `Shifting the audio buffer of length ${subarray.length} by ${this.readIndex}`
        );
        this.buffer.set(subarray);
      } else {
        // ... and we need to grow the buffer capacity to make room for more audio
        const newLength =
          (samples.length + this.writeIndex - this.readIndex) * 2;
        const newBuffer = new Float32Array(newLength);
        console.log(
          `Expanding the audio buffer from ${this.buffer.length} to ${newLength}`
        );
        newBuffer.set(this.buffer.subarray(this.readIndex, this.writeIndex));
        this.buffer = newBuffer;
      }
      this.writeIndex -= this.readIndex;
      this.readIndex = 0;
    }
    this.buffer.set(samples, this.writeIndex);
    this.writeIndex += samples.length;
    if (this.writeIndex - this.readIndex >= this.initialBufferLength) {
      // Filled the initial buffer length, so we can start playback with some cushion
      this.isInitialBuffering = false;
      // console.log("Initial audio buffer filled");
    }
  }

  read(destination) {
    let copyLength = 0;
    if (!this.isInitialBuffering) {
      // Only start to play audio after we've built up some initial cushion
      copyLength = Math.min(
        destination.length,
        this.writeIndex - this.readIndex
      );
    }
    destination.set(
      this.buffer.subarray(this.readIndex, this.readIndex + copyLength)
    );
    this.readIndex += copyLength;
    if (copyLength > 0 && this.underflowedSamples > 0) {
      console.log(
        `Detected audio buffer underflow of ${this.underflowedSamples} samples`
      );
      this.underflowedSamples = 0;
    }
    if (copyLength < destination.length) {
      // Not enough samples (buffer underflow). Fill the rest with silence.
      destination.fill(0, copyLength);
      this.underflowedSamples += destination.length - copyLength;
    }
    if (copyLength === 0) {
      // Ran out of audio, so refill the buffer to the initial length before playing more
      this.isInitialBuffering = true;
    }
  }

  clearBuffer() {
    this.readIndex = 0;
    this.writeIndex = 0;
  }
}

class AudioPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.playbackBuffer = new ExpandableBuffer();
    this.port.onmessage = (event) => {
      if (event.data.type === "audio") {
        this.playbackBuffer.write(event.data.audioData);
      } else if (event.data.type === "initial-buffer-length") {
        // Override the current playback initial buffer length
        const newLength = event.data.bufferLength;
        this.playbackBuffer.initialBufferLength = newLength;
        // console.log(`Changed initial audio buffer length to: ${newLength}`);
      } else if (event.data.type === "barge-in") {
        this.playbackBuffer.clearBuffer();
      }
    };
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0][0]; // Assume one output with one channel
    this.playbackBuffer.read(output);
    return true; // True to continue processing
  }
}

registerProcessor("audio-player-processor", AudioPlayerProcessor);
