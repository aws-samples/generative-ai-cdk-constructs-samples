/**
 * Manages chat history for the speech-to-speech interface
 */

interface ChatMessage {
  role?: string;
  message?: string;
  endOfResponse?: boolean;
  endOfConversation?: boolean;
}

interface Chat {
  history: ChatMessage[];
}

type ChatRef = {
  current: Chat;
};

type SetChatFunction = (chat: Chat) => void;

class ChatHistoryManager {
  private static instance: ChatHistoryManager | null = null;
  private chatRef!: ChatRef;
  private setChat!: SetChatFunction;

  constructor(chatRef: ChatRef, setChat: SetChatFunction) {
    if (ChatHistoryManager.instance) {
      return ChatHistoryManager.instance;
    }

    this.chatRef = chatRef;
    this.setChat = setChat;
    ChatHistoryManager.instance = this;
  }

  static getInstance(chatRef?: ChatRef, setChat?: SetChatFunction): ChatHistoryManager {
    if (!ChatHistoryManager.instance) {
      if (!chatRef || !setChat) {
        throw new Error("ChatHistoryManager: chatRef and setChat must be provided when creating a new instance");
      }
      ChatHistoryManager.instance = new ChatHistoryManager(chatRef, setChat);
    } else if (chatRef && setChat) {
      // Update references if they're provided
      ChatHistoryManager.instance.chatRef = chatRef;
      ChatHistoryManager.instance.setChat = setChat;
    }
    return ChatHistoryManager.instance;
  }

  addTextMessage(content: ChatMessage): void {
    if (!this.chatRef || !this.setChat) {
      console.error("ChatHistoryManager: chatRef or setChat is not initialized");
      return;
    }

    const history = this.chatRef.current?.history || [];
    const updatedChatHistory = [...history];
    const lastTurn = updatedChatHistory[updatedChatHistory.length - 1];

    if (lastTurn !== undefined && lastTurn.role === content.role) {
      // Same role, append to the last turn
      updatedChatHistory[updatedChatHistory.length - 1] = {
        ...content,
        message: `${lastTurn.message} ${content.message}`
      };
    } else {
      // Different role, add a new turn
      updatedChatHistory.push({
        role: content.role,
        message: content.message
      });
    }

    this.setChat({
      history: updatedChatHistory
    });
  }

  endTurn(): void {
    if (!this.chatRef || !this.setChat) {
      console.error("ChatHistoryManager: chatRef or setChat is not initialized");
      return;
    }

    const history = this.chatRef.current?.history || [];
    const updatedChatHistory = history.map(item => ({
      ...item,
      endOfResponse: true
    }));

    this.setChat({
      history: updatedChatHistory
    });
  }

  endConversation(): void {
    if (!this.chatRef || !this.setChat) {
      console.error("ChatHistoryManager: chatRef or setChat is not initialized");
      return;
    }

    const history = this.chatRef.current?.history || [];
    const updatedChatHistory = history.map(item => ({
      ...item,
      endOfResponse: true
    }));

    updatedChatHistory.push({
      endOfConversation: true,
      endOfResponse: true
    });

    this.setChat({
      history: updatedChatHistory
    });
  }
}

export default ChatHistoryManager;
