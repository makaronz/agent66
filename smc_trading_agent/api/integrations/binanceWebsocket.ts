/**
 * Binance WebSocket Integration
 * Secondary real-time market data source with failover capabilities
 */

import { WebSocketManager, WebSocketConfig, WebSocketMessage, SubscriptionRequest } from '../utils/websocketManager';
import { RateLimiterManager } from '../utils/rateLimiter';

export interface BinanceMarketData {
  symbol: string;
  price: number;
  priceChange: number;
  priceChangePercent: number;
  volume: string;
  highPrice: number;
  lowPrice: number;
  openPrice: number;
  timestamp: number;
}

export interface BinanceOrderBook {
  symbol: string;
  lastUpdateId: number;
  bids: [price: number, quantity: number][];
  asks: [price: number, quantity: number][];
  timestamp: number;
}

export interface BinanceTrade {
  symbol: string;
  price: number;
  quantity: number;
  buyerOrderId: string;
  sellerOrderId: string;
  timestamp: number;
  isBuyerMaker: boolean;
}

export class BinanceWebSocket extends WebSocketManager {
  private static readonly BINANCE_WS_URL = 'wss://stream.binance.com:9443/ws';
  private static readonly TESTNET_WS_URL = 'wss://testnet.binance.vision/ws';

  constructor(testnet: boolean = false) {
    const config: WebSocketConfig = {
      url: testnet ? BinanceWebSocket.TESTNET_WS_URL : BinanceWebSocket.BINANCE_WS_URL,
      name: 'Binance',
      exchanges: ['binance'],
      maxReconnectAttempts: 5,
      reconnectDelay: 2000,
      heartbeatInterval: 30000,
      connectionTimeout: 10000
    };

    super(config);
  }

  // Subscribe to ticker data for symbols
  subscribeToTickers(symbols: string[], callback: (data: BinanceMarketData) => void): string[] {
    const subscriptionIds: string[] = [];

    // Binance requires individual ticker subscriptions
    for (const symbol of symbols) {
      const subscriptionId = this.subscribe(
        [symbol.toLowerCase()],
        ['24hrTicker'],
        (message: WebSocketMessage) => {
          const tickerData = this.parseTickerData(message);
          if (tickerData) {
            callback(tickerData);
          }
        }
      );

      subscriptionIds.push(subscriptionId);
    }

    return subscriptionIds;
  }

  // Subscribe to order book data
  subscribeToOrderBook(symbols: string[], depth: number = 20, callback: (data: BinanceOrderBook) => void): string[] {
    const subscriptionIds: string[] = [];

    for (const symbol of symbols) {
      const subscriptionId = this.subscribe(
        [symbol.toLowerCase()],
        [`depth${depth}`],
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
  subscribeToTrades(symbols: string[], callback: (data: BinanceTrade) => void): string[] {
    const subscriptionIds: string[] = [];

    for (const symbol of symbols) {
      const subscriptionId = this.subscribe(
        [symbol.toLowerCase()],
        ['trade'],
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

  // Send subscription message specific to Binance format
  protected sendSubscription(subscription: SubscriptionRequest): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const messages: any[] = [];

    for (const symbol of subscription.symbols) {
      for (const channel of subscription.channels) {
        const stream = `${symbol}@${channel}`;
        messages.push({
          method: 'SUBSCRIBE',
          params: [stream],
          id: Date.now() + Math.random()
        });
      }
    }

    // Send all subscription messages
    messages.forEach(message => {
      this.ws!.send(JSON.stringify(message));
      console.log(`Binance subscription sent:`, message.params);
    });
  }

  // Send unsubscribe message specific to Binance format
  protected sendUnsubscription(subscription: SubscriptionRequest): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const messages: any[] = [];

    for (const symbol of subscription.symbols) {
      for (const channel of subscription.channels) {
        const stream = `${symbol}@${channel}`;
        messages.push({
          method: 'UNSUBSCRIBE',
          params: [stream],
          id: Date.now() + Math.random()
        });
      }
    }

    // Send all unsubscribe messages
    messages.forEach(message => {
      this.ws!.send(JSON.stringify(message));
      console.log(`Binance unsubscription sent:`, message.params);
    });
  }

  // Process Binance-specific message format
  protected processMessage(data: any, timestamp: number): WebSocketMessage | null {
    // Handle different message types from Binance
    if (data.stream) {
      // Streaming data message
      const [symbol, channel] = data.stream.split('@');
      return {
        type: channel,
        symbol: symbol.toUpperCase(),
        data: data.data,
        timestamp,
        source: 'Binance'
      };
    } else if (data.result !== undefined) {
      // Response message (subscription confirmation)
      return {
        type: 'response',
        data: data,
        timestamp,
        source: 'Binance'
      };
    } else if (data.error) {
      // Error message
      return {
        type: 'error',
        data: data.error,
        timestamp,
        source: 'Binance'
      };
    }

    return null;
  }

  // Parse ticker data from Binance format
  private parseTickerData(message: WebSocketMessage): BinanceMarketData | null {
    if (!message.data || typeof message.data !== 'object') return null;

    const ticker = message.data as any;

    // Binance ticker data structure
    if (ticker.s && ticker.c) {
      return {
        symbol: ticker.s,
        price: parseFloat(ticker.c),
        priceChange: parseFloat(ticker.P) ? parseFloat(ticker.c) - parseFloat(ticker.o) : 0,
        priceChangePercent: parseFloat(ticker.P) || 0,
        volume: ticker.v || '0',
        highPrice: parseFloat(ticker.h) || 0,
        lowPrice: parseFloat(ticker.l) || 0,
        openPrice: parseFloat(ticker.o) || 0,
        timestamp: ticker.E || Date.now()
      };
    }

    return null;
  }

  // Parse order book data from Binance format
  private parseOrderBookData(message: WebSocketMessage): BinanceOrderBook | null {
    if (!message.data || typeof message.data !== 'object') return null;

    const orderbook = message.data as any;

    // Binance order book data structure
    if (orderbook.s && orderbook.b && orderbook.a) {
      return {
        symbol: orderbook.s,
        lastUpdateId: orderbook.lastUpdateId || 0,
        bids: orderbook.b.map((bid: [string, string]) => [parseFloat(bid[0]), parseFloat(bid[1])]),
        asks: orderbook.a.map((ask: [string, string]) => [parseFloat(ask[0]), parseFloat(ask[1])]),
        timestamp: orderbook.T || Date.now()
      };
    }

    return null;
  }

  // Parse trade data from Binance format
  private parseTradeData(message: WebSocketMessage): BinanceTrade | null {
    if (!message.data || typeof message.data !== 'object') return null;

    const trade = message.data as any;

    // Binance trade data structure
    if (trade.s && trade.p && trade.q) {
      return {
        symbol: trade.s,
        price: parseFloat(trade.p),
        quantity: parseFloat(trade.q),
        buyerOrderId: trade.b || '',
        sellerOrderId: trade.a || '',
        timestamp: trade.T || Date.now(),
        isBuyerMaker: trade.m || false
      };
    }

    return null;
  }

  // Get current status with Binance-specific metrics
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

  // Validate connection health specifically for Binance
  isBinanceHealthy(): boolean {
    const status = this.getStatus();
    const recentMessages = this.getRecentMessages(10);

    // Check for recent ticker messages (at least one in last 30 seconds)
    const hasRecentTickers = recentMessages.some(msg =>
      msg.type.includes('Ticker') &&
      (Date.now() - msg.timestamp) < 30000
    );

    return status.connected &&
           status.messagesPerSecond > 0 &&
           hasRecentTickers;
  }
}

// Binance WebSocket factory
export class BinanceWebSocketFactory {
  private static instance: BinanceWebSocket;

  static getInstance(testnet: boolean = false): BinanceWebSocket {
    if (!BinanceWebSocketFactory.instance) {
      BinanceWebSocketFactory.instance = new BinanceWebSocket(testnet);
    }
    return BinanceWebSocketFactory.instance;
  }

  static createNew(testnet: boolean = false): BinanceWebSocket {
    return new BinanceWebSocket(testnet);
  }
}

// Binance market data aggregator
export class BinanceMarketDataAggregator {
  private ws: BinanceWebSocket;
  private tickerData: Map<string, BinanceMarketData> = new Map();
  private orderBookData: Map<string, BinanceOrderBook> = new Map();
  private recentTrades: Map<string, BinanceTrade[]> = new Map();
  private lastUpdate: number = 0;

  constructor(testnet: boolean = false) {
    this.ws = BinanceWebSocketFactory.getInstance(testnet);
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
    this.ws.subscribeToOrderBook(symbols, 20, (orderbook) => {
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
  getTicker(symbol: string): BinanceMarketData | null {
    return this.tickerData.get(symbol) || null;
  }

  // Get all ticker data
  getAllTickers(): BinanceMarketData[] {
    return Array.from(this.tickerData.values());
  }

  // Get order book for symbol
  getOrderBook(symbol: string): BinanceOrderBook | null {
    return this.orderBookData.get(symbol) || null;
  }

  // Get recent trades for symbol
  getRecentTrades(symbol: string, limit: number = 10): BinanceTrade[] {
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
      healthy: this.ws.isBinanceHealthy()
    };
  }

  // Disconnect
  disconnect(): void {
    this.ws.disconnect();
  }
}