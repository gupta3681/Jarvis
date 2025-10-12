'use client';

import { useEffect, useRef, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSpeechSynthesis } from '@/hooks/useSpeechSynthesis';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { Sidebar } from '@/components/Sidebar';
import { ProcessingStatus } from '@/components/ProcessingStatus';
import { Sparkles } from 'lucide-react';

export default function Home() {
  const [sessionId] = useState(() => `nextjs-${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastMessageCountRef = useRef(0);

  const { messages, sendMessage, isConnected, clearMessages, disconnect, connect } = useWebSocket(
    'ws://localhost:8000/ws',
    sessionId,
    false // Don't auto-connect
  );

  const { speak, enabled: ttsEnabled, setEnabled: setTtsEnabled } = useSpeechSynthesis();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-read new assistant messages
  useEffect(() => {
    const chatMessages = messages.filter((msg) => msg.type === 'user' || msg.type === 'assistant');
    
    // Check if there's a new assistant message
    if (chatMessages.length > lastMessageCountRef.current) {
      const lastMessage = chatMessages[chatMessages.length - 1];
      
      if (lastMessage.type === 'assistant' && ttsEnabled) {
        speak(lastMessage.content);
      }
      
      lastMessageCountRef.current = chatMessages.length;
    }
  }, [messages, speak, ttsEnabled]);

  const handleClearChat = () => {
    if (confirm('Are you sure you want to clear the chat history?')) {
      clearMessages();
      // Reload page to get new session ID
      window.location.reload();
    }
  };

  const handleDisconnect = () => {
    if (confirm('Are you sure you want to disconnect?')) {
      disconnect();
    }
  };

  // Only show user and assistant messages (hide all processing/node messages)
  const chatMessages = messages.filter((msg) => msg.type === 'user' || msg.type === 'assistant');

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <Sidebar 
        isConnected={isConnected} 
        onClearChat={handleClearChat} 
        onDisconnect={handleDisconnect}
        onConnect={connect}
        ttsEnabled={ttsEnabled}
        onToggleTts={() => setTtsEnabled(!ttsEnabled)}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {chatMessages.length === 0 ? (
              <div className="text-center py-20">
                <div className="w-20 h-20 mx-auto mb-6 rounded-3xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-2xl">
                  <Sparkles className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-3xl font-bold text-white mb-3">
                  Welcome to Jarvis
                </h2>
                <p className="text-white/70 text-lg">
                  Your personal AI assistant with memory. Ask me anything!
                </p>
              </div>
            ) : (
              chatMessages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={!isConnected} />
      </div>
    </div>
  );
}
