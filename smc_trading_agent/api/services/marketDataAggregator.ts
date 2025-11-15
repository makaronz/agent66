/**
 * Market Data Aggregator
 * Consolidates data from multiple exchanges with validation, deduplication, and failover
 */

import { ByBitMarketDataAggregator, ByBitMarketData, ByBitOrderBook, ByBitTrade } from '../integrations/bybitWebsocket';
import { BinanceMarketDataAggregator, BinanceMarketData, BinanceOrderBook, BinanceTrade } from '../integrations/binanceWebsocket';
import { CircuitBreakerRegistry } from '../utils/circuitBreaker';
import { WebSocketManagerRegistry } from '../utils/websocketManager';

export interface UnifiedMarketData {
  symbol: string;
  price: number;
  priceChange: number;
  priceChangePercent: number;
  volume: string;
  high24h: number;
  low24h: number;
  open24h: number;
  timestamp: number;
  source: 'ByBit' | 'Binance' | 'Aggregated';
  confidence: number;
}

export interface UnifiedOrderBook {
  symbol: string;
  bids: [price: number, quantity: number][];
  asks: [price: number, quantity: number][];
  timestamp: number;
  source: 'ByBit' | 'Binance';
  spread: number;
  midPrice: number;
}

export interface UnifiedTrade {
  symbol: string;
  price: number;
  size: number;
  side: 'Buy' | 'Sell';
  timestamp: number;
  source: 'ByBit' | 'Binance';
  tradeId: string;
}

export interface DataQualityMetrics {
  symbol: string;
  lastUpdate: number;
  sources: string[];
  priceVariance: number;
  dataFreshness: number;
  confidence: number;
}

export class MarketDataAggregator {
  private bybitAggregator?: ByBitMarketDataAggregator;
  private binanceAggregator?: BinanceMarketDataAggregator;
  private marketDataCache: Map<string, UnifiedMarketData> = new Map();
  private orderBookCache: Map<string, UnifiedOrderBook> = new Map();
  private tradeHistory: Map<string, UnifiedTrade[]> = new Map();
  private dataQualityMetrics: Map<string, DataQualityMetrics> = new Map();
  private primarySource: 'ByBit' | 'Binance' = 'ByBit';
  private initialized: boolean = false;
  private startTime: number = Date.now();

  constructor(
    private symbols: string[],
    private config: {
      testnet: boolean;
      maxPriceVariance: number; // Maximum acceptable price difference between exchanges
      dataFreshnessThreshold: number; // Maximum age of data in ms
      aggregationWindow: number; // Window for data aggregation in ms
      enableFailover: boolean;
    } = {
      testnet: false,
      maxPriceVariance: 0.1, // 0.1%
      dataFreshnessThreshold: 5000, // 5 seconds
      aggregationWindow: 1000, // 1 second
      enableFailover: true
    }
  ) {}

  // Initialize market data aggregation
  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      console.log('Initializing Market Data Aggregator...');

      // Initialize primary source (ByBit)
      try {
        this.bybitAggregator = new ByBitMarketDataAggregator(this.config.testnet);
        await this.bybitAggregator.initialize(this.symbols);
        console.log('ByBit aggregator initialized successfully');
      } catch (error) {
        console.error('Failed to initialize ByBit aggregator:', error);
        if (this.config.enableFailover) {
          this.primarySource = 'Binance';
        }
      }

      // Initialize secondary source (Binance) for redundancy
      if (this.config.enableFailover) {
        try {
          this.binanceAggregator = new BinanceMarketDataAggregator(this.config.testnet);
          await this.binanceAggregator.initialize(this.symbols);
          console.log('Binance aggregator initialized successfully');
        } catch (error) {
          console.error('Failed to initialize Binance aggregator:', error);
        }
      }

      // Start data processing
      this.startDataProcessing();

      this.initialized = true;
      console.log('Market Data Aggregator initialized successfully');

    } catch (error) {
      console.error('Failed to initialize Market Data Aggregator:', error);
      throw error;
    }
  }

  // Start processing data from exchanges
  private startDataProcessing(): void {
    if (this.bybitAggregator) {
      this.processByBitData();
    }

    if (this.binanceAggregator) {
      this.processBinanceData();
    }

    // Start quality monitoring
    this.startQualityMonitoring();
  }

  // Process data from ByBit
  private processByBitData(): void {
    if (!this.bybitAggregator) return;

    // Process ticker data
    setInterval(() => {
      const tickers = this.bybitAggregator!.getAllTickers();
      for (const ticker of tickers) {
        const unifiedData = this.convertByBitTicker(ticker);
        this.updateMarketDataCache(unifiedData);
      }
    }, 1000);
  }

  // Process data from Binance
  private processBinanceData(): void {
    if (!this.binanceAggregator) return;

    // Process ticker data
    setInterval(() => {
      const tickers = this.binanceAggregator!.getAllTickers();
      for (const ticker of tickers) {
        const unifiedData = this.convertBinanceTicker(ticker);
        this.updateMarketDataCache(unifiedData);
      }
    }, 1000);
  }

  // Convert ByBit ticker to unified format
  private convertByBitTicker(ticker: ByBitMarketData): UnifiedMarketData {
    return {
      symbol: ticker.symbol,
      price: ticker.price,
      priceChange: ticker.priceChange24h,
      priceChangePercent: ticker.priceChange24h,
      volume: ticker.volume24h,
      high24h: ticker.high24h,
      low24h: ticker.low24h,
      open24h: ticker.open24h,
      timestamp: ticker.timestamp,
      source: 'ByBit',
      confidence: this.calculateConfidence('ByBit', ticker.timestamp)
    };
  }

  // Convert Binance ticker to unified format
  private convertBinanceTicker(ticker: BinanceMarketData): UnifiedMarketData {
    return {
      symbol: ticker.symbol,
      price: ticker.price,
      priceChange: ticker.priceChange,
      priceChangePercent: ticker.priceChangePercent,
      volume: ticker.volume,
      high24h: ticker.highPrice,
      low24h: ticker.lowPrice,
      open24h: ticker.openPrice,
      timestamp: ticker.timestamp,
      source: 'Binance',
      confidence: this.calculateConfidence('Binance', ticker.timestamp)
    };
  }

  // Update market data cache with validation
  private updateMarketDataCache(data: UnifiedMarketData): void {
    const existing = this.marketDataCache.get(data.symbol);

    if (existing) {
      // Validate price variance
      const priceDiff = Math.abs(data.price - existing.price) / existing.price;
      if (priceDiff > this.config.maxPriceVariance / 100) {
        console.warn(`High price variance detected for ${data.symbol}: ${priceDiff * 100}%`);
      }
    }

    // Update with new data if it's more recent or higher confidence
    if (!existing || data.timestamp > existing.timestamp || data.confidence > existing.confidence) {
      this.marketDataCache.set(data.symbol, data);
    }
  }

  // Calculate confidence score based on data freshness and source reliability
  private calculateConfidence(source: 'ByBit' | 'Binance', timestamp: number): number {
    const now = Date.now();
    const freshness = Math.max(0, 1 - (now - timestamp) / this.config.dataFreshnessThreshold);

    // Source reliability scores (ByBit is primary)
    const sourceScore = source === 'ByBit' ? 0.9 : 0.8;

    return freshness * sourceScore;
  }

  // Get unified market data for symbol
  getMarketData(symbol: string): UnifiedMarketData | null {
    return this.marketDataCache.get(symbol) || null;
  }

  // Get all market data
  getAllMarketData(): UnifiedMarketData[] {
    return Array.from(this.marketDataCache.values())
      .sort((a, b) => a.symbol.localeCompare(b.symbol));
  }

  // Get aggregated market data (best price from multiple sources)
  getAggregatedMarketData(symbols: string[]): UnifiedMarketData[] {
    const aggregated: UnifiedMarketData[] = [];

    for (const symbol of symbols) {
      const data = this.aggregateDataForSymbol(symbol);
      if (data) {
        aggregated.push(data);
      }
    }

    return aggregated;
  }

  // Aggregate data from multiple sources for a symbol
  private aggregateDataForSymbol(symbol: string): UnifiedMarketData | null {
    // Get data from all sources for this symbol
    const symbolData = Array.from(this.marketDataCache.values())
      .filter(data => data.symbol === symbol);

    if (symbolData.length === 0) return null;

    if (symbolData.length === 1) {
      return symbolData[0];
    }

    // Aggregate multiple sources
    const now = Date.now();
    const validData = symbolData.filter(data =>
      (now - data.timestamp) < this.config.dataFreshnessThreshold
    );

    if (validData.length === 0) return null;

    // Weight by confidence and recency
    const totalWeight = validData.reduce((sum, data) => sum + data.confidence, 0);

    const aggregated: UnifiedMarketData = {
      symbol,
      price: validData.reduce((sum, data) => sum + data.price * data.confidence, 0) / totalWeight,
      priceChange: validData[0].priceChange, // Use primary source
      priceChangePercent: validData[0].priceChangePercent,
      volume: validData[0].volume,
      high24h: Math.max(...validData.map(d => d.high24h)),
      low24h: Math.min(...validData.map(d => d.low24h)),
      open24h: validData[0].open24h,
      timestamp: Math.max(...validData.map(d => d.timestamp)),
      source: 'Aggregated',
      confidence: Math.min(...validData.map(d => d.confidence))
    };

    return aggregated;
  }

  // Get order book for symbol
  getOrderBook(symbol: string): UnifiedOrderBook | null {
    const primary = this.primarySource === 'ByBit' ? this.bybitAggregator : this.binanceAggregator;
    const secondary = this.primarySource === 'ByBit' ? this.binanceAggregator : this.bybitAggregator;

    try {
      // Try primary source first
      if (primary) {
        const orderBook = this.primarySource === 'ByBit'
          ? this.convertByBitOrderBook(primary.getOrderBook(symbol)!)
          : this.convertBinanceOrderBook(primary.getOrderBook(symbol)!);

        if (orderBook) {
          return orderBook;
        }
      }

      // Fallback to secondary source
      if (secondary) {
        const orderBook = this.primarySource === 'ByBit'
          ? this.convertBinanceOrderBook(secondary.getOrderBook(symbol)!)
          : this.convertByBitOrderBook(secondary.getOrderBook(symbol)!);

        if (orderBook) {
          return orderBook;
        }
      }
    } catch (error) {
      console.error(`Error getting order book for ${symbol}:`, error);
    }

    return null;
  }

  // Convert ByBit order book to unified format
  private convertByBitOrderBook(orderBook: ByBitOrderBook): UnifiedOrderBook {
    const bestBid = orderBook.bids[0]?.[0] || 0;
    const bestAsk = orderBook.asks[0]?.[0] || 0;
    const midPrice = bestBid && bestAsk ? (bestBid + bestAsk) / 2 : 0;
    const spread = bestAsk - bestBid;

    return {
      symbol: orderBook.symbol,
      bids: orderBook.bids,
      asks: orderBook.asks,
      timestamp: orderBook.timestamp,
      source: 'ByBit',
      spread,
      midPrice
    };
  }

  // Convert Binance order book to unified format
  private convertBinanceOrderBook(orderBook: BinanceOrderBook): UnifiedOrderBook {
    const bestBid = orderBook.bids[0]?.[0] || 0;
    const bestAsk = orderBook.asks[0]?.[0] || 0;
    const midPrice = bestBid && bestAsk ? (bestBid + bestAsk) / 2 : 0;
    const spread = bestAsk - bestBid;

    return {
      symbol: orderBook.symbol,
      bids: orderBook.bids,
      asks: orderBook.asks,
      timestamp: orderBook.timestamp,
      source: 'Binance',
      spread,
      midPrice
    };
  }

  // Start quality monitoring
  private startQualityMonitoring(): void {
    setInterval(() => {
      this.updateQualityMetrics();
    }, 5000); // Update every 5 seconds
  }

  // Update data quality metrics
  private updateQualityMetrics(): void {
    const now = Date.now();

    for (const symbol of this.symbols) {
      const symbolData = Array.from(this.marketDataCache.values())
        .filter(data => data.symbol === symbol);

      if (symbolData.length > 0) {
        const latest = symbolData.reduce((latest, current) =>
          current.timestamp > latest.timestamp ? current : latest
        );

        const sources = [...new Set(symbolData.map(d => d.source))];
        const priceVariance = this.calculatePriceVariance(symbolData);
        const dataFreshness = Math.max(0, 1 - (now - latest.timestamp) / this.config.dataFreshnessThreshold);

        const metrics: DataQualityMetrics = {
          symbol,
          lastUpdate: latest.timestamp,
          sources,
          priceVariance,
          dataFreshness,
          confidence: latest.confidence
        };

        this.dataQualityMetrics.set(symbol, metrics);
      }
    }
  }

  // Calculate price variance between sources
  private calculatePriceVariance(data: UnifiedMarketData[]): number {
    if (data.length < 2) return 0;

    const prices = data.map(d => d.price);
    const mean = prices.reduce((sum, price) => sum + price, 0) / prices.length;
    const variance = prices.reduce((sum, price) => sum + Math.pow(price - mean, 2), 0) / prices.length;

    return Math.sqrt(variance) / mean; // Coefficient of variation
  }

  // Get data quality metrics
  getDataQualityMetrics(): DataQualityMetrics[] {
    return Array.from(this.dataQualityMetrics.values())
      .sort((a, b) => a.symbol.localeCompare(b.symbol));
  }

  // Get system health status
  getHealthStatus(): {
    connected: boolean;
    primarySource: string;
    activeSources: string[];
    symbolsTracked: number;
    dataQuality: 'excellent' | 'good' | 'fair' | 'poor';
    lastUpdate: number;
    uptime: number;
    actualConnections: {
      bybitWebSocket: boolean;
      binanceWebSocket: boolean;
      both: boolean;
    };
  } {
    // Check actual WebSocket connection status, not just health flags
    const bybitStatus = this.bybitAggregator?.getHealthStatus() || { connected: false, healthy: false };
    const binanceStatus = this.binanceAggregator?.getHealthStatus() || { connected: false, healthy: false };

    const activeSources = [];
    if (bybitStatus.connected && bybitStatus.healthy) {
      activeSources.push('ByBit');
    }
    if (binanceStatus.connected && binanceStatus.healthy) {
      activeSources.push('Binance');
    }

    // Calculate overall data quality
    const qualityMetrics = this.getDataQualityMetrics();
    const avgConfidence = qualityMetrics.length > 0
      ? qualityMetrics.reduce((sum, m) => sum + m.confidence, 0) / qualityMetrics.length
      : 0;

    let dataQuality: 'excellent' | 'good' | 'fair' | 'poor';
    if (avgConfidence > 0.8) dataQuality = 'excellent';
    else if (avgConfidence > 0.6) dataQuality = 'good';
    else if (avgConfidence > 0.4) dataQuality = 'fair';
    else dataQuality = 'poor';

    return {
      connected: activeSources.length > 0,
      primarySource: this.primarySource,
      activeSources,
      symbolsTracked: this.marketDataCache.size,
      dataQuality,
      lastUpdate: Date.now(),
      uptime: Date.now() - this.startTime, // Track actual uptime since start
      actualConnections: {
        bybitWebSocket: bybitStatus.connected,
        binanceWebSocket: binanceStatus.connected,
        both: bybitStatus.connected && binanceStatus.connected
      }
    };
  }

  // Disconnect all connections
  async disconnect(): Promise<void> {
    if (this.bybitAggregator) {
      this.bybitAggregator.disconnect();
    }
    if (this.binanceAggregator) {
      this.binanceAggregator.disconnect();
    }

    // Clear caches
    this.marketDataCache.clear();
    this.orderBookCache.clear();
    this.tradeHistory.clear();
    this.dataQualityMetrics.clear();

    this.initialized = false;
  }

  // Get statistics
  getStatistics(): {
    totalMessages: number;
    messagesPerSecond: number;
    averageLatency: number;
    circuitBreakerStatus: any;
    rateLimitStatus: any;
  } {
    const wsRegistry = WebSocketManagerRegistry.getInstance();
    const circuitRegistry = CircuitBreakerRegistry.getInstance();

    return {
      totalMessages: 0, // TODO: Track total messages
      messagesPerSecond: wsRegistry.getAggregatedStats().totalMessagesPerSecond,
      averageLatency: wsRegistry.getAggregatedStats().averageLatency,
      circuitBreakerStatus: circuitRegistry.getMetrics(),
      rateLimitStatus: {} // TODO: Add rate limiter status
    };
  }
}