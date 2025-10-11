import { Message } from '@/hooks/useWebSocket';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

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
            : 'bg-white/20 backdrop-blur-md border border-white/30 text-white shadow-lg'
        } rounded-2xl px-5 py-4`}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center ${
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
          <span className={`text-sm font-semibold ${isUser ? 'text-white/95' : 'text-white'}`}>
            {isUser ? 'You' : 'Jarvis'}
          </span>
          {message.timestamp && (
            <span className={`text-xs ${isUser ? 'text-white/60' : 'text-white/60'}`}>
              {new Date(message.timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}
        </div>

        {/* Content */}
        {isUser ? (
          <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>
        ) : (
          <div className="prose prose-sm max-w-none prose-headings:text-white prose-p:text-white/90 prose-p:leading-relaxed prose-strong:text-white prose-code:text-purple-300 prose-code:bg-purple-900/30 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-black/20 prose-pre:text-white/90 prose-pre:border prose-pre:border-white/20 prose-a:text-blue-300 prose-a:no-underline hover:prose-a:underline prose-ul:text-white/90 prose-ol:text-white/90 prose-li:text-white/90">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
