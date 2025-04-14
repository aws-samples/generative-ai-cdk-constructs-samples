import { useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { askQuestion } from "@/lib/api";

interface QATabProps {
  jobId: string;
}

const models = [
  {
    id: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    name: "Claude 3 Sonnet (Oct 2024) - On Demand"
  },
  {
    id: "amazon.nova-pro-v1:0",
    name: "Amazon Nova Pro - On Demand"
  },
  {
    id: "anthropic.claude-3-7-sonnet-20250219-v1:0",
    name: "Claude 3.7 Sonnet (Feb 2025) - On Demand"
  },
  {
    id: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    name: "Claude 3 Sonnet (Oct 2024) - CRIS US"
  },
  {
    id: "us.amazon.nova-pro-v1:0",
    name: "Amazon Nova Pro - CRIS US"
  },
  {
    id: "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    name: "Claude 3.7 Sonnet (Feb 2025) - CRIS US"
  }
];

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function QATab({ jobId }: QATabProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState(models[0].id);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: inputMessage
    };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setStreamingMessage('');

    try {
      const response = await askQuestion({
        jobId,
        model: selectedModel,
        question: inputMessage
      });

      const responseData = await response.json();
      const answer = responseData.answer;

      // Add the assistant message
      const assistantMessage: Message = {
        role: 'assistant',
        content: answer
      };
      setMessages(prev => [...prev, assistantMessage]);
      setStreamingMessage('');

    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your question.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-4">
      <div className="mb-4">
        <Label htmlFor="model-select">Select Model</Label>
        <Select value={selectedModel} onValueChange={setSelectedModel}>
          <SelectTrigger id="model-select" className="w-full">
            <SelectValue placeholder="Select a model" />
          </SelectTrigger>
          <SelectContent>
            {models.map(model => (
              <SelectItem key={model.id} value={model.id}>
                {model.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex-1 overflow-y-auto mb-4 space-y-4 border rounded-lg p-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <pre className="whitespace-pre-wrap font-sans">
                {message.content}
              </pre>
            </div>
          </div>
        ))}
        {streamingMessage && (
          <div className="flex justify-start">
            <div className="max-w-[80%] p-3 rounded-lg bg-gray-100 text-gray-900">
              <pre className="whitespace-pre-wrap font-sans">
                {streamingMessage}
              </pre>
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Input
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Ask a question about the document..."
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          disabled={isLoading}
        />
        <Button 
          onClick={handleSendMessage}
          disabled={isLoading || !inputMessage.trim()}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </Button>
      </div>
    </div>
  );
}
