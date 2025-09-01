import { useEffect, useRef, useState, useCallback } from 'react';

// Global WebSocket connection manager to prevent multiple connections
class WebSocketManager {
  private static instance: WebSocketManager;
  private ws: WebSocket | null = null;
  private clientId: string = `client_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 3;
  private isManuallyDisconnected: boolean = false;
  private subscribers: Set<(message: WebSocketMessage) => void> = new Set();
  private statusCallbacks: Set<(isConnected: boolean, error?: string) => void> = new Set();

  static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager();
    }
    return WebSocketManager.instance;
  }

  subscribe(onMessage: (message: WebSocketMessage) => void, onStatus?: (isConnected: boolean, error?: string) => void) {
    this.subscribers.add(onMessage);
    if (onStatus) {
      this.statusCallbacks.add(onStatus);
    }
  }

  unsubscribe(onMessage: (message: WebSocketMessage) => void, onStatus?: (isConnected: boolean, error?: string) => void) {
    this.subscribers.delete(onMessage);
    if (onStatus) {
      this.statusCallbacks.delete(onStatus);
    }
  }

  connect(url: string = 'ws://localhost:8000/ws') {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    if (this.isManuallyDisconnected) {
      return;
    }

    this.isManuallyDisconnected = false;

    try {
      const wsUrl = `${url}/${this.clientId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.statusCallbacks.forEach(callback => callback(true));
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.subscribers.forEach(callback => callback(message));
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        this.ws = null;
        this.statusCallbacks.forEach(callback => callback(false));

        if (!this.isManuallyDisconnected && 
            this.reconnectAttempts < this.maxReconnectAttempts &&
            event.code !== 1000) {
          
          const delay = Math.min(2000 * Math.pow(2, this.reconnectAttempts), 15000);
          this.reconnectAttempts++;
          
          console.log(`Attempting to reconnect... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          
          this.reconnectTimeout = setTimeout(() => {
            this.connect(url);
          }, delay);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.log('Max reconnection attempts reached. Giving up.');
          this.statusCallbacks.forEach(callback => callback(false, 'Connection failed after multiple attempts'));
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.statusCallbacks.forEach(callback => callback(false, 'Connection error'));
        
        if (this.ws) {
          this.ws.close();
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.statusCallbacks.forEach(callback => callback(false, 'Failed to connect'));
    }
  }

  disconnect() {
    this.isManuallyDisconnected = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.reconnectAttempts = 0;
    this.statusCallbacks.forEach(callback => callback(false));
  }

  sendMessage(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const messageToSend = typeof message === 'string' ? message : JSON.stringify(message);
      this.ws.send(messageToSend);
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN || false;
  }
}

interface WebSocketMessage {
  type: 'progress' | 'complete' | 'error' | 'ping' | 'typing';
  content?: any;
  progress?: number;
  stage?: string;
  metadata?: any;
  timestamp?: string;
}

interface UseWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: any) => void;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    url = `ws://localhost:8000/ws`,
    autoConnect = false, // Temporarily disable to stop connection spam
    onMessage,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const wsManager = useRef(WebSocketManager.getInstance());
  const onMessageRef = useRef(onMessage);
  const onStatusRef = useRef((isConnected: boolean, error?: string) => {
    setIsConnected(isConnected);
    setConnectionError(error || null);
    
    if (isConnected) {
      onConnect?.();
    } else {
      onDisconnect?.();
    }
    
    if (error) {
      onError?.(new Error(error));
    }
  });

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    setLastMessage(message);
    onMessageRef.current?.(message);
  }, []);

  const connect = useCallback(() => {
    wsManager.current.connect(url);
  }, [url]);

  const disconnect = useCallback(() => {
    wsManager.current.disconnect();
  }, []);

  const sendMessage = useCallback((message: any) => {
    wsManager.current.sendMessage(message);
  }, []);

  const sendChatMessage = useCallback((content: string, sessionId: string) => {
    const message = {
      type: 'chat',
      content,
      session_id: sessionId,
      timestamp: new Date().toISOString(),
    };
    sendMessage(message);
  }, [sendMessage]);

  // Subscribe to WebSocket manager
  useEffect(() => {
    wsManager.current.subscribe(handleMessage, onStatusRef.current);
    
    // Initialize connection state
    setIsConnected(wsManager.current.isConnected());

    return () => {
      wsManager.current.unsubscribe(handleMessage, onStatusRef.current);
    };
  }, [handleMessage]);

  // Auto-connect
  useEffect(() => {
    if (autoConnect) {
      wsManager.current.connect(url);
    }
  }, [autoConnect, url]);

  // Ping interval (only one instance needed since we have singleton)
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      if (wsManager.current.isConnected()) {
        sendMessage({ type: 'ping', timestamp: new Date().toISOString() });
      }
    }, 60000);

    return () => clearInterval(pingInterval);
  }, [isConnected, sendMessage]);

  return {
    isConnected,
    connectionError,
    lastMessage,
    connect,
    disconnect,
    sendMessage,
    sendChatMessage,
    clientId: wsManager.current.isConnected() ? 'shared_client' : 'disconnected',
  };
};