/**
 * WebSocket event manager for speech-to-speech functionality
 */

import AudioPlayer from "./AudioPlayer";
import config from "./config";

const audioPlayer = new AudioPlayer();

interface AudioConfig {
  mediaType: string;
  sampleRateHertz: number;
  sampleSizeBits: number;
  channelCount: number;
  voiceId: string;
  encoding: string;
  audioType: string;
}

interface CompletionStartEvent {
  promptName: string;
  sessionId: string;
}

interface ContentStartEvent {
  type: string;
  role: string;
  contentId: string;
  promptName: string;
  sessionId: string;
  contentName?: string;
  audioOutputConfiguration?: AudioConfig;
  textOutputConfiguration?: { mediaType: string };
  additionalModelFields?: string;
}

interface TextOutputEvent {
  role: string;
  content: string;
  contentId: string;
  promptName: string;
  sessionId: string;
  completionId: string;
}

interface AudioOutputEvent {
  content: string;
  contentId: string;
  promptName: string;
  sessionId: string;
}

interface ContentEndEvent {
  type: string;
  stopReason: string;
  contentId: string;
  promptName: string;
  sessionId: string;
  completionId: string;
}

interface CompletionEndEvent {
  completionId: string;
  promptName: string;
  sessionId: string;
}

interface WebSocketEventData {
  completionStart?: CompletionStartEvent;
  contentStart?: ContentStartEvent;
  textOutput?: TextOutputEvent;
  audioOutput?: AudioOutputEvent;
  contentEnd?: ContentEndEvent;
  completionEnd?: CompletionEndEvent;
  usageEvent?: unknown; // Nova 2 Sonic usage tracking event (can be ignored)
}

interface OutgoingEventData {
  sessionStart?: {
    inferenceConfiguration: {
      maxTokens: number;
      topP: number;
      temperature: number;
    };
  };
  promptStart?: {
    promptName: string;
    textOutputConfiguration: { mediaType: string };
    audioOutputConfiguration: AudioConfig;
    toolUseOutputConfiguration: { mediaType: string };
    toolConfiguration: unknown;
  };
  contentStart?: {
    promptName: string;
    contentName: string;
    type: string;
    role: string;
    interactive: boolean;
    textInputConfiguration?: { mediaType: string };
    audioInputConfiguration?: {
      mediaType: string;
      sampleRateHertz: number;
      sampleSizeBits: number;
      channelCount: number;
      audioType: string;
      encoding: string;
    };
  };
  textInput?: {
    promptName: string;
    contentName: string;
    content: string;
  };
  audioInput?: {
    promptName: string;
    contentName: string;
    content: string;
  };
  contentEnd?: {
    promptName: string;
    contentName: string;
  };
  promptEnd?: {
    promptName: string;
  };
  sessionEnd?: Record<string, never>;
}

interface OutgoingEvent {
  event: OutgoingEventData;
}

interface WebSocketEvent {
  event?: WebSocketEventData;
}

export class WebSocketEventManager {
  private wsUrl: string;
  public socket: WebSocket | null = null;
  private promptName: string | null = null;
  private audioContentName: string | null = null;
  private currentAudioConfig: AudioConfig | null = null;
  public role: string | null = null;
  private isInitialized: boolean = false;
  private onDisconnectCallback: (() => void) | null = null;
  private onConnectCallback: (() => void) | null = null;
  private systemPrompt: string;
  private audioCleanup: (() => void) | null = null;
  private isProcessingAudio: boolean = false;
  private isPlayingAudio: boolean = false;
  private userIsSpeaking: boolean = false;
  private silenceTimer: NodeJS.Timeout | null = null;
  private speechSampleCount: number = 0;
  private readonly SILENCE_THRESHOLD = 0.005; // Threshold for UI feedback (silence detection)
  private readonly SPEECH_THRESHOLD = 0.01; // Threshold for UI feedback (speech detection)
  private readonly SILENCE_DURATION = 1000;
  private readonly MIN_SPEECH_SAMPLES = 3; // Samples needed for UI feedback
  private audioProcessor: ScriptProcessorNode | null = null;
  private audioContext: AudioContext | null = null;
  private audioStream: MediaStream | null = null;
  private voiceId: string = "tiffany"; // Default voice (polyglot voice for Nova 2 Sonic)

  constructor(wsUrl: string, onDisconnect?: () => void, onConnect?: () => void, systemPrompt?: string) {
    this.wsUrl = wsUrl;
    this.onDisconnectCallback = onDisconnect || null;
    this.onConnectCallback = onConnect || null;
    this.systemPrompt = systemPrompt || "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.";
    console.log("WebSocket URL:", this.wsUrl);
    this.connect();
  }

  connect(): void {
    if (this.socket) {
      console.log("[WebSocketEventManager] Closing existing WebSocket before creating a new one.");
      this.socket.close(1000, "Re-initializing WebSocket connection");
    }

    console.log("[WebSocketEventManager] Attempting to retrieve Cognito token...");
    
    // Get Cognito token from local storage
    let token = null;
    const storageKeys = Object.keys(localStorage);
    
    // Look for Cognito access tokens
    const accessTokenKey = storageKeys.find(key => 
      key.includes('CognitoIdentityServiceProvider') && 
      key.endsWith('.accessToken')
    );

    if (accessTokenKey) {
      token = localStorage.getItem(accessTokenKey);
      console.log("[WebSocketEventManager] Found Cognito token with key:", accessTokenKey);
    }
    
    // Log token status (presence/absence only, not the actual token)
    console.log("[WebSocketEventManager] Token status:", {
      isTokenPresent: !!token,
      accessTokenKey: accessTokenKey || 'not found',
      storageKeys: storageKeys,
      timestamp: new Date().toISOString()
    });

    if (!token) {
      console.error("[WebSocketEventManager] No valid Cognito token found. User must be authenticated.");
      console.log("[WebSocketEventManager] Available localStorage keys:", storageKeys);
      this.updateStatus("Authentication required", "error");
      return;
    }

    console.log("[WebSocketEventManager] Token found, creating WebSocket connection...");
    
    // Create WebSocket with authorization header
    const socket = new WebSocket(this.wsUrl);
    socket.addEventListener('open', () => {
      console.log("[WebSocketEventManager] WebSocket connection opened, sending authorization...");
      // Send authorization header after connection
      const authMsg = {
        type: 'authorization',
        token: `Bearer ${token}`
      };
      socket.send(JSON.stringify(authMsg));
      console.log("[WebSocketEventManager] Authorization message sent");
    });

    this.socket = socket;
    this.setupSocketListeners();
    this.isInitialized = false;
  }

  setupSocketListeners(): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      console.log("WebSocket Connected");
      this.updateStatus("Connected", "connected");
      if (this.onConnectCallback) this.onConnectCallback();
      this.startSession();
      audioPlayer.start();
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketEvent;
        // Handle the message internally
        this.handleMessage(data);
        // Also emit a custom event so SpeechToSpeech component can listen
        // This ensures both handlers can process the event
        if (data.event) {
          window.dispatchEvent(new CustomEvent('nova-sonic-event', { detail: data }));
        }
      } catch (e) {
        console.error("Error parsing message:", e, "Raw data:", JSON.stringify(event.data));
      }
    };

    this.socket.onerror = (error) => {
      console.error("WebSocket Error:", error);
      this.updateStatus("Connection error", "error");
      this.isInitialized = false;
    };

    this.socket.onclose = (event) => {
      console.log("WebSocket Disconnected", JSON.stringify(event));
      this.updateStatus("Disconnected", "disconnected");
      audioPlayer.stop();
      this.isInitialized = false;
      this.promptName = null;
      this.audioContentName = null;
      if (this.onDisconnectCallback) this.onDisconnectCallback();
    };
  }

  async sendEvent(event: OutgoingEvent): Promise<void> {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.error("[WebSocketEventManager] Cannot send event - socket not open:", {
        readyState: this.socket?.readyState,
        timestamp: new Date().toISOString()
      });
      return;
    }

    const eventType = Object.keys(event.event)[0] as keyof OutgoingEventData;
    const eventData = event.event[eventType];
    
    if (!eventData) {
      console.error("[WebSocketEventManager] Invalid event data:", event);
      return;
    }

    console.log("[WebSocketEventManager] Sending event:", {
      direction: "OUTGOING",
      type: eventType,
      details: {
        ...eventData,
        ...(('content' in eventData && typeof eventData.content === 'string') 
          ? { contentLength: eventData.content.length } 
          : {})
      },
      timestamp: new Date().toISOString()
    });

    try {
      this.socket.send(JSON.stringify(event));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("[WebSocketEventManager] Error sending event:", {
        type: eventType,
        error: errorMessage,
        timestamp: new Date().toISOString()
      });
      this.updateStatus("Error sending message", "error");
    }
  }

  handleMessage(data: WebSocketEvent): void {
    if (!data.event) {
      console.error("[WebSocketEventManager] Received message without event:", {
        data: JSON.stringify(data),
        timestamp: new Date().toISOString()
      });
      return;
    }

    const event = data.event;
    const eventType = Object.keys(event)[0] as keyof WebSocketEventData;
    const eventData = event[eventType];
    
    if (!eventData) {
      console.error("[WebSocketEventManager] Invalid event data:", event);
      return;
    }

    const hasContent = eventData && typeof eventData === 'object' && 'content' in eventData && typeof (eventData as any).content === 'string';
    const contentDetails = hasContent ? {
      contentLength: (eventData as any).content.length,
      contentPreview: (eventData as any).content.substring(0, 100) + ((eventData as any).content.length > 100 ? '...' : '')
    } : {};

    // Enhanced logging for all incoming events
    const eventDataObj = eventData as Record<string, any>;
    console.log("[WebSocketEventManager] Received event:", {
      direction: "INCOMING",
      type: eventType,
      details: {
        ...eventDataObj,
        ...contentDetails,
        sessionId: eventDataObj?.sessionId,
        completionId: eventDataObj?.completionId,
        contentId: eventDataObj?.contentId
      },
      timestamp: new Date().toISOString()
    });

    try {
      // Handle completionStart
      if (event.completionStart) {
        console.log("[WebSocketEventManager] Completion start:", {
          event: "completionStart",
          promptName: event.completionStart.promptName,
          sessionId: event.completionStart.sessionId,
          timestamp: new Date().toISOString()
        });
        this.promptName = event.completionStart.promptName;
        this.isInitialized = true;
        // Stop audio processing when a new completion starts
        this.pauseAudioProcessing();
      }
      // Handle contentStart
      else if (event.contentStart) {
        console.log("[WebSocketEventManager] Content start:", {
          event: "contentStart",
          type: event.contentStart.type,
          role: event.contentStart.role,
          contentId: event.contentStart.contentId,
          sessionId: event.contentStart.sessionId,
          config: event.contentStart.type === "AUDIO" ? event.contentStart.audioOutputConfiguration : event.contentStart.textOutputConfiguration,
          additionalFields: event.contentStart.additionalModelFields,
          timestamp: new Date().toISOString()
        });
        this.role = event.contentStart.role;
        if (event.contentStart.type === "AUDIO") {
          if (event.contentStart.role === "USER") {
            // For user audio, set or preserve audioContentName
            if (!this.audioContentName) {
              this.audioContentName = event.contentStart.contentName || null;
            }
          } else {
            // For assistant audio, just update config without changing audioContentName
            this.currentAudioConfig = event.contentStart.audioOutputConfiguration || null;
            this.isInitialized = true;
            if (this.isProcessingAudio) {
              this.pauseAudioProcessing();
            }
          }
        }
        if (event.contentStart.type === "TEXT") {
          try {
            if (event.contentStart.additionalModelFields) {
              console.log("Additional model fields:", event.contentStart.additionalModelFields);
              const additionalFields = JSON.parse(event.contentStart.additionalModelFields);
              if (additionalFields.generationStage === "SPECULATIVE") {
                console.log("Received speculative content");
              }
            }
          } catch (e) {
            console.error("Error parsing additionalModelFields:", e);
          }
        }
      }
      // Handle textOutput
      else if (event.textOutput) {
        console.log("[WebSocketEventManager] Text output:", {
          event: "textOutput",
          role: event.textOutput.role,
          contentId: event.textOutput.contentId,
          sessionId: event.textOutput.sessionId,
          completionId: event.textOutput.completionId,
          content: event.textOutput.content,
          timestamp: new Date().toISOString()
        });
      }
      // Handle audioOutput
      else if (event.audioOutput) {
        const currentState = {
          isProcessingAudio: this.isProcessingAudio,
          isPlayingAudio: this.isPlayingAudio,
          audioContentName: this.audioContentName,
          role: this.role
        };
        
        console.log("[WebSocketEventManager] Audio output:", {
          event: "audioOutput",
          config: this.currentAudioConfig,
          contentId: event.audioOutput.contentId,
          sessionId: event.audioOutput.sessionId,
          contentLength: event.audioOutput.content.length,
          state: currentState,
          timestamp: new Date().toISOString()
        });

        if (this.currentAudioConfig) {
          // Preserve audioContentName during playback
          const savedAudioContentName = this.audioContentName;
          
          // Only pause on first audio chunk if not already playing
          if (!this.isPlayingAudio) {
            this.isPlayingAudio = true;
            if (this.isProcessingAudio) {
              this.pauseAudioProcessing();
            }
          }
          
          // Restore audioContentName after state changes
          this.audioContentName = savedAudioContentName;
          
          audioPlayer.playAudio(this.base64ToFloat32Array(event.audioOutput.content));
        }
      }
      // Handle contentEnd
      else if (event.contentEnd) {
        console.log("[WebSocketEventManager] Content end:", {
          event: "contentEnd",
          type: event.contentEnd.type,
          stopReason: event.contentEnd.stopReason,
          contentId: event.contentEnd.contentId,
          sessionId: event.contentEnd.sessionId,
          completionId: event.contentEnd.completionId,
          timestamp: new Date().toISOString()
        });

        // Handle text content end
        if (event.contentEnd.type === "TEXT") {
          if (event.contentEnd.stopReason.toUpperCase() === "INTERRUPTED") {
            audioPlayer.bargeIn();
          }
          // Resume audio processing after text content ends
          this.resumeAudioProcessing();
        }
        // Handle audio content end
        else if (event.contentEnd.type === "AUDIO") {
          // Save current state
          const savedState = {
            audioContentName: this.audioContentName,
            role: this.role
          };
          
          console.log("[WebSocketEventManager] Audio content end state:", savedState);
          
          // Only reset audio playback state if it's assistant audio
          if (this.role === "ASSISTANT") {
            this.isPlayingAudio = false;
          }
          
          // Resume audio processing after a delay
          setTimeout(() => {
            // Restore saved state
            this.audioContentName = savedState.audioContentName;
            this.role = savedState.role;
            
            console.log("[WebSocketEventManager] Resuming with state:", {
              audioContentName: this.audioContentName,
              role: this.role
            });
            
            this.resumeAudioProcessing();
          }, 100);
        }

        // Don't automatically start new audio content on END_TURN
        // Let the server manage the conversation flow
      }
      // Handle completionEnd
      else if (event.completionEnd) {
        console.log("[WebSocketEventManager] Completion end:", {
          event: "completionEnd",
          data: event.completionEnd,
          timestamp: new Date().toISOString()
        });
        // Only resume audio processing, don't start new prompt
        this.resumeAudioProcessing();
      }
      // Handle usageEvent (Nova 2 Sonic feature - usage tracking, can be ignored)
      else if (event.usageEvent) {
        console.log("[WebSocketEventManager] Usage event received (ignored):", event.usageEvent);
        // Usage events are informational and don't need processing
      }
      else {
        console.warn("Unknown event type received:", JSON.stringify(Object.keys(event)[0]));
      }
    } catch (error) {
      console.error("Error processing message:", error);
      console.error("Event data:", JSON.stringify(event));
    }
  }

  base64ToFloat32Array(base64String: string): Float32Array {
    const binaryString = window.atob(base64String);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    return float32Array;
  }

  updateStatus(message: string, className: string): void {
    const statusDiv = document.getElementById('status');
    if (statusDiv) {
      statusDiv.textContent = message;
      statusDiv.className = `status ${className}`;
    }
  }

  private endpointingSensitivity: "HIGH" | "MEDIUM" | "LOW" = "MEDIUM";

  setEndpointingSensitivity(sensitivity: "HIGH" | "MEDIUM" | "LOW"): void {
    this.endpointingSensitivity = sensitivity;
  }

  startSession(): void {
    console.log("Starting session...");
    const sessionStartData: any = {
      inferenceConfiguration: {
        maxTokens: 1024,
        topP: 0.9,
        temperature: 0.7
      },
      // Nova 2 Sonic uses turnDetectionConfiguration with endpointingSensitivity
      turnDetectionConfiguration: {
        endpointingSensitivity: this.endpointingSensitivity
      }
    };
    
    const sessionStartEvent = {
      event: {
        sessionStart: sessionStartData
      }
    };
    console.log("Sending session start:", JSON.stringify(sessionStartEvent, null, 2));
    this.sendEvent(sessionStartEvent);
    this.startPrompt();
  }

  setVoiceId(voiceId: string): void {
    this.voiceId = voiceId;
  }

  startPrompt(): void {
    const promptName = crypto.randomUUID();
    this.promptName = promptName;

    const getDefaultToolSchema = JSON.stringify({
      "type": "object",
      "properties": {},
      "required": []
    });

    const getWeatherToolSchema = JSON.stringify({
      "type": "object",
      "properties": {
        "latitude": {
          "type": "string",
          "description": "Geographical WGS84 latitude of the location."
        },
        "longitude": {
          "type": "string",
          "description": "Geographical WGS84 longitude of the location."
        }
      },
      "required": ["latitude", "longitude"]
    });

    const promptStartEvent = {
      event: {
        promptStart: {
          promptName,
          textOutputConfiguration: {
            mediaType: "text/plain"
          },
          audioOutputConfiguration: {
            mediaType: "audio/lpcm",
            sampleRateHertz: 24000,
            sampleSizeBits: 16,
            channelCount: 1,
            voiceId: this.voiceId, // Use configurable voice ID (supports polyglot voices)
            encoding: "base64",
            audioType: "SPEECH"
          },
          toolUseOutputConfiguration: {
            mediaType: "application/json"
          },
          toolConfiguration: {
            tools: [{
              toolSpec: {
                name: "getDateAndTimeTool",
                description: "get information about the current date and current time",
                inputSchema: {
                  json: getDefaultToolSchema
                }
              }
            },
            {
              toolSpec: {
                name: "getWeatherTool",
                description: "Get the current weather for a given location, based on its WGS84 coordinates.",
                inputSchema: {
                  json: getWeatherToolSchema
                }
              }
            }]
          }
        }
      }
    };
    this.sendEvent(promptStartEvent);
    this.sendSystemPrompt();
  }

  sendSystemPrompt(): void {
    if (!this.promptName) return;

    const systemContentName = crypto.randomUUID();
    const contentStartEvent = {
      event: {
        contentStart: {
          promptName: this.promptName,
          contentName: systemContentName,
          type: "TEXT",
          role: "SYSTEM",
          interactive: true,
          textInputConfiguration: {
            mediaType: "text/plain"
          }
        }
      }
    };
    this.sendEvent(contentStartEvent);

    const textInputEvent = {
      event: {
        textInput: {
          promptName: this.promptName,
          contentName: systemContentName,
          content: this.systemPrompt
        }
      }
    };
    this.sendEvent(textInputEvent);

    const contentEndEvent = {
      event: {
        contentEnd: {
          promptName: this.promptName,
          contentName: systemContentName
        }
      }
    };
    this.sendEvent(contentEndEvent);
    this.startAudioContent();
  }

  private pauseAudioProcessing(): void {
    if (!this.isProcessingAudio) {
      console.log("[WebSocketEventManager] Audio processing already paused");
      return;
    }
    console.log("[WebSocketEventManager] Pausing audio processing");
    this.isProcessingAudio = false;
    if (this.audioProcessor) {
      this.audioProcessor.disconnect();
    }
  }

  private resumeAudioProcessing(): void {
    console.log("[WebSocketEventManager] Resuming audio processing");
    // Don't resume if we're in cleanup
    if (!this.promptName) {
      console.log("[WebSocketEventManager] Cannot resume - no prompt active");
      return;
    }
    
    // Ensure we're initialized before resuming
    if (!this.isInitialized) {
      console.log("[WebSocketEventManager] Cannot resume - not initialized");
      return;
    }

    // Don't resume if already processing
    if (this.isProcessingAudio) {
      console.log("[WebSocketEventManager] Already processing audio");
      return;
    }

    this.isProcessingAudio = true;
    
    // Reconnect audio processor if it exists
    if (this.audioProcessor && this.audioContext) {
      this.audioProcessor.connect(this.audioContext.destination);
      console.log("[WebSocketEventManager] Reconnected audio processor");
    }
    
    // Start new audio content if needed
    if (!this.audioContentName) {
      console.log("[WebSocketEventManager] Starting new audio content");
      this.startAudioContent();
    } else {
      console.log("[WebSocketEventManager] Resumed with existing audio content:", this.audioContentName);
    }
  }

  async startAudioContent(): Promise<void> {
    if (!this.promptName || this.isProcessingAudio) {
      console.log("[WebSocketEventManager] Cannot start audio content:", {
        hasPrompt: !!this.promptName,
        isProcessing: this.isProcessingAudio
      });
      return;
    }

    try {
      // Clean up any existing audio resources
      if (this.audioCleanup) {
        this.audioCleanup();
        this.audioCleanup = null;
      }

      // Set up audio processing
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: config.audioChannels,
          sampleRate: config.audioSampleRate,
          sampleSize: 16,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      this.audioContext = new AudioContext({
        sampleRate: config.audioSampleRate,
        latencyHint: 'interactive'
      });

      // Ensure audio context is resumed (required by browsers after user interaction)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
        console.log("[WebSocketEventManager] Audio context resumed");
      }

      const source = this.audioContext.createMediaStreamSource(this.audioStream);
      // Use smaller buffer size (256 samples) for lower latency
      // Smaller buffer = more frequent processing = lower latency
      this.audioProcessor = this.audioContext.createScriptProcessor(256, 1, 1);

      source.connect(this.audioProcessor);
      this.audioProcessor.connect(this.audioContext.destination);

      // Now that audio processing is ready, send the contentStart event
      const audioContentName = crypto.randomUUID();
      this.audioContentName = audioContentName;

      const contentStartEvent = {
        event: {
          contentStart: {
            promptName: this.promptName,
            contentName: audioContentName,
            type: "AUDIO",
            interactive: true,
            role: "USER",
            audioInputConfiguration: {
              mediaType: "audio/lpcm",
              sampleRateHertz: config.audioSampleRate,
              sampleSizeBits: 16,
              channelCount: config.audioChannels,
              audioType: "SPEECH",
              encoding: "base64"
            }
          }
        }
      };
      this.sendEvent(contentStartEvent);

      // Set up audio processing handler
      // According to Nova 2 Sonic documentation, audio should be streamed continuously
      // as it's captured, maintaining the natural microphone sampling cadence.
      // The server-side turn detection will handle speech detection and filtering.
      this.audioProcessor.onaudioprocess = (e) => {
        if (!this.isProcessingAudio) return;

        const inputData = e.inputBuffer.getChannelData(0);
        
        // Calculate audio level for UI feedback only (not for filtering)
        const audioLevel = Math.max(...Array.from(inputData).map(Math.abs));

        // Convert audio to PCM format
        const buffer = new ArrayBuffer(inputData.length * 2);
        const pcmData = new DataView(buffer);
        
        for (let i = 0; i < inputData.length; i++) {
          const int16 = Math.max(-32768, Math.min(32767, Math.round(inputData[i] * 32767)));
          pcmData.setInt16(i * 2, int16, true);
        }

        let data = "";
        for (let i = 0; i < pcmData.byteLength; i++) {
          data += String.fromCharCode(pcmData.getUint8(i));
        }

        // Send ALL audio chunks immediately - Nova 2 Sonic handles speech detection server-side
        // This is critical for low latency. The documentation states audio should be
        // "immediately sent as audioInput events" maintaining "natural microphone sampling cadence"
        this.sendAudioChunk(btoa(data));

        // Use audio level only for UI feedback (showing "USER Listening" indicator)
        // Don't filter audio based on this - send everything
        if (audioLevel > this.SPEECH_THRESHOLD) {
          this.speechSampleCount++;
          if (this.speechSampleCount >= this.MIN_SPEECH_SAMPLES && !this.userIsSpeaking) {
            this.userIsSpeaking = true;
            console.log("[WebSocketEventManager] Speech detected (UI feedback only)");
          }
          // Reset silence timer if active
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
          }
        } else if (audioLevel < this.SILENCE_THRESHOLD && this.userIsSpeaking) {
          // Potential silence detected - only for UI feedback
          this.speechSampleCount = 0;
          if (!this.silenceTimer) {
            this.silenceTimer = setTimeout(() => {
              this.userIsSpeaking = false;
              console.log("[WebSocketEventManager] Silence detected (UI feedback only)");
              this.silenceTimer = null;
            }, this.SILENCE_DURATION);
          }
        } else {
          this.speechSampleCount = 0;
        }
      };

      // Store cleanup functions
      this.audioCleanup = () => {
        if (this.audioProcessor) {
          this.audioProcessor.disconnect();
          this.audioProcessor = null;
        }
        if (this.audioStream) {
          this.audioStream.getTracks().forEach(track => track.stop());
          this.audioStream = null;
        }
        if (this.audioContext) {
          this.audioContext.close();
          this.audioContext = null;
        }
      };

      this.isInitialized = true;
      this.isProcessingAudio = true;
    } catch (error) {
      console.error("Error setting up audio:", error);
      this.cleanup();
    }
  }

  // Crossmodal support: Send text input during an active session (Nova 2 Sonic feature)
  sendTextInput(text: string): void {
    if (!this.isInitialized || !this.promptName) {
      console.warn("Cannot send text input - session not initialized");
      return;
    }

    const textContentName = crypto.randomUUID();
    
    // Start text content with USER role for crossmodal input
    const contentStartEvent = {
      event: {
        contentStart: {
          promptName: this.promptName,
          contentName: textContentName,
          type: "TEXT",
          role: "USER",
          interactive: true,
          textInputConfiguration: {
            mediaType: "text/plain"
          }
        }
      }
    };
    this.sendEvent(contentStartEvent);

    // Send the text input
    const textInputEvent = {
      event: {
        textInput: {
          promptName: this.promptName,
          contentName: textContentName,
          content: text
        }
      }
    };
    this.sendEvent(textInputEvent);

    // End the text content
    const contentEndEvent = {
      event: {
        contentEnd: {
          promptName: this.promptName,
          contentName: textContentName
        }
      }
    };
    this.sendEvent(contentEndEvent);
  }

  sendAudioChunk(base64AudioData: string): void {
    if (!this.isInitialized || !this.promptName || !this.audioContentName) {
      console.warn("WebSocket initialization state:", {
        isInitialized: this.isInitialized,
        promptName: this.promptName,
        audioContentName: this.audioContentName
      });
      
      if (this.socket?.readyState === WebSocket.OPEN) {
        console.log("Attempting to reinitialize audio content...");
        this.startPrompt();
        return;
      }
      
      console.error("Cannot send audio chunk - WebSocket not fully initialized");
      return;
    }

    // Send audio chunk immediately without JSON.stringify overhead for better performance
    // This reduces latency by avoiding the async sendEvent wrapper
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }

    const audioInputEvent = {
      event: {
        audioInput: {
          promptName: this.promptName,
          contentName: this.audioContentName,
          content: base64AudioData
        }
      }
    };
    
    // Send directly for lower latency (audio chunks are sent frequently)
    try {
      this.socket.send(JSON.stringify(audioInputEvent));
    } catch (error) {
      console.error("[WebSocketEventManager] Error sending audio chunk:", error);
    }
  }

  endContent(): void {
    // Don't send contentEnd events - let the server manage content lifecycle
    return;
  }

  endPrompt(): void {
    if (!this.promptName) return;

    const promptEndEvent = {
      event: {
        promptEnd: {
          promptName: this.promptName
        }
      }
    };
    this.sendEvent(promptEndEvent);
  }

  endSession(): void {
    const sessionEndEvent = {
      event: {
        sessionEnd: {}
      }
    };
    this.sendEvent(sessionEndEvent);
    if (this.socket) {
      this.socket.close();
    }
  }

  cleanup(): void {
    try {
      // Clean up audio resources first
      if (this.audioCleanup) {
        this.audioCleanup();
        this.audioCleanup = null;
      }

      // Reset all audio-related state
      this.isProcessingAudio = false;
      this.isPlayingAudio = false;
      this.userIsSpeaking = false;
      if (this.silenceTimer) {
        clearTimeout(this.silenceTimer);
        this.silenceTimer = null;
      }
      this.speechSampleCount = 0;

      // Then handle WebSocket cleanup
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        console.log("[WebSocketEventManager] Cleanup: closing session");
        this.endSession();
        console.log("[WebSocketEventManager] Sent sessionEnd.");
      } else if (this.socket && this.socket.readyState !== WebSocket.CLOSED && this.socket.readyState !== WebSocket.CLOSING) {
        console.log("[WebSocketEventManager] Cleanup: socket not open, closing anyway.");
        this.socket.close(1000, "Cleanup called by frontend (not open)");
      }

      // Finally reset remaining state
      this.isInitialized = false;
      this.promptName = null;
      this.audioContentName = null;
    } catch (error) {
      console.error("[WebSocketEventManager] Error during cleanup:", error);
    }
  }
}
