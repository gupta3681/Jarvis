import { useEffect, useRef, useState, useCallback } from 'react';

export interface Message {
  type: 'user' | 'assistant' | 'system' | 'node' | 'error';
  content: string;
  timestamp?: number;
}

interface UseWebSocketReturn {
  messages: Message[];
  sendMessage: (content: string) => void;
  isConnected: boolean;
  clearMessages: () => void;
  disconnect: () => void;
  connect: () => void;
}

export function useWebSocket(url: string, sessionId: string, autoConnect: boolean = false): UseWebSocketReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const shouldAutoReconnect = useRef(autoConnect);

  const connect = useCallback(() => {
    const wsUrl = `${url}/${sessionId}`;
    console.log('[WS] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WS] Received:', data);

        // Filter out "Processing:" messages and node messages (internal processing)
        if (data.type === 'user' && data.content?.startsWith('Processing:')) {
          return; // Skip processing acknowledgment messages
        }

        // Add message to state
        setMessages((prev) => [
          ...prev,
          {
            type: data.type,
            content: data.content,
            timestamp: Date.now(),
          },
        ]);
      } catch (error) {
        console.error('[WS] Parse error:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      setIsConnected(false);

      // Auto-reconnect only if enabled
      if (shouldAutoReconnect.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WS] Attempting to reconnect...');
          connect();
        }, 3000);
      }
    };
  }, [url, sessionId]);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect, autoConnect]);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Add user message to UI immediately
      setMessages((prev) => [
        ...prev,
        {
          type: 'user',
          content,
          timestamp: Date.now(),
        },
      ]);

      // Send to backend
      wsRef.current.send(JSON.stringify({ message: content }));
    } else {
      console.error('[WS] Not connected');
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const disconnect = useCallback(() => {
    shouldAutoReconnect.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const manualConnect = useCallback(() => {
    shouldAutoReconnect.current = true;
    connect();
  }, [connect]);

  return {
    messages,
    sendMessage,
    isConnected,
    clearMessages,
    disconnect,
    connect: manualConnect,
  };
}
