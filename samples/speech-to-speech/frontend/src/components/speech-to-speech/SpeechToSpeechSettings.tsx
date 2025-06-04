/**
 * Settings component for Speech-to-Speech functionality
 * Based on the reference implementation from amazon-nova-samples
 */

import { useState } from "react";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Checkbox } from "../ui/checkbox";
import { Settings } from "lucide-react";

export interface SpeechSettings {
  voiceId: string;
  systemPrompt: string;
  toolConfiguration: string;
  chatHistory: string;
  includeChatHistory: boolean;
}

interface SpeechToSpeechSettingsProps {
  settings: SpeechSettings;
  onSettingsChange: (settings: SpeechSettings) => void;
  disabled?: boolean;
}

const DEFAULT_SYSTEM_PROMPT = "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios. You may start each of your sentences with emotions in square brackets such as [amused], [neutral] or any other stage direction such as [joyful]. Only use a single pair of square brackets for indicating a stage command.";

const DEFAULT_TOOL_CONFIG = {
  tools: [
    {
      toolSpec: {
        name: "getDateAndTimeTool",
        description: "get information about the current date and current time",
        inputSchema: {
          json: JSON.stringify({
            "type": "object",
            "properties": {},
            "required": []
          })
        }
      }
    },
    {
      toolSpec: {
        name: "getWeatherTool",
        description: "Get the current weather for a given location, based on its WGS84 coordinates.",
        inputSchema: {
          json: JSON.stringify({
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
          })
        }
      }
    }
  ]
};

const DEFAULT_CHAT_HISTORY = [
  {
    "content": "hi there i would like to cancel my hotel reservation",
    "role": "USER"
  },
  {
    "content": "Hello! I'd be happy to assist you with cancelling your hotel reservation. To get started, could you please provide me with your full name and the check-in date for your reservation?",
    "role": "ASSISTANT"
  },
  {
    "content": "yeah so my name is don smith",
    "role": "USER"
  },
  {
    "content": "Thank you, Don. Now, could you please provide me with the check-in date for your reservation?",
    "role": "ASSISTANT"
  },
  {
    "content": "yes so um let me check just a second",
    "role": "USER"
  },
  {
    "content": "Take your time, Don. I'll be here when you're ready.",
    "role": "ASSISTANT"
  }
];

const VOICE_OPTIONS = [
  { label: "Matthew (en-US)", value: "matthew" },
  { label: "Tiffany (en-US)", value: "tiffany" },
  { label: "Amy (en-GB)", value: "amy" },
];

export function SpeechToSpeechSettings({ 
  settings, 
  onSettingsChange, 
  disabled = false 
}: SpeechToSpeechSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleSettingChange = (key: keyof SpeechSettings, value: string | boolean) => {
    onSettingsChange({
      ...settings,
      [key]: value
    });
  };

  const resetToDefaults = () => {
    onSettingsChange({
      voiceId: "matthew",
      systemPrompt: DEFAULT_SYSTEM_PROMPT,
      toolConfiguration: JSON.stringify(DEFAULT_TOOL_CONFIG, null, 2),
      chatHistory: JSON.stringify(DEFAULT_CHAT_HISTORY, null, 2),
      includeChatHistory: false
    });
  };

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        disabled={disabled}
        variant="outline"
        size="sm"
        className="flex items-center gap-2"
      >
        <Settings className="h-4 w-4" />
        Settings
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 m-4">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">Speech-to-Speech Settings</h2>
          <Button
            onClick={() => setIsOpen(false)}
            variant="outline"
            size="sm"
          >
            Close
          </Button>
        </div>

        <div className="space-y-6">
          {/* Voice ID Selection */}
          <div className="space-y-2">
            <Label htmlFor="voice-select">Voice ID</Label>
            <Select
              value={settings.voiceId}
              onValueChange={(value) => handleSettingChange('voiceId', value)}
            >
              <SelectTrigger id="voice-select">
                <SelectValue placeholder="Select a voice" />
              </SelectTrigger>
              <SelectContent>
                {VOICE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* System Prompt */}
          <div className="space-y-2">
            <Label htmlFor="system-prompt">System Prompt</Label>
            <p className="text-sm text-gray-600">For the speech model</p>
            <Textarea
              id="system-prompt"
              value={settings.systemPrompt}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleSettingChange('systemPrompt', e.target.value)}
              placeholder="Speech system prompt"
              rows={4}
              className="resize-vertical"
            />
          </div>

          {/* Tool Configuration */}
          <div className="space-y-2">
            <Label htmlFor="tool-config">Tool Use Configuration</Label>
            <p className="text-sm text-gray-600">For external integration such as RAG and Agents</p>
            <Textarea
              id="tool-config"
              value={settings.toolConfiguration}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleSettingChange('toolConfiguration', e.target.value)}
              placeholder="{}"
              rows={10}
              className="resize-vertical font-mono text-sm"
            />
          </div>

          {/* Chat History */}
          <div className="space-y-2">
            <Label htmlFor="chat-history">Chat History</Label>
            <p className="text-sm text-gray-600">Sample chat history to resume conversation</p>
            <div className="flex items-center space-x-2 mb-2">
              <Checkbox
                id="include-chat-history"
                checked={settings.includeChatHistory}
                onCheckedChange={(checked: boolean) => handleSettingChange('includeChatHistory', !!checked)}
              />
              <Label htmlFor="include-chat-history" className="text-sm">
                Include chat history
              </Label>
            </div>
            <Textarea
              id="chat-history"
              value={settings.chatHistory}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleSettingChange('chatHistory', e.target.value)}
              placeholder="{}"
              rows={15}
              className="resize-vertical font-mono text-sm"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex justify-between pt-4">
            <Button
              onClick={resetToDefaults}
              variant="outline"
            >
              Reset to Defaults
            </Button>
            <div className="flex gap-2">
              <Button
                onClick={() => setIsOpen(false)}
                variant="outline"
              >
                Cancel
              </Button>
              <Button
                onClick={() => setIsOpen(false)}
                variant="default"
              >
                Save Settings
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// Export default settings for initialization
export const getDefaultSettings = (): SpeechSettings => ({
  voiceId: "matthew",
  systemPrompt: DEFAULT_SYSTEM_PROMPT,
  toolConfiguration: JSON.stringify(DEFAULT_TOOL_CONFIG, null, 2),
  chatHistory: JSON.stringify(DEFAULT_CHAT_HISTORY, null, 2),
  includeChatHistory: false
});
