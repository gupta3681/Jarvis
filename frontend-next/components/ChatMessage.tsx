import { Message } from '@/hooks/useWebSocket';
import { User, Bot, Sparkles } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.type === 'user';

  return (
    <div className={`flex gap-3 message-enter ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] ${
          isUser
            ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white'
            : 'bg-white/95 backdrop-blur-sm text-gray-800 shadow-lg'
        } rounded-2xl px-5 py-3`}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <div
            className={`w-6 h-6 rounded-full flex items-center justify-center ${
              isUser
                ? 'bg-white/20'
                : 'bg-gradient-to-br from-purple-500 to-pink-500'
            }`}
          >
            {isUser ? (
              <User className="w-4 h-4" />
            ) : (
              <Bot className="w-4 h-4 text-white" />
            )}
          </div>
          <span className={`text-xs font-medium ${isUser ? 'text-white/90' : 'text-gray-600'}`}>
            {isUser ? 'You' : 'Jarvis'}
          </span>
          {message.timestamp && (
            <span className={`text-xs ${isUser ? 'text-white/70' : 'text-gray-400'}`}>
              {new Date(message.timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}
        </div>

        {/* Content */}
        <div className={`text-sm leading-relaxed whitespace-pre-wrap break-words`}>
          {message.content}
        </div>
      </div>
    </div>
  );
}
