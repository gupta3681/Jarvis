import { useState, KeyboardEvent, useEffect, useRef, useCallback } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [autoSendEnabled, setAutoSendEnabled] = useState(true);
  const previousTranscriptRef = useRef('');
  
  const { 
    transcript, 
    isListening, 
    startListening, 
    stopListening, 
    resetTranscript,
    browserSupportsSpeechRecognition 
  } = useSpeechRecognition();

  // Update input with transcript
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  const handleSend = useCallback(() => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      resetTranscript();
      previousTranscriptRef.current = '';
      if (isListening) {
        stopListening();
      }
    }
  }, [input, disabled, onSend, resetTranscript, isListening, stopListening]);

  // Auto-send when listening stops and we have a transcript
  useEffect(() => {
    // When listening stops and we have a new transcript
    if (!isListening && transcript && transcript.trim() && autoSendEnabled) {
      // Check if this is a new transcript (not the same as before)
      if (transcript !== previousTranscriptRef.current) {
        console.log('[Auto-send] Triggered with transcript:', transcript);
        previousTranscriptRef.current = transcript;
        
        // Small delay to ensure transcript is complete
        const timer = setTimeout(() => {
          if (transcript.trim()) {
            handleSend();
          }
        }, 500);
        
        return () => clearTimeout(timer);
      }
    }
  }, [isListening, transcript, autoSendEnabled, handleSend]);

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening(true); // Enable auto-stop on silence
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-white/10 bg-white/5 backdrop-blur-md p-6">
      <div className="max-w-4xl mx-auto flex gap-3">
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isListening ? "Listening..." : "Message Jarvis..."}
            disabled={disabled}
            rows={1}
            className="w-full resize-none rounded-2xl bg-white/95 backdrop-blur-sm border border-white/60 px-5 py-4 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed shadow-lg text-gray-800 placeholder-gray-400"
          />
        </div>
        
        {/* Microphone Button */}
        {browserSupportsSpeechRecognition && (
          <button
            onClick={toggleListening}
            disabled={disabled}
            className={`px-4 py-4 rounded-2xl transition-all duration-200 flex items-center gap-2 shadow-lg ${
              isListening
                ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                : 'bg-white/20 hover:bg-white/30 backdrop-blur-sm border border-white/40'
            } text-white disabled:opacity-50 disabled:cursor-not-allowed`}
            title={isListening ? 'Stop listening' : 'Start voice input'}
          >
            {isListening ? (
              <MicOff className="w-5 h-5" />
            ) : (
              <Mic className="w-5 h-5" />
            )}
          </button>
        )}
        
        {/* Send Button */}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="px-6 py-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-2xl hover:from-purple-600 hover:to-pink-600 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 shadow-lg hover:shadow-xl hover:scale-105"
        >
          <Send className="w-5 h-5" />
          <span className="hidden sm:inline font-medium">Send</span>
        </button>
      </div>
    </div>
  );
}
