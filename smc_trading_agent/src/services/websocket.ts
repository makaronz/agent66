import { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';

interface AgentStatusUpdate {
  agentId: string;
  status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping';
  metrics?: {
    cpu: number;
    memory: number;
    network: number;
    latency: string;
  };
  performance?: {
    pnl: number;
    trades: number;
    winRate: number;
  };
  lastUpdate: string;
}

interface MarketDataUpdate {
  symbol: string;
  price: number;
  change: number;
  volume: string;
  timestamp: string;
}

interface LogEntry {
  id: string;
  agentId: string;
  agentName: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug' | 'trade';
  message: string;
  details?: Record<string, any>;
  category: 'system' | 'trading' | 'performance' | 'risk' | 'network';
}

interface TradeAlert {
  id: string;
  agentId: string;
  agentName: string;
  type: 'entry' | 'exit' | 'stop_loss' | 'take_profit';
  symbol: string;
  side: 'buy' | 'sell';
  price: number;
  size: number;
  pnl?: number;
  timestamp: string;
}

export class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnected = false;

  constructor(private serverUrl: string = 'http://localhost:3002') {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = io(this.serverUrl, {
          transports: ['websocket', 'polling'],
          timeout: 10000,
          forceNew: true
        });

        this.socket.on('connect', () => {
          console.log('WebSocket connected to', this.serverUrl);
          this.isConnected = true;
          this.reconnectAttempts = 0;
          resolve();
        });

        this.socket.on('disconnect', (reason) => {
          console.log('WebSocket disconnected:', reason);
          this.isConnected = false;
          this.handleReconnect();
        });

        this.socket.on('connect_error', (error) => {
          console.error('WebSocket connection error:', error);
          this.isConnected = false;
          reject(error);
        });

        this.socket.on('error', (error) => {
          console.error('WebSocket error:', error);
        });

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);

      setTimeout(() => {
        this.connect().catch(error => {
          console.error('Reconnection failed:', error);
        });
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
    }
  }

  // Agent status subscriptions
  subscribeToAgentUpdates(callback: (update: AgentStatusUpdate) => void): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.on('agent:update', callback);

    return () => {
      this.socket?.off('agent:update', callback);
    };
  }

  subscribeToAllAgents(callback: (updates: AgentStatusUpdate[]) => void): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.on('agents:bulk-update', callback);

    return () => {
      this.socket?.off('agents:bulk-update', callback);
    };
  }

  // Market data subscriptions
  subscribeToMarketData(callback: (data: MarketDataUpdate) => void): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.on('market:update', callback);

    return () => {
      this.socket?.off('market:update', callback);
    };
  }

  subscribeToSymbol(symbol: string, callback: (data: MarketDataUpdate) => void): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.emit('symbol:subscribe', symbol);
    this.socket.on(`market:${symbol}`, callback);

    return () => {
      this.socket?.off(`market:${symbol}`, callback);
      this.socket?.emit('symbol:unsubscribe', symbol);
    };
  }

  // Log subscriptions
  subscribeToAgentLogs(
    agentId: string,
    callback: (log: LogEntry) => void
  ): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.emit('logs:subscribe', agentId);
    this.socket.on(`logs:${agentId}`, callback);

    return () => {
      this.socket?.off(`logs:${agentId}`, callback);
      this.socket?.emit('logs:unsubscribe', agentId);
    };
  }

  subscribeToAllLogs(callback: (log: LogEntry) => void): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.emit('logs:subscribe:all');
    this.socket.on('logs:all', callback);

    return () => {
      this.socket?.off('logs:all', callback);
      this.socket?.emit('logs:unsubscribe:all');
    };
  }

  // Trade alerts
  subscribeToTradeAlerts(callback: (alert: TradeAlert) => void): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.on('trade:alert', callback);

    return () => {
      this.socket?.off('trade:alert', callback);
    };
  }

  subscribeToAgentTrades(
    agentId: string,
    callback: (alert: TradeAlert) => void
  ): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.emit('trades:subscribe', agentId);
    this.socket.on(`trades:${agentId}`, callback);

    return () => {
      this.socket?.off(`trades:${agentId}`, callback);
      this.socket?.emit('trades:unsubscribe', agentId);
    };
  }

  // System events
  subscribeToSystemEvents(callback: (event: any) => void): () => void {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return () => {};
    }

    this.socket.on('system:event', callback);

    return () => {
      this.socket?.off('system:event', callback);
    };
  }

  // Send events to server
  sendAgentCommand(agentId: string, command: string, params?: any) {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return;
    }

    this.socket.emit('agent:command', {
      agentId,
      command,
      params,
      timestamp: new Date().toISOString()
    });
  }

  sendHeartbeat() {
    if (this.socket && this.isConnected) {
      this.socket.emit('heartbeat', {
        timestamp: new Date().toISOString()
      });
    }
  }

  // Utility methods
  getConnectionStatus(): {
    connected: boolean;
    reconnectAttempts: number;
    serverUrl: string;
  } {
    return {
      connected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      serverUrl: this.serverUrl
    };
  }

  // Simulated data methods for development/testing
  startSimulation() {
    if (!this.socket) return;

    // Simulate market data updates
    const marketSymbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'];
    marketSymbols.forEach((symbol, index) => {
      setInterval(() => {
        if (!this.isConnected) return;

        const basePrice = symbol === 'BTCUSDT' ? 43000 : symbol === 'ETHUSDT' ? 2650 : 0.48;
        const change = (Math.random() - 0.5) * 2; // -1% to +1%
        const price = basePrice * (1 + change / 100);

        this.socket?.emit('market:simulate', {
          symbol,
          price,
          change,
          volume: `${Math.floor(Math.random() * 1000000)}M`,
          timestamp: new Date().toISOString()
        });
      }, 2000 + index * 1000); // Stagger updates
    });

    // Simulate agent status updates
    setInterval(() => {
      if (!this.isConnected) return;

      const agentIds = ['agent_1', 'agent_2'];
      agentIds.forEach(agentId => {
        const statusOptions = ['running', 'warning', 'error'];
        const status = statusOptions[Math.floor(Math.random() * statusOptions.length)] as any;

        this.socket?.emit('agent:simulate', {
          agentId,
          status: status === 'warning' ? 'running' : status,
          metrics: {
            cpu: Math.random() * 100,
            memory: Math.random() * 100,
            network: Math.random() * 100,
            latency: `${Math.floor(Math.random() * 50)}ms`
          },
          performance: {
            pnl: (Math.random() - 0.5) * 1000,
            trades: Math.floor(Math.random() * 100),
            winRate: Math.random() * 100
          },
          lastUpdate: new Date().toISOString()
        });
      });
    }, 5000);
  }
}

// Singleton instance
export const websocketService = new WebSocketService();

// Hook for React components
export function useWebSocket(service: WebSocketService = websocketService) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({
    connected: false,
    reconnectAttempts: 0,
    serverUrl: ''
  });

  useEffect(() => {
    const updateStatus = () => {
      const status = service.getConnectionStatus();
      setConnectionStatus(status);
      setIsConnected(status.connected);
    };

    const interval = setInterval(updateStatus, 1000);
    updateStatus();

    return () => clearInterval(interval);
  }, [service]);

  return {
    isConnected,
    connectionStatus,
    service
  };
}