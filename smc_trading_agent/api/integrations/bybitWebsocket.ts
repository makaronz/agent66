/**
 * ByBit WebSocket Integration
 * Primary real-time market data source with optimized connection management
 */

import { WebSocketManager, WebSocketConfig, WebSocketMessage, SubscriptionRequest } from '../utils/websocketManager';
import { RateLimiterManager } from '../utils/rateLimiter';

export interface ByBitMarketData {
  symbol: string;
  price: number;
  priceChange24h: number;
  volume24h: string;
  high24h: number;
  low24h: number;
  open24h: number;
  timestamp: number;
}

export interface ByBitOrderBook {
  symbol: string;
  bids: [price: number, quantity: number][];
  asks: [price: number, quantity: number][];
  timestamp: number;
}

export interface ByBitTrade {
  symbol: string;
  price: number;
  size: number;
  side: 'Buy' | 'Sell';
  timestamp: number;
  tradeId: string;
}

export class ByBitWebSocket extends WebSocketManager {
  private static readonly BYBIT_WS_URL = 'wss://stream.bybit.com/v5/public/linear';
  private static readonly TESTNET_WS_URL = 'wss://stream-testnet.bybit.com/v5/public/linear';

  constructor(testnet: boolean = false) {
    const config: WebSocketConfig = {
      url: testnet ? ByBitWebSocket.TESTNET_WS_URL : ByBitWebSocket.BYBIT_WS_URL,
      name: 'ByBit',
      exchanges: ['bybit'],
      maxReconnectAttempts: 5,
      reconnectDelay: 2000,
      heartbeatInterval: 30000,
      connectionTimeout: 10000
    };

    super(config);
  }

  // Subscribe to ticker data for symbols
  subscribeToTickers(symbols: string[], callback: (data: ByBitMarketData) => void): string[] {
    const subscriptionIds: string[] = [];

    // ByBit supports batch ticker subscriptions
    const subscriptionId = this.subscribe(
      symbols,
      ['tickers'],
      (message: WebSocketMessage) => {
        const tickerData = this.parseTickerData(message);
        if (tickerData) {
          callback(tickerData);
        }
      }
    );

    subscriptionIds.push(subscriptionId);
    return subscriptionIds;
  }

  // Subscribe to order book data
  subscribeToOrderBook(symbols: string[], depth: number = 25, callback: (data: ByBitOrderBook) => void): string[] {
    const subscriptionIds: string[] = [];

    for (const symbol of symbols) {
      const subscriptionId = this.subscribe(
        [symbol],
        [`orderbook.${depth}`],
        (message: WebSocketMessage) => {
          const orderBookData = this.parseOrderBookData(message);
          if (orderBookData) {
            callback(orderBookData);
          }
        }
      );

      subscriptionIds.push(subscriptionId);
    }

    return subscriptionIds;
  }

  // Subscribe to public trades
  subscribeToTrades(symbols: string[], callback: (data: ByBitTrade) => void): string[] {
    const subscriptionIds: string[] = [];

    for (const symbol of symbols) {
      const subscriptionId = this.subscribe(
        [symbol],
        ['publicTrade'],
        (message: WebSocketMessage) => {
          const tradeData = this.parseTradeData(message);
          if (tradeData) {
            callback(tradeData);
          }
        }
      );

      subscriptionIds.push(subscriptionId);
    }

    return subscriptionIds;
  }

  // Send subscription message specific to ByBit format
  protected sendSubscription(subscription: SubscriptionRequest): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const messages: any[] = [];

    for (const channel of subscription.channels) {
      if (channel === 'tickers') {
        messages.push({
          op: 'subscribe',
          args: subscription.symbols.map(symbol => `tickers.${symbol}`)
        });
      } else if (channel.startsWith('orderbook.')) {
        const depth = channel.split('.')[1];
        messages.push({
          op: 'subscribe',
          args: subscription.symbols.map(symbol => `orderbook.${depth}.${symbol}`)
        });
      } else if (channel === 'publicTrade') {
        messages.push({
          op: 'subscribe',
          args: subscription.symbols.map(symbol => `publicTrade.${symbol}`)
        });
      }
    }

    // Send all subscription messages
    messages.forEach(message => {
      this.ws!.send(JSON.stringify(message));
      console.log(`ByBit subscription sent:`, message.args);
    });
  }

  // Send unsubscribe message specific to ByBit format
  protected sendUnsubscription(subscription: SubscriptionRequest): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const messages: any[] = [];

    for (const channel of subscription.channels) {
      if (channel === 'tickers') {
        messages.push({
          op: 'unsubscribe',
          args: subscription.symbols.map(symbol => `tickers.${symbol}`)
        });
      } else if (channel.startsWith('orderbook.')) {
        const depth = channel.split('.')[1];
        messages.push({
          op: 'unsubscribe',
          args: subscription.symbols.map(symbol => `orderbook.${depth}.${symbol}`)
        });
      } else if (channel === 'publicTrade') {
        messages.push({
          op: 'unsubscribe',
          args: subscription.symbols.map(symbol => `publicTrade.${symbol}`)
        });
      }
    }

    // Send all unsubscribe messages
    messages.forEach(message => {
      this.ws!.send(JSON.stringify(message));
      console.log(`ByBit unsubscription sent:`, message.args);
    });
  }

  // Process ByBit-specific message format
  protected processMessage(data: any, timestamp: number): WebSocketMessage | null {
    // Handle different message types from ByBit
    if (data.topic) {
      // Streaming data message
      return {
        type: data.topic,
        symbol: this.extractSymbolFromTopic(data.topic),
        data: data.data,
        timestamp,
        source: 'ByBit'
      };
    } else if (data.op) {
      // Operation message (subscribe, unsubscribe, etc.)
      return {
        type: 'operation',
        data: data,
        timestamp,
        source: 'ByBit'
      };
    } else if (data.success !== undefined) {
      // Response message
      return {
        type: 'response',
        data: data,
        timestamp,
        source: 'ByBit'
      };
    }

    return null;
  }

  // Extract symbol from ByBit topic string
  private extractSymbolFromTopic(topic: string): string | undefined {
    // Examples: tickers.BTCUSDT, orderbook.25.BTCUSDT, publicTrade.BTCUSDT
    const parts = topic.split('.');
    return parts[parts.length - 1];
  }

  // Parse ticker data from ByBit format
  private parseTickerData(message: WebSocketMessage): ByBitMarketData | null {
    if (!message.data || typeof message.data !== 'object') return null;

    const ticker = message.data as any;

    // ByBit ticker data structure
    if (ticker.symbol && ticker.lastPrice) {
      return {
        symbol: ticker.symbol,
        price: parseFloat(ticker.lastPrice),
        priceChange24h: parseFloat(ticker.price24hPcnt) * 100 || 0,
        volume24h: ticker.turnover24h || '0',
        high24h: parseFloat(ticker.highPrice24h) || 0,
        low24h: parseFloat(ticker.lowPrice24h) || 0,
        open24h: parseFloat(ticker.openPrice24h) || 0,
        timestamp: Date.now()
      };
    }

    return null;
  }

  // Parse order book data from ByBit format
  private parseOrderBookData(message: WebSocketMessage): ByBitOrderBook | null {
    if (!message.data || typeof message.data !== 'object') return null;

    const orderbook = message.data as any;

    // ByBit order book data structure
    if (orderbook.s && orderbook.b && orderbook.a) {
      return {
        symbol: orderbook.s,
        bids: orderbook.b.map((bid: [string, string]) => [parseFloat(bid[0]), parseFloat(bid[1])]),
        asks: orderbook.a.map((ask: [string, string]) => [parseFloat(ask[0]), parseFloat(ask[1])]),
        timestamp: Date.now()
      };
    }

    return null;
  }

  // Parse trade data from ByBit format
  private parseTradeData(message: WebSocketMessage): ByBitTrade | null {
    if (!message.data || typeof message.data !== 'object') return null;

    const tradeData = message.data as any;

    // ByBit trade data structure - can be array of trades
    if (Array.isArray(tradeData) && tradeData.length > 0) {
      // Return the most recent trade
      const latestTrade = tradeData[tradeData.length - 1];

      return {
        symbol: message.symbol || '',
        price: parseFloat(latestTrade.p),
        size: parseFloat(latestTrade.s || latestTrade.v),
        side: latestTrade.side === 'Buy' ? 'Buy' : 'Sell',
        timestamp: parseInt(latestTrade.T) || Date.now(),
        tradeId: latestTrade.i || latestTrade.trade_id || ''
      };
    }

    return null;
  }

  // Get current status with ByBit-specific metrics
  getExtendedStatus(): {
    connected: boolean;
    subscriptions: string[];
    messageRate: number;
    latency: number;
    uptime: number;
    lastUpdate: number;
  } {
    const status = this.getStatus();
    const subscriptions = this.getSubscriptions();

    return {
      connected: status.connected,
      subscriptions: subscriptions.map(sub => `${sub.channels.join(', ')}(${sub.symbols.join(', ')})`),
      messageRate: status.messagesPerSecond,
      latency: status.latency,
      uptime: status.uptime,
      lastUpdate: Date.now()
    };
  }

  // Validate connection health specifically for ByBit
  isByBitHealthy(): boolean {
    const status = this.getStatus();
    const recentMessages = this.getRecentMessages(10);

    // Check for recent ticker messages (at least one in last 30 seconds)
    const hasRecentTickers = recentMessages.some(msg =>
      msg.type.includes('tickers') &&
      (Date.now() - msg.timestamp) < 30000
    );

    return status.connected &&
           status.messagesPerSecond > 0 &&
           hasRecentTickers;
  }
}

// ByBit WebSocket factory
export class ByBitWebSocketFactory {
  private static instance: ByBitWebSocket;

  static getInstance(testnet: boolean = false): ByBitWebSocket {
    if (!ByBitWebSocketFactory.instance) {
      ByBitWebSocketFactory.instance = new ByBitWebSocket(testnet);
    }
    return ByBitWebSocketFactory.instance;
  }

  static createNew(testnet: boolean = false): ByBitWebSocket {
    return new ByBitWebSocket(testnet);
  }
}

// ByBit market data aggregator
export class ByBitMarketDataAggregator {
  private ws: ByBitWebSocket;
  private tickerData: Map<string, ByBitMarketData> = new Map();
  private orderBookData: Map<string, ByBitOrderBook> = new Map();
  private recentTrades: Map<string, ByBitTrade[]> = new Map();
  private lastUpdate: number = 0;

  constructor(testnet: boolean = false) {
    this.ws = ByBitWebSocketFactory.getInstance(testnet);
  }

  // Initialize data collection for symbols
  async initialize(symbols: string[]): Promise<void> {
    await this.ws.connect();

    // Subscribe to tickers
    this.ws.subscribeToTickers(symbols, (ticker) => {
      this.tickerData.set(ticker.symbol, ticker);
      this.lastUpdate = Date.now();
    });

    // Subscribe to order books
    this.ws.subscribeToOrderBook(symbols, 25, (orderbook) => {
      this.orderBookData.set(orderbook.symbol, orderbook);
    });

    // Subscribe to trades
    this.ws.subscribeToTrades(symbols, (trade) => {
      const trades = this.recentTrades.get(trade.symbol) || [];
      trades.push(trade);

      // Keep only last 100 trades per symbol
      if (trades.length > 100) {
        trades.shift();
      }

      this.recentTrades.set(trade.symbol, trades);
    });
  }

  // Get ticker data for symbol
  getTicker(symbol: string): ByBitMarketData | null {
    return this.tickerData.get(symbol) || null;
  }

  // Get all ticker data
  getAllTickers(): ByBitMarketData[] {
    return Array.from(this.tickerData.values());
  }

  // Get order book for symbol
  getOrderBook(symbol: string): ByBitOrderBook | null {
    return this.orderBookData.get(symbol) || null;
  }

  // Get recent trades for symbol
  getRecentTrades(symbol: string, limit: number = 10): ByBitTrade[] {
    const trades = this.recentTrades.get(symbol) || [];
    return trades.slice(-limit);
  }

  // Get system health
  getHealthStatus(): {
    connected: boolean;
    symbolsTracked: number;
    lastUpdate: number;
    messageRate: number;
    healthy: boolean;
  } {
    return {
      connected: this.ws.getStatus().connected,
      symbolsTracked: this.tickerData.size,
      lastUpdate: this.lastUpdate,
      messageRate: this.ws.getStatus().messagesPerSecond,
      healthy: this.ws.isByBitHealthy()
    };
  }

  // Disconnect
  disconnect(): void {
    this.ws.disconnect();
  }
}