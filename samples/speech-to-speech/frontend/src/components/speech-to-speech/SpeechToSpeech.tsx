/**
 * Speech-to-Speech component for the NovaSonicSolution frontend
 */

import { useEffect, useRef, useState } from "react";
import { WebSocketEventManager } from "../../lib/speech-to-speech/WebSocketEventManager";
import config from "../../lib/speech-to-speech/config";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import "../../styles/speech-to-speech.css";

interface WebSocketEvent {
  event: {
    contentStart?: {
      type: string;
      role: string;
      additionalModelFields?: string;
    };
    textOutput?: {
      role: string;
      content: string;
    };
    contentEnd?: {
      type: string;
      stopReason: string;
    };
  };
}

interface ChatMessage {
  role?: string;
  message?: string;
  endOfResponse?: boolean;
  endOfConversation?: boolean;
}

interface SpeechToSpeechProps {
  websocketUrl?: string;
}

export function SpeechToSpeech({ websocketUrl = config.websocketUrl }: SpeechToSpeechProps) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState("Click 'Start Streaming' to begin");
  const [statusClass, setStatusClass] = useState("disconnected");
  const [isInitializing, setIsInitializing] = useState(false);
  const [disconnected, setDisconnected] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState(
    "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios."
  );
  const [endpointingSensitivity, setEndpointingSensitivity] = useState<"HIGH" | "MEDIUM" | "LOW">("MEDIUM");
  const [voiceId, setVoiceId] = useState("tiffany");
  const [textInput, setTextInput] = useState("");
  interface MessageWithId extends ChatMessage {
    id: string;
  }
  const [messages, setMessages] = useState<MessageWithId[]>([]);
  const [isUserThinking, setIsUserThinking] = useState(false);
  const [isAssistantThinking, setIsAssistantThinking] = useState(false);
  const wsManagerRef = useRef<WebSocketEventManager | null>(null);
  const audioCleanupRef = useRef<(() => void) | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const inputTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Monitor connection status
  useEffect(() => {
    const statusDiv = document.getElementById('status');
    if (statusDiv) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
            const newClass = statusDiv.className.replace('status ', '');
            setStatusClass(newClass);
          }
          if (mutation.type === 'childList') {
            setStatus(statusDiv.textContent || "Unknown");
          }
        });
      });
      
      observer.observe(statusDiv, { 
        attributes: true, 
        childList: true 
      });
      
      return () => observer.disconnect();
    }
  }, []);

  // Handle WebSocket disconnect
  const handleDisconnect = () => {
    setIsStreaming(false);
    setIsInitializing(false);
    setDisconnected(true);
    setStatus("Connection lost. Please restart streaming.");
    setStatusClass("disconnected");
    if (audioCleanupRef.current) {
      audioCleanupRef.current();
      audioCleanupRef.current = null;
    }
  };

  // Handle WebSocket connect
  const handleConnect = () => {
    setDisconnected(false);
  };

  async function startStreaming() {
    setIsInitializing(true);
    setStatus("Initializing WebSocket connection...");
    setDisconnected(false);
    
    // Use the WebSocket URL from the config file
    const wsUrl = websocketUrl + '/interact-s2s';
    wsManagerRef.current = new WebSocketEventManager(wsUrl, handleDisconnect, handleConnect, systemPrompt);
    
    // Configure Nova 2 Sonic features BEFORE connection is established
    // These will be used when startSession() is called
    wsManagerRef.current.setEndpointingSensitivity(endpointingSensitivity);
    wsManagerRef.current.setVoiceId(voiceId);

    // Start inactivity timer
    if (inputTimeoutRef.current) clearTimeout(inputTimeoutRef.current);
    inputTimeoutRef.current = setTimeout(() => {
      setStatus('Session timed out waiting for input. Please try again.');
      handleStopClick();
    }, 20000); // 20 seconds

    // Wait for WebSocket to be ready
    try {
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error("WebSocket connection timeout"));
        }, 10000); // 10 second timeout

        const checkConnection = () => {
          if (wsManagerRef.current?.socket?.readyState === WebSocket.OPEN) {
            clearTimeout(timeout);
            resolve();
          } else if (wsManagerRef.current?.socket?.readyState === WebSocket.CLOSED) {
            clearTimeout(timeout);
            reject(new Error("WebSocket connection failed"));
          } else {
            setTimeout(checkConnection, 100);
          }
        };
        checkConnection();
      });

      setStatus("WebSocket connected. Waiting for session initialization...");

      // The WebSocketEventManager will handle audio setup via startAudioContent()
      // We just need to wait for it to be ready
      setIsStreaming(true);
      setIsInitializing(false);
      setStatus("Ready - Speak to begin conversation");

      // No cleanup needed here - WebSocketEventManager handles it
      return null;
    } catch (error) {
      setIsInitializing(false);
      setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`);
      console.error("Error in startStreaming:", error);
      return null;
    }
  }

  function stopStreaming(_audioCleanup: (() => void) | null) {
    // Cleanup is handled by WebSocketEventManager
    if (wsManagerRef.current) {
      console.log("[SpeechToSpeech] Calling wsManagerRef.current.cleanup() to close WebSocket.");
      wsManagerRef.current.cleanup();
      wsManagerRef.current = null;
    }

    setIsStreaming(false);
    setStatus("Click 'Start Streaming' to begin");
  }

  const handleStartClick = async () => {
    if (isInitializing || isStreaming) {
      console.log("[SpeechToSpeech] Start button clicked while already initializing or streaming. Ignoring.");
      return;
    }
    const audioCleanup = await startStreaming();
    audioCleanupRef.current = audioCleanup;
  };

  const handleStopClick = () => {
    if (inputTimeoutRef.current) {
      clearTimeout(inputTimeoutRef.current);
      inputTimeoutRef.current = null;
    }
    stopStreaming(audioCleanupRef.current);
    audioCleanupRef.current = null;
  };

  const handleClearChat = () => {
    setMessages([]);
    setIsUserThinking(false);
    setIsAssistantThinking(false);
  };

  const handleSendTextInput = () => {
    if (!textInput.trim() || !wsManagerRef.current) return;
    
    const textToSend = textInput.trim();
    
    // Display the text input in the chat immediately
    const messageId = `user-text-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setMessages(prev => [...prev, { id: messageId, role: 'USER', message: textToSend }]);
    setIsUserThinking(false);
    
    wsManagerRef.current.sendTextInput(textToSend);
    setTextInput("");
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSendTextInput();
    }
  };

  // Ensure audio context is resumed after user interaction
  useEffect(() => {
    const handleClick = () => {
      // Audio context is handled internally by WebSocketEventManager
      // No need to access it directly
    };

    document.addEventListener('click', handleClick, { once: true });
    
    return () => {
      document.removeEventListener('click', handleClick);
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioCleanupRef.current) {
        stopStreaming(audioCleanupRef.current);
      }
      
      if (wsManagerRef.current) {
        wsManagerRef.current.cleanup();
        wsManagerRef.current = null;
      }
    };
  }, []);

  // Handle WebSocket events
  useEffect(() => {
    if (!wsManagerRef.current) return;

    const handleWebSocketMessage = (data: WebSocketEvent) => {
      if (!data.event) return;

      const event = data.event;

      if (event.contentStart) {
        if (event.contentStart.type === 'TEXT') {
          if (event.contentStart.role === 'USER') {
            setIsUserThinking(false);
          } else if (event.contentStart.role === 'ASSISTANT') {
            setIsAssistantThinking(false);
          }
        } else if (event.contentStart.type === 'AUDIO') {
          // Only show "Listening" for USER audio input, not ASSISTANT audio output
          if (event.contentStart.role === 'USER' && isStreaming) {
            setIsUserThinking(true);
          } else if (event.contentStart.role === 'ASSISTANT') {
            setIsUserThinking(false);
          }
        }
      }

      if (event.textOutput) {
        const role = event.textOutput.role;
        const content = event.textOutput.content;
        
        // Create a unique ID for this message
        const messageId = `${role}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        if (role === 'USER') {
          setIsUserThinking(false);
          setIsAssistantThinking(true);
          setMessages(prev => {
            const isDuplicate = prev.some(msg => msg.role === role && msg.message === content);
            return isDuplicate ? prev : [...prev, { id: messageId, role, message: content }];
          });
        } else if (role === 'ASSISTANT') {
          setMessages(prev => {
            const isDuplicate = prev.some(msg => msg.role === role && msg.message === content);
            return isDuplicate ? prev : [...prev, { id: messageId, role, message: content }];
          });
        }
      }

      if (event.contentEnd) {
        if (event.contentEnd.type === 'TEXT') {
          const currentRole = wsManagerRef.current?.role;
          if (currentRole === 'USER') {
            setIsUserThinking(false);
            setIsAssistantThinking(true);
          } else if (currentRole === 'ASSISTANT') {
            setIsAssistantThinking(false);
          }

          if (event.contentEnd.stopReason === 'END_TURN') {
            setMessages(prev => prev.map(msg => ({ ...msg, endOfResponse: true })));
          }
        } else if (event.contentEnd.type === 'AUDIO') {
          // When audio content ends, clear the listening indicator
          if (wsManagerRef.current?.role === 'USER') {
            setIsUserThinking(false);
          }
        }
      }
    };

    // Set up WebSocket message listener - listen to both direct socket and custom events
    const socket = wsManagerRef.current.socket;
    if (socket) {
      const messageHandler = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };
      
      socket.addEventListener('message', messageHandler);
      
      // Also listen to custom events from WebSocketEventManager
      const customEventHandler = ((event: CustomEvent) => {
        handleWebSocketMessage(event.detail);
      }) as EventListener;
      
      window.addEventListener('nova-sonic-event', customEventHandler);
      
      return () => {
        socket.removeEventListener('message', messageHandler);
        window.removeEventListener('nova-sonic-event', customEventHandler);
      };
    }

    return () => {
      setIsUserThinking(false);
      setIsAssistantThinking(false);
    };
  }, [wsManagerRef.current, isStreaming]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'auto',
      });
    }
  }, [messages, isUserThinking, isAssistantThinking]);

  // Function to render thinking indicators
  const renderThinkingIndicator = (role: string) => {
    return (
      <div className={`message ${role.toLowerCase()}`}>
        <div className="role-label">{role}</div>
        <div className="thinking-indicator">
          <span>{role === 'USER' ? 'Listening' : 'Thinking'}</span>
          <div className="thinking-dots">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        </div>
      </div>
    );
  };

  // Clear inactivity timer when audio is sent
  useEffect(() => {
    if (!isStreaming) return;
    // Patch: clear timer when a message is sent by the user
    if (messages.length > 0 && messages[messages.length - 1].role === 'USER') {
      if (inputTimeoutRef.current) {
        clearTimeout(inputTimeoutRef.current);
        inputTimeoutRef.current = null;
      }
    }
  }, [messages, isStreaming]);

  return (
    <div className="flex flex-col h-full">
      <Card className="p-4 mb-4">
        <div id="status" className={`status ${statusClass}`}>{status}</div>
        {disconnected && (
          <div className="text-red-600 font-semibold mt-2">Connection lost. Please click "Start Streaming" to reconnect.</div>
        )}
        <div className="mt-4 space-y-4">
          <div>
            <label htmlFor="system-prompt" className="block text-sm font-medium mb-1">System Prompt:</label>
            <textarea
              id="system-prompt"
              className="w-full border rounded p-2 text-sm"
              rows={3}
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              disabled={isStreaming || isInitializing}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="vad-sensitivity" className="block text-sm font-medium mb-1">
                Turn Detection Sensitivity (Nova 2 Sonic):
              </label>
              <select
                id="vad-sensitivity"
                className="w-full border rounded p-2 text-sm"
                value={endpointingSensitivity}
                onChange={e => setEndpointingSensitivity(e.target.value as "HIGH" | "MEDIUM" | "LOW")}
                disabled={isStreaming || isInitializing}
              >
                <option value="HIGH">High (Fast Response - 1.5s pause)</option>
                <option value="MEDIUM">Medium (Balanced - 1.75s pause)</option>
                <option value="LOW">Low (Patient - 2.0s pause)</option>
              </select>
            </div>
            <div>
              <label htmlFor="voice-id" className="block text-sm font-medium mb-1">
                Voice (Nova 2 Sonic):
              </label>
              <select
                id="voice-id"
                className="w-full border rounded p-2 text-sm"
                value={voiceId}
                onChange={e => setVoiceId(e.target.value)}
                disabled={isStreaming || isInitializing}
              >
                <option value="matthew">Matthew (en-US, Masculine)</option>
                <option value="tiffany">Tiffany (Polyglot - All languages)</option>
                <option value="amy">Amy (en-GB, Feminine)</option>
                <option value="olivia">Olivia (en-AU, Feminine)</option>
                <option value="lupe">Lupe (es-US, Feminine)</option>
              </select>
            </div>
          </div>
        </div>
      </Card>
      
      {/* Crossmodal Text Input (Nova 2 Sonic feature) */}
      {isStreaming && (
        <Card className="p-4 mb-4">
          <div className="flex gap-2">
            <input
              type="text"
              className="flex-1 border rounded p-2 text-sm"
              placeholder="Type a message (crossmodal support - Nova 2 Sonic)"
              value={textInput}
              onChange={e => setTextInput(e.target.value)}
              onKeyPress={handleKeyPress}
            />
            <Button
              onClick={handleSendTextInput}
              disabled={!textInput.trim()}
              variant="default"
              className="bg-blue-600 hover:bg-blue-700"
            >
              Send Text
            </Button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            You can send text messages during an active voice session (Nova 2 Sonic crossmodal feature)
          </p>
        </Card>
      )}
      
      <Card className="flex-1 overflow-y-auto mb-4 p-4" ref={chatContainerRef}>
        <div className="chat-container h-full">
          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.role?.toLowerCase()}`}>
              <div className="role-label">{msg.role}</div>
              <div>{msg.message}</div>
            </div>
          ))}
          {isUserThinking && renderThinkingIndicator('USER')}
          {isAssistantThinking && renderThinkingIndicator('ASSISTANT')}
        </div>
      </Card>
      
      <div id="controls" className="flex justify-center gap-4 p-4">
        <Button 
          id="start" 
          onClick={handleStartClick} 
          disabled={isStreaming || isInitializing}
          variant="default"
          className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400"
        >
          {isInitializing ? 'Initializing...' : 'Start Streaming'}
        </Button>
        <Button 
          id="stop" 
          onClick={handleStopClick} 
          disabled={!isStreaming}
          variant="default"
          className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400"
        >
          Stop Streaming
        </Button>
        <Button 
          id="clear" 
          onClick={handleClearChat}
          variant="default"
          className="bg-blue-600 hover:bg-blue-700"
        >
          Clear Chat
        </Button>
      </div>
    </div>
  );
}
