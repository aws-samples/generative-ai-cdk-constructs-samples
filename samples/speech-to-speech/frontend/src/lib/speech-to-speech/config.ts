/**
 * Configuration file for the Speech-to-Speech UI
 */

// Get the environment variables from the window object or the import.meta.env object
// Window object is set by the custom resource in the backend stack
// If the window object is not set, use the import.meta.env object (local development)
const env = window.APP_CONFIG || import.meta.env;

// Default configuration for local development
const config = {
  // WebSocket backend URL - will be replaced during deployment
  websocketUrl: env.VITE_DEPLOYMENT_TYPE === 'remote' 
    ? `wss://${env.VITE_LOAD_BALANCER_DNS}` 
    : 'ws://localhost:8081', // Local development - match container port
  
  // Connection settings
  reconnectInterval: 2000, // Reconnect interval in milliseconds
  maxReconnectAttempts: 5,
  
  // Audio settings
  audioSampleRate: 16000,
  audioChannels: 1,
  
  // UI settings
  enableDebugLogs: false,
  maxChatHistoryItems: 50,
};

export default config;
