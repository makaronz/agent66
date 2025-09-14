import { binanceApi } from './binanceApi';
import { smcSignalGenerator } from './smcSignalGenerator';
import { toast } from 'sonner';

interface PatternDetectionConfig {
  symbols: string[];
  intervals: string[];
  detectionIntervalMs: number;
  maxConcurrentDetections: number;
}

class BackgroundPatternDetectionService {
  private isRunning = false;
  private detectionIntervals: Map<string, NodeJS.Timeout> = new Map();
  private activeDetections = 0;
  private config: PatternDetectionConfig;
  private lastPatternCheck: Map<string, number> = new Map();
  private priceDataCache: Map<string, any[]> = new Map();

  constructor() {
    this.config = {
      symbols: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'],
      intervals: ['5m', '15m', '1h'],
      detectionIntervalMs: 30000, // 30 seconds
      maxConcurrentDetections: 3
    };
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      console.log('Background pattern detection is already running');
      return;
    }

    this.isRunning = true;
    console.log('Starting background pattern detection service...');
    
    // SMC signal generator is already initialized in constructor
    
    // Start pattern detection for each symbol-interval combination
    for (const symbol of this.config.symbols) {
      for (const interval of this.config.intervals) {
        const key = `${symbol}_${interval}`;
        this.startPatternDetectionForPair(symbol, interval, key);
      }
    }

    toast.success('Background pattern detection started', {
      description: `Monitoring ${this.config.symbols.length} symbols across ${this.config.intervals.length} timeframes`
    });
  }

  stop(): void {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;
    console.log('Stopping background pattern detection service...');

    // Clear all intervals
    for (const [key, interval] of this.detectionIntervals) {
      clearInterval(interval);
      this.detectionIntervals.delete(key);
    }

    this.activeDetections = 0;
    this.lastPatternCheck.clear();
    
    // Clear price data cache
    this.priceDataCache.clear();

    toast.info('Background pattern detection stopped');
  }

  private getCachedPriceData(symbol: string): any[] | null {
    return this.priceDataCache.get(symbol) || null;
  }

  public updatePriceData(symbol: string, marketData: any): void {
    if (!marketData) return;
    
    const pricePoint = {
      timestamp: Date.now(),
      open: marketData.open || marketData.price,
      high: marketData.high || marketData.price,
      low: marketData.low || marketData.price,
      close: marketData.close || marketData.price,
      volume: marketData.volume || 0
    };
    
    const existing = this.priceDataCache.get(symbol) || [];
    existing.push(pricePoint);
    
    // Keep only last 200 data points
    if (existing.length > 200) {
      existing.shift();
    }
    
    this.priceDataCache.set(symbol, existing);
  }

  private startPatternDetectionForPair(symbol: string, interval: string, key: string): void {
    const intervalId = setInterval(async () => {
      if (this.activeDetections >= this.config.maxConcurrentDetections) {
        console.log(`Skipping detection for ${key} - max concurrent detections reached`);
        return;
      }

      const lastCheck = this.lastPatternCheck.get(key) || 0;
      const now = Date.now();
      
      // Avoid too frequent checks for the same pair
      if (now - lastCheck < this.config.detectionIntervalMs * 0.8) {
        return;
      }

      this.activeDetections++;
      this.lastPatternCheck.set(key, now);

      try {
        await this.detectPatternsForPair(symbol, interval);
      } catch (error) {
        console.error(`Error detecting patterns for ${key}:`, error);
      } finally {
        this.activeDetections--;
      }
    }, this.config.detectionIntervalMs);

    this.detectionIntervals.set(key, intervalId);
  }

  private async detectPatternsForPair(symbol: string, interval: string): Promise<void> {
    try {
      // Skip pattern detection if WebSocket is not connected
      if (!binanceApi.isConnected()) {
        console.warn(`WebSocket not connected, skipping pattern detection for ${symbol}`);
        return;
      }

      // Get cached market data from WebSocket streams
      const priceData = this.getCachedPriceData(symbol);
      
      if (!priceData || priceData.length < 50) {
        console.warn(`Insufficient cached data for ${symbol} ${interval}`);
        return;
      }

      // SMC generator updates its own data automatically when running

      // Check for new patterns
      const patterns = await this.analyzeForPatterns(symbol, priceData, interval);
      
      if (patterns.length > 0) {
        console.log(`Found ${patterns.length} new patterns for ${symbol} ${interval}:`, patterns);
        
        // Notify about significant patterns
        for (const pattern of patterns) {
          if (pattern.confidence > 0.7) {
            toast.success(`New ${pattern.type} pattern detected`, {
              description: `${symbol} ${interval} - Confidence: ${(pattern.confidence * 100).toFixed(1)}%`
            });
          }
        }
      }
    } catch (error) {
      console.error(`Pattern detection error for ${symbol} ${interval}:`, error);
    }
  }

  private async analyzeForPatterns(symbol: string, priceData: any[], interval: string): Promise<any[]> {
    const patterns: any[] = [];
    
    try {
      // Analyze for Break of Structure (BOS)
      const bosPattern = this.detectBreakOfStructure(priceData);
      if (bosPattern) {
        patterns.push({
          type: 'BOS',
          symbol,
          interval,
          confidence: bosPattern.confidence,
          price: bosPattern.price,
          timestamp: Date.now()
        });
      }

      // Analyze for Change of Character (CHoCH)
      const chochPattern = this.detectChangeOfCharacter(priceData);
      if (chochPattern) {
        patterns.push({
          type: 'CHoCH',
          symbol,
          interval,
          confidence: chochPattern.confidence,
          price: chochPattern.price,
          timestamp: Date.now()
        });
      }

      // Analyze for Fair Value Gap (FVG)
      const fvgPattern = this.detectFairValueGap(priceData);
      if (fvgPattern) {
        patterns.push({
          type: 'FVG',
          symbol,
          interval,
          confidence: fvgPattern.confidence,
          price: fvgPattern.price,
          timestamp: Date.now()
        });
      }

      // Analyze for Order Block (OB)
      const obPattern = this.detectOrderBlock(priceData);
      if (obPattern) {
        patterns.push({
          type: 'OB',
          symbol,
          interval,
          confidence: obPattern.confidence,
          price: obPattern.price,
          timestamp: Date.now()
        });
      }

    } catch (error) {
      console.error('Error in pattern analysis:', error);
    }

    return patterns;
  }

  private detectBreakOfStructure(priceData: any[]): any | null {
    if (priceData.length < 20) return null;

    const recent = priceData.slice(-20);
    const highs = recent.map(d => d.high);
    const lows = recent.map(d => d.low);
    
    const recentHigh = Math.max(...highs.slice(-5));
    const previousHigh = Math.max(...highs.slice(-15, -5));
    
    if (recentHigh > previousHigh * 1.002) { // 0.2% threshold
      return {
        confidence: 0.75,
        price: recentHigh,
        direction: 'bullish'
      };
    }

    const recentLow = Math.min(...lows.slice(-5));
    const previousLow = Math.min(...lows.slice(-15, -5));
    
    if (recentLow < previousLow * 0.998) { // 0.2% threshold
      return {
        confidence: 0.75,
        price: recentLow,
        direction: 'bearish'
      };
    }

    return null;
  }

  private detectChangeOfCharacter(priceData: any[]): any | null {
    if (priceData.length < 30) return null;

    // Simplified CHoCH detection - look for trend reversal patterns
    const recent = priceData.slice(-30);
    const closes = recent.map(d => d.close);
    
    // Calculate simple moving averages
    const sma10 = closes.slice(-10).reduce((a, b) => a + b, 0) / 10;
    const sma20 = closes.slice(-20, -10).reduce((a, b) => a + b, 0) / 10;
    
    const currentPrice = closes[closes.length - 1];
    
    // Detect potential character change
    if (sma10 > sma20 * 1.005 && currentPrice > sma10) {
      return {
        confidence: 0.65,
        price: currentPrice,
        direction: 'bullish_reversal'
      };
    }
    
    if (sma10 < sma20 * 0.995 && currentPrice < sma10) {
      return {
        confidence: 0.65,
        price: currentPrice,
        direction: 'bearish_reversal'
      };
    }

    return null;
  }

  private detectFairValueGap(priceData: any[]): any | null {
    if (priceData.length < 10) return null;

    const recent = priceData.slice(-10);
    
    for (let i = 1; i < recent.length - 1; i++) {
      const prev = recent[i - 1];
      const curr = recent[i];
      const next = recent[i + 1];
      
      // Bullish FVG: gap between previous high and next low
      if (prev.high < next.low && curr.close > curr.open) {
        const gapSize = (next.low - prev.high) / prev.high;
        if (gapSize > 0.001) { // 0.1% minimum gap
          return {
            confidence: Math.min(0.8, gapSize * 100),
            price: (prev.high + next.low) / 2,
            direction: 'bullish'
          };
        }
      }
      
      // Bearish FVG: gap between previous low and next high
      if (prev.low > next.high && curr.close < curr.open) {
        const gapSize = (prev.low - next.high) / next.high;
        if (gapSize > 0.001) { // 0.1% minimum gap
          return {
            confidence: Math.min(0.8, gapSize * 100),
            price: (prev.low + next.high) / 2,
            direction: 'bearish'
          };
        }
      }
    }

    return null;
  }

  private detectOrderBlock(priceData: any[]): any | null {
    if (priceData.length < 15) return null;

    const recent = priceData.slice(-15);
    
    // Look for strong rejection candles (order blocks)
    for (let i = 5; i < recent.length - 2; i++) {
      const candle = recent[i];
      const bodySize = Math.abs(candle.close - candle.open);
      const totalSize = candle.high - candle.low;
      const wickRatio = (totalSize - bodySize) / totalSize;
      
      // Strong rejection with long wicks
      if (wickRatio > 0.6 && totalSize > bodySize * 3) {
        const volume = candle.volume || 0;
        const avgVolume = recent.slice(i - 5, i).reduce((sum, c) => sum + (c.volume || 0), 0) / 5;
        
        if (volume > avgVolume * 1.5) { // High volume confirmation
          return {
            confidence: 0.7,
            price: (candle.high + candle.low) / 2,
            direction: candle.close > candle.open ? 'bullish_ob' : 'bearish_ob'
          };
        }
      }
    }

    return null;
  }

  getStatus(): { isRunning: boolean; activeDetections: number; monitoredPairs: number } {
    return {
      isRunning: this.isRunning,
      activeDetections: this.activeDetections,
      monitoredPairs: this.config.symbols.length * this.config.intervals.length
    };
  }

  updateConfig(newConfig: Partial<PatternDetectionConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    if (this.isRunning) {
      // Restart with new config
      this.stop();
      setTimeout(() => this.start(), 1000);
    }
  }
}

// Export singleton instance
export const backgroundPatternDetection = new BackgroundPatternDetectionService();
export default backgroundPatternDetection;