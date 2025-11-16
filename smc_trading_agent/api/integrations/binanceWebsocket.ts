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
  private static readonly BINANCE_WS_BASE = 'wss://stream.binance.com:9443';
  private static readonly TESTNET_WS_BASE = 'wss://testnet.binance.vision';
  private activeStreams: string[] = [];
  private testnet: boolean;

  constructor(testnet: boolean = false) {
    // URL will be built dynamically based on streams
    const config: WebSocketConfig = {
      url: '', // Will be set when connecting
      name: 'Binance',
      exchanges: ['binance'],
      maxReconnectAttempts: 5,
      reconnectDelay: 2000,
      heartbeatInterval: 30000,
      connectionTimeout: 10000
    };

    super(config);
    this.testnet = testnet;
  }

  // Build Combined Streams URL for Binance
  private buildCombinedStreamsUrl(streams: string[]): string {
    const base = this.testnet ? BinanceWebSocket.TESTNET_WS_BASE : BinanceWebSocket.BINANCE_WS_BASE;
    const streamsParam = streams.join('/');
    return `${base}/stream?streams=${streamsParam}`;
  }

  // Subscribe to ticker data for symbols
  subscribeToTickers(symbols: string[], callback: (data: BinanceMarketData) => void): string[] {
    const subscriptionIds: string[] = [];

    // Register subscriptions first
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

    // If already connected, reconnect with new streams
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.disconnect();
      this.connect().catch(err => {
        console.error('Failed to reconnect with new streams:', err);
      });
    }

    return subscriptionIds;
  }

  // Subscribe to order book data
  subscribeToOrderBook(symbols: string[], depth: number = 20, callback: (data: BinanceOrderBook) => void): string[] {
    const subscriptionIds: string[] = [];

    // Register subscriptions first
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

    // If already connected, reconnect with new streams
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.disconnect();
      this.connect().catch(err => {
        console.error('Failed to reconnect with new streams:', err);
      });
    }

    return subscriptionIds;
  }

  // Subscribe to public trades
  subscribeToTrades(symbols: string[], callback: (data: BinanceTrade) => void): string[] {
    const subscriptionIds: string[] = [];

    // Register subscriptions first
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

    // If already connected, reconnect with new streams
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.disconnect();
      this.connect().catch(err => {
        console.error('Failed to reconnect with new streams:', err);
      });
    }

    return subscriptionIds;
  }

  // Override connect to use Combined Streams URL
  async connect(): Promise<void> {
    // Build streams list from active subscriptions
    const streams: string[] = [];
    const subscriptions = this.getSubscriptions();
    
    for (const sub of subscriptions) {
      for (const symbol of sub.symbols) {
        for (const channel of sub.channels) {
          // Map channel names to Binance format
          let binanceChannel = channel;
          if (channel === '24hrTicker') binanceChannel = 'ticker';
          if (channel === 'depth20') binanceChannel = 'depth20@100ms';
          if (channel === 'trade') binanceChannel = 'trade';
          
          const stream = `${symbol.toLowerCase()}@${binanceChannel}`;
          if (!streams.includes(stream)) {
            streams.push(stream);
          }
        }
      }
    }

    // If no streams, use default ticker for BTCUSDT
    if (streams.length === 0) {
      streams.push('btcusdt@ticker');
    }

    // Update URL with combined streams
    this.config.url = this.buildCombinedStreamsUrl(streams);
    this.activeStreams = streams;

    console.log(`Binance connecting to: ${this.config.url}`);
    return super.connect();
  }

  // Binance Combined Streams don't use SUBSCRIBE method
  // Streams are specified in the URL
  protected sendSubscription(subscription: SubscriptionRequest): void {
    // No-op for Binance - streams are in URL
    // If we need to add more streams, we need to reconnect with new URL
    console.log(`Binance subscription registered: ${subscription.symbols.join(',')} @ ${subscription.channels.join(',')}`);
  }

  // Binance Combined Streams don't use UNSUBSCRIBE method
  protected sendUnsubscription(subscription: SubscriptionRequest): void {
    // To unsubscribe, we need to reconnect with updated URL
    console.log(`Binance unsubscription registered: ${subscription.symbols.join(',')} @ ${subscription.channels.join(',')}`);
    // Note: Full reconnection would be needed to remove streams
  }

  // Process Binance-specific message format (Combined Streams)
  protected processMessage(data: any, timestamp: number): WebSocketMessage | null {
    try {
      // Binance Combined Streams format: { stream: "btcusdt@ticker", data: {...} }
      if (data.stream && data.data) {
        const [symbol, channel] = data.stream.split('@');
        
        // Map Binance channel names back to our format
        let mappedChannel = channel;
        if (channel === 'ticker') mappedChannel = '24hrTicker';
        if (channel.startsWith('depth')) mappedChannel = 'depth20';
        
        return {
          type: mappedChannel,
          symbol: symbol.toUpperCase(),
          data: data.data,
          timestamp: data.data.E || timestamp, // Use event time if available
          source: 'Binance'
        };
      }
      
      // Handle error messages
      if (data.error) {
        console.error('Binance WebSocket error:', data.error);
        return {
          type: 'error',
          data: data.error,
          timestamp,
          source: 'Binance'
        };
      }

      return null;
    } catch (error) {
      console.error('Error processing Binance message:', error, data);
      return null;
    }
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