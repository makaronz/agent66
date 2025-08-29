import { binanceApi } from './binanceApi';
import { db } from '../supabase';
import { toast } from 'sonner';

interface SMCPattern {
  type: 'BOS' | 'CHoCH' | 'FVG' | 'OB' | 'LQ';
  direction: 'bullish' | 'bearish';
  confidence: number;
  price: number;
  timestamp: number;
  metadata: {
    timeframe: string;
    volume?: number;
    strength?: number;
    [key: string]: any;
  };
}

interface PriceData {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: number;
}

class SMCSignalGenerator {
  private isRunning = false;
  private intervals: Map<string, NodeJS.Timeout> = new Map();
  private priceHistory: Map<string, PriceData[]> = new Map();
  private readonly HISTORY_LIMIT = 200;
  private readonly ANALYSIS_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'];

  constructor() {
    this.initializePriceHistory();
  }

  private async initializePriceHistory() {
    // Initialize empty price history - data will be populated from WebSocket streams
    for (const symbol of this.ANALYSIS_SYMBOLS) {
      this.priceHistory.set(symbol, []);
    }
    console.log('Price history initialized - waiting for WebSocket data');
  }

  public start() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    console.log('SMC Signal Generator started');
    
    // Start analysis for each symbol
    this.ANALYSIS_SYMBOLS.forEach(symbol => {
      this.startSymbolAnalysis(symbol);
    });
  }

  public stop() {
    this.isRunning = false;
    
    // Clear all intervals
    this.intervals.forEach(interval => clearInterval(interval));
    this.intervals.clear();
    
    console.log('SMC Signal Generator stopped');
  }

  private startSymbolAnalysis(symbol: string) {
    // Update price data every 15 seconds
    const interval = setInterval(async () => {
      if (!this.isRunning) return;
      
      try {
        await this.updatePriceData(symbol);
        await this.analyzeSymbol(symbol);
      } catch (error) {
        console.error(`Error analyzing ${symbol}:`, error);
      }
    }, 15000);
    
    this.intervals.set(symbol, interval);
  }

  private async updatePriceData(symbol: string) {
    // Skip update if WebSocket is not connected
    if (!binanceApi.isConnected()) {
      console.warn(`WebSocket not connected, skipping price update for ${symbol}`);
      return;
    }
    
    // Price data is now updated via WebSocket streams through updatePriceFromWebSocket method
    // This method is kept for compatibility but doesn't make REST API calls
    console.log(`Price data for ${symbol} is updated via WebSocket streams`);
  }
  
  public updatePriceFromWebSocket(symbol: string, marketData: any) {
    if (!marketData) return;
    
    const history = this.priceHistory.get(symbol) || [];
    const timestamp = Date.now();
    
    // Add new price point from WebSocket data
    const newPriceData: PriceData = {
      open: marketData.open || (history.length > 0 ? history[history.length - 1].close : marketData.price),
      high: marketData.high || marketData.price,
      low: marketData.low || marketData.price,
      close: marketData.close || marketData.price,
      volume: marketData.volume || 0,
      timestamp
    };
    
    history.push(newPriceData);
    
    // Keep only recent data
    if (history.length > this.HISTORY_LIMIT) {
      history.shift();
    }
    
    this.priceHistory.set(symbol, history);
  }

  private async analyzeSymbol(symbol: string) {
    const history = this.priceHistory.get(symbol);
    if (!history || history.length < 50) return;
    
    const patterns = [
      ...this.detectBreakOfStructure(symbol, history),
      ...this.detectChangeOfCharacter(symbol, history),
      ...this.detectFairValueGaps(symbol, history),
      ...this.detectOrderBlocks(symbol, history),
      ...this.detectLiquidity(symbol, history)
    ];
    
    // Process high-confidence patterns
    for (const pattern of patterns) {
      if (pattern.confidence >= 0.7) {
        await this.createSignal(symbol, pattern);
      }
    }
  }

  private detectBreakOfStructure(symbol: string, history: PriceData[]): SMCPattern[] {
    const patterns: SMCPattern[] = [];
    const recent = history.slice(-20);
    
    if (recent.length < 10) return patterns;
    
    // Find recent highs and lows
    const highs = this.findSwingHighs(recent);
    const lows = this.findSwingLows(recent);
    
    const currentPrice = recent[recent.length - 1].close;
    
    // Check for bullish BOS (break above recent high)
    if (highs.length > 0) {
      const lastHigh = Math.max(...highs.map(h => h.price));
      if (currentPrice > lastHigh * 1.002) { // 0.2% buffer
        patterns.push({
          type: 'BOS',
          direction: 'bullish',
          confidence: this.calculateBOSConfidence(recent, 'bullish'),
          price: currentPrice,
          timestamp: Date.now(),
          metadata: {
            timeframe: '15m',
            volume: recent[recent.length - 1].volume,
            strength: (currentPrice - lastHigh) / lastHigh
          }
        });
      }
    }
    
    // Check for bearish BOS (break below recent low)
    if (lows.length > 0) {
      const lastLow = Math.min(...lows.map(l => l.price));
      if (currentPrice < lastLow * 0.998) { // 0.2% buffer
        patterns.push({
          type: 'BOS',
          direction: 'bearish',
          confidence: this.calculateBOSConfidence(recent, 'bearish'),
          price: currentPrice,
          timestamp: Date.now(),
          metadata: {
            timeframe: '15m',
            volume: recent[recent.length - 1].volume,
            strength: (lastLow - currentPrice) / lastLow
          }
        });
      }
    }
    
    return patterns;
  }

  private detectChangeOfCharacter(symbol: string, history: PriceData[]): SMCPattern[] {
    const patterns: SMCPattern[] = [];
    const recent = history.slice(-30);
    
    if (recent.length < 15) return patterns;
    
    // Simplified CHoCH detection based on trend reversal
    const trend = this.identifyTrend(recent.slice(-15));
    const previousTrend = this.identifyTrend(recent.slice(-30, -15));
    
    if (trend !== previousTrend && trend !== 'sideways') {
      patterns.push({
        type: 'CHoCH',
        direction: trend === 'bullish' ? 'bullish' : 'bearish',
        confidence: 0.75,
        price: recent[recent.length - 1].close,
        timestamp: Date.now(),
        metadata: {
          timeframe: '15m',
          previousTrend,
          currentTrend: trend
        }
      });
    }
    
    return patterns;
  }

  private detectFairValueGaps(symbol: string, history: PriceData[]): SMCPattern[] {
    const patterns: SMCPattern[] = [];
    const recent = history.slice(-10);
    
    if (recent.length < 3) return patterns;
    
    for (let i = 1; i < recent.length - 1; i++) {
      const prev = recent[i - 1];
      const current = recent[i];
      const next = recent[i + 1];
      
      // Bullish FVG: gap between prev.high and next.low
      if (prev.high < next.low && current.close > current.open) {
        const gapSize = (next.low - prev.high) / prev.high;
        if (gapSize > 0.001) { // Minimum 0.1% gap
          patterns.push({
            type: 'FVG',
            direction: 'bullish',
            confidence: Math.min(0.9, 0.6 + gapSize * 100),
            price: (prev.high + next.low) / 2,
            timestamp: Date.now(),
            metadata: {
              timeframe: '15m',
              gapSize,
              topPrice: next.low,
              bottomPrice: prev.high
            }
          });
        }
      }
      
      // Bearish FVG: gap between prev.low and next.high
      if (prev.low > next.high && current.close < current.open) {
        const gapSize = (prev.low - next.high) / next.high;
        if (gapSize > 0.001) {
          patterns.push({
            type: 'FVG',
            direction: 'bearish',
            confidence: Math.min(0.9, 0.6 + gapSize * 100),
            price: (prev.low + next.high) / 2,
            timestamp: Date.now(),
            metadata: {
              timeframe: '15m',
              gapSize,
              topPrice: prev.low,
              bottomPrice: next.high
            }
          });
        }
      }
    }
    
    return patterns;
  }

  private detectOrderBlocks(symbol: string, history: PriceData[]): SMCPattern[] {
    const patterns: SMCPattern[] = [];
    const recent = history.slice(-20);
    
    if (recent.length < 5) return patterns;
    
    // Find strong volume candles that could be order blocks
    const avgVolume = recent.reduce((sum, candle) => sum + candle.volume, 0) / recent.length;
    
    for (let i = 1; i < recent.length - 1; i++) {
      const candle = recent[i];
      
      // High volume candle
      if (candle.volume > avgVolume * 1.5) {
        const bodySize = Math.abs(candle.close - candle.open);
        const candleRange = candle.high - candle.low;
        
        // Strong bullish candle (potential bullish OB)
        if (candle.close > candle.open && bodySize > candleRange * 0.7) {
          patterns.push({
            type: 'OB',
            direction: 'bullish',
            confidence: 0.7,
            price: candle.low,
            timestamp: Date.now(),
            metadata: {
              timeframe: '15m',
              volume: candle.volume,
              volumeRatio: candle.volume / avgVolume,
              highPrice: candle.high,
              lowPrice: candle.low
            }
          });
        }
        
        // Strong bearish candle (potential bearish OB)
        if (candle.close < candle.open && bodySize > candleRange * 0.7) {
          patterns.push({
            type: 'OB',
            direction: 'bearish',
            confidence: 0.7,
            price: candle.high,
            timestamp: Date.now(),
            metadata: {
              timeframe: '15m',
              volume: candle.volume,
              volumeRatio: candle.volume / avgVolume,
              highPrice: candle.high,
              lowPrice: candle.low
            }
          });
        }
      }
    }
    
    return patterns;
  }

  private detectLiquidity(symbol: string, history: PriceData[]): SMCPattern[] {
    const patterns: SMCPattern[] = [];
    const recent = history.slice(-15);
    
    if (recent.length < 10) return patterns;
    
    // Find equal highs/lows that could be liquidity zones
    const highs = this.findSwingHighs(recent);
    const lows = this.findSwingLows(recent);
    
    // Check for equal highs (sell-side liquidity)
    for (let i = 0; i < highs.length - 1; i++) {
      for (let j = i + 1; j < highs.length; j++) {
        const priceDiff = Math.abs(highs[i].price - highs[j].price) / highs[i].price;
        if (priceDiff < 0.005) { // Within 0.5%
          patterns.push({
            type: 'LQ',
            direction: 'bearish',
            confidence: 0.65,
            price: (highs[i].price + highs[j].price) / 2,
            timestamp: Date.now(),
            metadata: {
              timeframe: '15m',
              liquidityType: 'sell-side',
              priceLevel: (highs[i].price + highs[j].price) / 2
            }
          });
        }
      }
    }
    
    // Check for equal lows (buy-side liquidity)
    for (let i = 0; i < lows.length - 1; i++) {
      for (let j = i + 1; j < lows.length; j++) {
        const priceDiff = Math.abs(lows[i].price - lows[j].price) / lows[i].price;
        if (priceDiff < 0.005) { // Within 0.5%
          patterns.push({
            type: 'LQ',
            direction: 'bullish',
            confidence: 0.65,
            price: (lows[i].price + lows[j].price) / 2,
            timestamp: Date.now(),
            metadata: {
              timeframe: '15m',
              liquidityType: 'buy-side',
              priceLevel: (lows[i].price + lows[j].price) / 2
            }
          });
        }
      }
    }
    
    return patterns;
  }

  private findSwingHighs(data: PriceData[]): { price: number; index: number }[] {
    const swingHighs: { price: number; index: number }[] = [];
    
    for (let i = 2; i < data.length - 2; i++) {
      const current = data[i];
      const isSwingHigh = 
        current.high > data[i - 1].high &&
        current.high > data[i - 2].high &&
        current.high > data[i + 1].high &&
        current.high > data[i + 2].high;
      
      if (isSwingHigh) {
        swingHighs.push({ price: current.high, index: i });
      }
    }
    
    return swingHighs;
  }

  private findSwingLows(data: PriceData[]): { price: number; index: number }[] {
    const swingLows: { price: number; index: number }[] = [];
    
    for (let i = 2; i < data.length - 2; i++) {
      const current = data[i];
      const isSwingLow = 
        current.low < data[i - 1].low &&
        current.low < data[i - 2].low &&
        current.low < data[i + 1].low &&
        current.low < data[i + 2].low;
      
      if (isSwingLow) {
        swingLows.push({ price: current.low, index: i });
      }
    }
    
    return swingLows;
  }

  private calculateBOSConfidence(data: PriceData[], direction: 'bullish' | 'bearish'): number {
    const recentVolume = data.slice(-3).reduce((sum, candle) => sum + candle.volume, 0) / 3;
    const avgVolume = data.reduce((sum, candle) => sum + candle.volume, 0) / data.length;
    
    const volumeConfidence = Math.min(1, recentVolume / avgVolume);
    const baseConfidence = 0.7;
    
    return Math.min(0.95, baseConfidence + (volumeConfidence - 1) * 0.2);
  }

  private identifyTrend(data: PriceData[]): 'bullish' | 'bearish' | 'sideways' {
    if (data.length < 5) return 'sideways';
    
    const firstPrice = data[0].close;
    const lastPrice = data[data.length - 1].close;
    const priceChange = (lastPrice - firstPrice) / firstPrice;
    
    if (priceChange > 0.01) return 'bullish';
    if (priceChange < -0.01) return 'bearish';
    return 'sideways';
  }

  private async createSignal(symbol: string, pattern: SMCPattern) {
    try {
      const signalData = {
        symbol,
        signal_type: pattern.type,
        direction: pattern.direction,
        confidence: pattern.confidence,
        price: pattern.price,
        timeframe: pattern.metadata.timeframe,
        metadata: pattern.metadata,
        processed: false,
        created_at: new Date().toISOString()
      };
      
      const { data, error } = await db.signals.create(signalData);
      
      if (error) {
        console.error('Failed to create signal:', error);
        return;
      }
      
      // Show notification for high-confidence signals
      if (pattern.confidence >= 0.8) {
        toast.success(
          `Nowy sygnał ${pattern.type}: ${symbol} ${pattern.direction} (${(pattern.confidence * 100).toFixed(0)}%)`,
          { duration: 6000 }
        );
      }
      
      console.log(`Created ${pattern.type} signal for ${symbol}:`, data);
    } catch (error) {
      console.error('Error creating signal:', error);
    }
  }
}

// Export singleton instance
export const smcSignalGenerator = new SMCSignalGenerator();
export default smcSignalGenerator;