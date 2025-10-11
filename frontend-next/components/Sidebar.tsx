import { Trash2, Circle, Sparkles, Power, Wifi } from 'lucide-react';

interface SidebarProps {
  isConnected: boolean;
  onClearChat: () => void;
  onDisconnect: () => void;
  onConnect: () => void;
}

export function Sidebar({ isConnected, onClearChat, onDisconnect, onConnect }: SidebarProps) {
  return (
    <div className="w-72 bg-white/10 backdrop-blur-md border-r border-white/20 flex flex-col">
      {/* Header */}
      <div className="p-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Jarvis</h1>
            <p className="text-xs text-white/70">AI Assistant</p>
          </div>
        </div>
      </div>

      {/* Connection Status */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-2 px-3 py-2 bg-white/10 rounded-lg backdrop-blur-sm">
          <Circle
            className={`w-2 h-2 ${
              isConnected ? 'fill-green-400 text-green-400' : 'fill-gray-400 text-gray-400'
            }`}
          />
          <span className={`text-sm ${isConnected ? 'text-green-300' : 'text-gray-400'}`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 space-y-2">
        {!isConnected ? (
          <button
            onClick={onConnect}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-white/90 hover:bg-green-500/20 rounded-xl transition-all duration-200 hover:scale-105"
          >
            <Wifi className="w-4 h-4" />
            Connect
          </button>
        ) : (
          <button
            onClick={onDisconnect}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-white/90 hover:bg-red-500/20 rounded-xl transition-all duration-200 hover:scale-105"
          >
            <Power className="w-4 h-4" />
            Disconnect
          </button>
        )}
        
        <button
          onClick={onClearChat}
          className="w-full flex items-center gap-3 px-4 py-3 text-sm text-white/90 hover:bg-white/10 rounded-xl transition-all duration-200 hover:scale-105"
        >
          <Trash2 className="w-4 h-4" />
          Clear Chat
        </button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="p-6 border-t border-white/10">
        <p className="text-xs text-white/50 text-center">
          Powered by LangGraph & Mem0
        </p>
      </div>
    </div>
  );
}
