/**
 * WebSocket Connection Manager for Real-Time Market Data
 * Handles multiple exchange connections with automatic reconnection and health monitoring
 */

import { CircuitBreaker, CircuitBreakerRegistry, DEFAULT_CIRCUIT_CONFIGS } from './circuitBreaker';
import { RateLimiterManager, RateLimitedRetryHandler } from './rateLimiter';

export interface WebSocketConfig {
  url: string;
  name: string;
  exchanges: string[];
  maxReconnectAttempts: number;
  reconnectDelay: number;
  heartbeatInterval: number;
  connectionTimeout: number;
}

export interface WebSocketMessage {
  type: string;
  symbol?: string;
  data: any;
  timestamp: number;
  source: string;
}

export interface WebSocketStatus {
  connected: boolean;
  lastMessage?: number;
  lastHeartbeat?: number;
  reconnectAttempts: number;
  messagesReceived: number;
  messagesPerSecond: number;
  latency: number;
  uptime: number;
}

export interface SubscriptionRequest {
  id: string;
  symbols: string[];
  channels: string[];
  callback: (data: WebSocketMessage) => void;
  timestamp: number;
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private subscriptions: Map<string, SubscriptionRequest> = new Map();
  private messageQueue: WebSocketMessage[] = [];
  private status: WebSocketStatus;
  private reconnectTimer?: NodeJS.Timeout;
  private heartbeatTimer?: NodeJS.Timeout;
  private messageBuffer: number[] = [];
  private startTime: number = Date.now();
  private circuitBreaker: CircuitBreaker;

  constructor(private config: WebSocketConfig) {
    this.status = {
      connected: false,
      reconnectAttempts: 0,
      messagesReceived: 0,
      messagesPerSecond: 0,
      latency: 0,
      uptime: 0
    };

    // Initialize circuit breaker for WebSocket connections
    const circuitBreakerRegistry = CircuitBreakerRegistry.getInstance();
    this.circuitBreaker = circuitBreakerRegistry.create(
      `websocket_${config.name}`,
      DEFAULT_CIRCUIT_CONFIGS.WEBSOCKET_CONNECTION
    );
  }

  // Connect to WebSocket with retry and circuit breaker protection
  async connect(): Promise<void> {
    try {
      // Try with rate limiting first
      return RateLimitedRetryHandler.executeWithRetryAndRateLimit(
        async () => {
          await this.circuitBreaker.execute(async () => {
            return this._connect();
          });
        },
        `${this.config.name.toUpperCase()}_WEBSOCKET`,
        'connection'
      );
    } catch (rateLimitError) {
      // If rate limiter is not configured, try without it
      if (rateLimitError.message.includes('Rate limiter not found')) {
        console.warn(`Rate limiter not found for ${this.config.name}, proceeding without rate limiting`);
        return this.circuitBreaker.execute(async () => {
          return this._connect();
        });
      } else {
        throw rateLimitError;
      }
    }
  }

  private async _connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        console.log(`Connecting to WebSocket: ${this.config.url}`);
        this.ws = new WebSocket(this.config.url);

        // Connection timeout
        const timeoutTimer = setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            reject(new Error('WebSocket connection timeout'));
          }
        }, this.config.connectionTimeout);

        this.ws.onopen = () => {
          clearTimeout(timeoutTimer);
          console.log(`WebSocket connected: ${this.config.name}`);
          this.status.connected = true;
          this.status.reconnectAttempts = 0;
          this.startTime = Date.now();

          // Start heartbeat
          this.startHeartbeat();

          // Resubscribe to previous subscriptions
          this.resubscribe();

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          clearTimeout(timeoutTimer);
          this.handleDisconnection(event.code, event.reason);
        };

        this.ws.onerror = (error) => {
          clearTimeout(timeoutTimer);
          console.error(`WebSocket error: ${this.config.name}`, error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  // Subscribe to market data channels
  subscribe(symbols: string[], channels: string[], callback: (data: WebSocketMessage) => void): string {
    const id = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const subscription: SubscriptionRequest = {
      id,
      symbols,
      channels,
      callback,
      timestamp: Date.now()
    };

    this.subscriptions.set(id, subscription);

    // Send subscription message if connected
    if (this.status.connected && this.ws) {
      this.sendSubscription(subscription);
    }

    return id;
  }

  // Unsubscribe from specific subscription
  unsubscribe(subscriptionId: string): boolean {
    const subscription = this.subscriptions.get(subscriptionId);
    if (!subscription) return false;

    this.subscriptions.delete(subscriptionId);

    // Send unsubscribe message if connected
    if (this.status.connected && this.ws) {
      this.sendUnsubscription(subscription);
    }

    return true;
  }

  // Send subscription message (to be overridden by exchange-specific implementations)
  protected sendSubscription(subscription: SubscriptionRequest): void {
    // Base implementation - to be overridden
    console.log(`Subscribing to ${subscription.channels.join(', ')} for ${subscription.symbols.join(', ')}`);
  }

  // Send unsubscribe message (to be overridden by exchange-specific implementations)
  protected sendUnsubscription(subscription: SubscriptionRequest): void {
    // Base implementation - to be overridden
    console.log(`Unsubscribing from subscription: ${subscription.id}`);
  }

  // Handle incoming WebSocket messages
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      const timestamp = Date.now();

      // Update status
      this.status.lastMessage = timestamp;
      this.status.messagesReceived++;

      // Calculate messages per second
      this.updateMessageRate();

      // Process message based on type
      const processedMessage = this.processMessage(data, timestamp);
      if (processedMessage) {
        this.messageQueue.push(processedMessage);

        // Notify relevant subscribers
        this.notifySubscribers(processedMessage);

        // Keep queue size manageable
        if (this.messageQueue.length > 1000) {
          this.messageQueue = this.messageQueue.slice(-500);
        }
      }

    } catch (error) {
      console.error(`Error processing WebSocket message:`, error);
    }
  }

  // Process raw WebSocket data (to be overridden by exchange-specific implementations)
  protected processMessage(data: any, timestamp: number): WebSocketMessage | null {
    return {
      type: data.type || 'unknown',
      symbol: data.symbol,
      data,
      timestamp,
      source: this.config.name
    };
  }

  // Notify subscribers of relevant messages
  private notifySubscribers(message: WebSocketMessage): void {
    for (const subscription of this.subscriptions.values()) {
      if (this.isMessageRelevant(message, subscription)) {
        try {
          subscription.callback(message);
        } catch (error) {
          console.error(`Error in subscription callback:`, error);
        }
      }
    }
  }

  // Check if message is relevant to subscription
  private isMessageRelevant(message: WebSocketMessage, subscription: SubscriptionRequest): boolean {
    // Check if message symbol matches subscription
    if (message.symbol && subscription.symbols.length > 0) {
      return subscription.symbols.includes(message.symbol);
    }

    // Check if message channel matches subscription
    if (subscription.channels.includes(message.type)) {
      return true;
    }

    return false;
  }

  // Update message rate calculation
  private updateMessageRate(): void {
    const now = Date.now();
    this.messageBuffer.push(now);

    // Keep only last second of messages
    const oneSecondAgo = now - 1000;
    this.messageBuffer = this.messageBuffer.filter(timestamp => timestamp > oneSecondAgo);

    this.status.messagesPerSecond = this.messageBuffer.length;
  }

  // Start heartbeat monitoring
  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    this.heartbeatTimer = setInterval(() => {
      this.performHeartbeat();
    }, this.config.heartbeatInterval);
  }

  // Perform heartbeat check
  private performHeartbeat(): void {
    const now = Date.now();
    this.status.lastHeartbeat = now;
    this.status.uptime = now - this.startTime;

    // Check if we're receiving messages
    if (this.status.lastMessage && (now - this.status.lastMessage) > this.config.heartbeatInterval * 2) {
      console.warn(`No messages received from ${this.config.name} for ${(now - this.status.lastMessage) / 1000}s`);
      this.triggerReconnection();
    }
  }

  // Handle WebSocket disconnection
  private handleDisconnection(code: number, reason: string): void {
    console.warn(`WebSocket disconnected: ${this.config.name} - ${code} ${reason}`);
    this.status.connected = false;

    // Clear heartbeat
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    // Trigger reconnection
    this.triggerReconnection();
  }

  // Trigger reconnection with exponential backoff
  private triggerReconnection(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    const delay = this.config.reconnectDelay * Math.pow(2, this.status.reconnectAttempts);

    if (this.status.reconnectAttempts < this.config.maxReconnectAttempts) {
      console.log(`Reconnecting to ${this.config.name} in ${delay}ms (attempt ${this.status.reconnectAttempts + 1})`);

      this.reconnectTimer = setTimeout(async () => {
        this.status.reconnectAttempts++;
        try {
          await this.connect();
        } catch (error) {
          console.error(`Reconnection failed:`, error);
          this.triggerReconnection();
        }
      }, delay);
    } else {
      console.error(`Max reconnection attempts reached for ${this.config.name}`);
    }
  }

  // Resubscribe to all active subscriptions
  private resubscribe(): void {
    for (const subscription of this.subscriptions.values()) {
      this.sendSubscription(subscription);
    }
  }

  // Get current WebSocket status
  getStatus(): WebSocketStatus {
    return { ...this.status };
  }

  // Get recent messages
  getRecentMessages(limit: number = 100): WebSocketMessage[] {
    return this.messageQueue.slice(-limit);
  }

  // Get active subscriptions
  getSubscriptions(): SubscriptionRequest[] {
    return Array.from(this.subscriptions.values());
  }

  // Disconnect WebSocket
  disconnect(): void {
    console.log(`Disconnecting WebSocket: ${this.config.name}`);

    // Clear timers
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    // Close WebSocket
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.status.connected = false;
    this.subscriptions.clear();
    this.messageQueue = [];
  }

  // Check health of WebSocket connection
  isHealthy(): boolean {
    return this.status.connected &&
           this.status.messagesPerSecond > 0 &&
           this.circuitBreaker.getState() === 'CLOSED';
  }
}

// WebSocket manager registry for multiple connections
export class WebSocketManagerRegistry {
  private static instance: WebSocketManagerRegistry;
  private managers: Map<string, WebSocketManager> = new Map();

  static getInstance(): WebSocketManagerRegistry {
    if (!WebSocketManagerRegistry.instance) {
      WebSocketManagerRegistry.instance = new WebSocketManagerRegistry();
    }
    return WebSocketManagerRegistry.instance;
  }

  register(name: string, manager: WebSocketManager): void {
    this.managers.set(name, manager);
  }

  get(name: string): WebSocketManager | undefined {
    return this.managers.get(name);
  }

  getAll(): Map<string, WebSocketManager> {
    return new Map(this.managers);
  }

  // Get health status of all connections
  getHealthStatus(): Record<string, { connected: boolean; healthy: boolean; messageRate: number }> {
    const status: Record<string, { connected: boolean; healthy: boolean; messageRate: number }> = {};

    for (const [name, manager] of this.managers) {
      const managerStatus = manager.getStatus();
      status[name] = {
        connected: managerStatus.connected,
        healthy: manager.isHealthy(),
        messageRate: managerStatus.messagesPerSecond
      };
    }

    return status;
  }

  // Disconnect all WebSockets
  disconnectAll(): void {
    for (const manager of this.managers.values()) {
      manager.disconnect();
    }
    this.managers.clear();
  }

  // Get aggregated statistics
  getAggregatedStats(): {
    totalConnections: number;
    activeConnections: number;
    totalMessagesPerSecond: number;
    averageLatency: number;
  } {
    let activeConnections = 0;
    let totalMessagesPerSecond = 0;
    let totalLatency = 0;
    let latencyCount = 0;

    for (const manager of this.managers.values()) {
      const status = manager.getStatus();
      if (status.connected) activeConnections++;
      totalMessagesPerSecond += status.messagesPerSecond;
      if (status.latency > 0) {
        totalLatency += status.latency;
        latencyCount++;
      }
    }

    return {
      totalConnections: this.managers.size,
      activeConnections,
      totalMessagesPerSecond,
      averageLatency: latencyCount > 0 ? totalLatency / latencyCount : 0
    };
  }
}