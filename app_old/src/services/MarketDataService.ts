// HOTFIX: Singleton Market Data Service with throttling
// This prevents multiple instances and excessive API calls

import { binanceApi, MarketData } from './binanceApi';
import { toast } from 'sonner';

interface MarketDataServiceState {
  data: Record<string, MarketData>;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  subscribers: Set<(data: Record<string, MarketData>) => void>;
}

class MarketDataService {
  private static instance: MarketDataService | null = null;
  private state: MarketDataServiceState;
  private updateInterval: NodeJS.Timeout | null = null;
  private throttleTimeout: NodeJS.Timeout | null = null;
  private readonly THROTTLE_INTERVAL = 60000; // 60 seconds to avoid rate limits
  private readonly MAX_RETRIES = 3;
  private retryCount = 0;
  private isUpdating = false;

  private constructor() {
    this.state = {
      data: {},
      isConnected: false,
      isLoading: false,
      error: null,
      lastUpdate: null,
      subscribers: new Set()
    };
  }

  // Singleton pattern implementation
  public static getInstance(): MarketDataService {
    if (!MarketDataService.instance) {
      MarketDataService.instance = new MarketDataService();
    }
    return MarketDataService.instance;
  }

  // Subscribe to data updates
  public subscribe(callback: (data: Record<string, MarketData>) => void): () => void {
    this.state.subscribers.add(callback);
    
    // Immediately send current data if available
    if (Object.keys(this.state.data).length > 0) {
      callback(this.state.data);
    }
    
    // Return unsubscribe function
    return () => {
      this.state.subscribers.delete(callback);
    };
  }

  // Notify all subscribers
  private notifySubscribers(): void {
    this.state.subscribers.forEach(callback => {
      try {
        callback(this.state.data);
      } catch (error) {
        console.error('Error notifying subscriber:', error);
      }
    });
  }

  // Update state and notify subscribers
  private updateState(updates: Partial<MarketDataServiceState>): void {
    this.state = { ...this.state, ...updates };
    this.notifySubscribers();
  }

  // Throttled data fetch with deduplication
  public async fetchMarketData(symbols: string[]): Promise<void> {
    // Prevent multiple simultaneous updates
    if (this.isUpdating) {
      console.log('🔄 Market data update already in progress, skipping...');
      return;
    }

    // Check throttle
    const now = Date.now();
    const lastUpdateTime = this.state.lastUpdate?.getTime() || 0;
    const timeSinceLastUpdate = now - lastUpdateTime;

    if (timeSinceLastUpdate < this.THROTTLE_INTERVAL) {
      const remainingTime = this.THROTTLE_INTERVAL - timeSinceLastUpdate;
      console.log(`🕒 Throttling: ${remainingTime}ms remaining until next update`);
      return;
    }

    this.isUpdating = true;
    this.updateState({ isLoading: true, error: null });

    try {
      console.log('🔄 Fetching market data for symbols:', symbols);
      
      const tickers = await binanceApi.get24hrTicker();
      const filteredTickers = tickers.filter(ticker => 
        symbols.includes(ticker.symbol)
      );
      
      const newData: Record<string, MarketData> = {};
      filteredTickers.forEach(ticker => {
        newData[ticker.symbol] = {
          symbol: ticker.symbol,
          price: parseFloat(ticker.price),
          change: parseFloat(ticker.priceChange),
          changePercent: parseFloat(ticker.priceChangePercent),
          volume: parseFloat(ticker.volume),
          high: parseFloat(ticker.highPrice),
          low: parseFloat(ticker.lowPrice),
          open: parseFloat(ticker.openPrice)
        };
      });
      
      this.updateState({
        data: newData,
        isLoading: false,
        isConnected: true,
        lastUpdate: new Date(),
        error: null
      });
      
      this.retryCount = 0; // Reset retry count on success
      console.log('✅ Market data updated successfully');
      
    } catch (error) {
      console.error('❌ Failed to fetch market data:', error);
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch market data';
      
      // Implement retry logic
      if (this.retryCount < this.MAX_RETRIES) {
        this.retryCount++;
        console.log(`🔄 Retrying... (${this.retryCount}/${this.MAX_RETRIES})`);
        
        // Exponential backoff
        const retryDelay = Math.min(1000 * Math.pow(2, this.retryCount - 1), 10000);
        setTimeout(() => {
          this.fetchMarketData(symbols);
        }, retryDelay);
      } else {
        this.updateState({
          error: errorMessage,
          isConnected: false,
          isLoading: false
        });
        
        toast.error(`Market data error: ${errorMessage}`);
        this.retryCount = 0; // Reset for next attempt
      }
    } finally {
      this.isUpdating = false;
    }
  }

  // Start automatic updates
  public startAutoUpdate(symbols: string[], interval: number = this.THROTTLE_INTERVAL): void {
    this.stopAutoUpdate(); // Clear any existing interval
    
    console.log(`🔄 Starting auto-update every ${interval}ms for symbols:`, symbols);
    
    // Initial fetch
    this.fetchMarketData(symbols);
    
    // Set up interval
    this.updateInterval = setInterval(() => {
      this.fetchMarketData(symbols);
    }, interval);
  }

  // Stop automatic updates
  public stopAutoUpdate(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
      console.log('🛑 Auto-update stopped');
    }
  }

  // Get current state
  public getState(): Readonly<MarketDataServiceState> {
    return { ...this.state };
  }

  // Get specific symbol data
  public getSymbolData(symbol: string): MarketData | null {
    return this.state.data[symbol] || null;
  }

  // Get all data as array
  public getAllData(): MarketData[] {
    return Object.values(this.state.data);
  }

  // Check if symbol exists
  public hasSymbol(symbol: string): boolean {
    return symbol in this.state.data;
  }

  // Manual refresh with throttle check
  public async refresh(symbols: string[]): Promise<void> {
    await this.fetchMarketData(symbols);
  }

  // Reset service state
  public reset(): void {
    this.stopAutoUpdate();
    this.state = {
      data: {},
      isConnected: false,
      isLoading: false,
      error: null,
      lastUpdate: null,
      subscribers: new Set()
    };
    this.retryCount = 0;
    this.isUpdating = false;
  }

  // Cleanup method
  public destroy(): void {
    this.stopAutoUpdate();
    this.state.subscribers.clear();
    MarketDataService.instance = null;
  }

  // Additional methods for compatibility
  public async getExchangeInfo(): Promise<any> {
    try {
      // Mock exchange info for now
      return {
        symbols: [
          { symbol: 'BTCUSDT', status: 'TRADING', baseAsset: 'BTC', quoteAsset: 'USDT', filters: [] },
          { symbol: 'ETHUSDT', status: 'TRADING', baseAsset: 'ETH', quoteAsset: 'USDT', filters: [] }
        ],
        serverTime: Date.now()
      };
    } catch (error) {
      console.error('Error fetching exchange info:', error);
      throw error;
    }
  }

  public async getAllTickers(): Promise<any[]> {
    try {
      // Return current market data as tickers
      return Object.values(this.state.data);
    } catch (error) {
      console.error('Error fetching all tickers:', error);
      throw error;
    }
  }

  public async getTicker(symbol: string): Promise<any> {
    try {
      const data = this.getSymbolData(symbol);
      if (!data) {
        throw new Error(`No data available for symbol: ${symbol}`);
      }
      return data;
    } catch (error) {
      console.error(`Error fetching ticker for ${symbol}:`, error);
      throw error;
    }
  }

  public async getOrderBook(symbol: string, limit: number = 100): Promise<any> {
    try {
      // Mock order book data
      return {
        symbol,
        bids: [['50000', '1.0'], ['49999', '2.0']],
        asks: [['50001', '1.5'], ['50002', '2.5']],
        timestamp: Date.now()
      };
    } catch (error) {
      console.error(`Error fetching order book for ${symbol}:`, error);
      throw error;
    }
  }

  public async getKlines(symbol: string, interval: string, limit: number = 500): Promise<any[]> {
    try {
      // Mock klines data
      const now = Date.now();
      const klines = [];
      for (let i = 0; i < limit; i++) {
        klines.push([
          now - (i * 60000), // timestamp
          '50000', // open
          '50100', // high
          '49900', // low
          '50050', // close
          '100', // volume
          now - (i * 60000) + 59999, // close time
          '5000000', // quote asset volume
          100, // number of trades
          '50', // taker buy base asset volume
          '2500000', // taker buy quote asset volume
          '0' // ignore
        ]);
      }
      return klines.reverse();
    } catch (error) {
      console.error(`Error fetching klines for ${symbol}:`, error);
      throw error;
    }
  }

  public async getRecentTrades(symbol: string, limit: number = 100): Promise<any[]> {
    try {
      // Mock recent trades data
      const trades = [];
      for (let i = 0; i < limit; i++) {
        trades.push({
          id: i,
          price: '50000',
          qty: '0.01',
          quoteQty: '500',
          time: Date.now() - i * 1000,
          isBuyerMaker: i % 2 === 0,
          isBestMatch: true,
        });
      }
      return trades;
    } catch (error) {
      console.error(`Error fetching recent trades for ${symbol}:`, error);
      throw error;
    }
  }
}

// Export singleton instance
export const marketDataService = MarketDataService.getInstance();
export default MarketDataService;