import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { TimeFrame } from './uiStore';

export interface CandlestickData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalIndicator {
  id: string;
  name: string;
  type: 'sma' | 'ema' | 'rsi' | 'macd' | 'bollinger' | 'stochastic';
  params: Record<string, any>;
  visible: boolean;
  color: string;
  data: Array<{ timestamp: number; value: number | Record<string, number> }>;
}

export interface ChartAnnotation {
  id: string;
  type: 'line' | 'rectangle' | 'text' | 'arrow';
  symbol: string;
  timeFrame: TimeFrame;
  coordinates: {
    x1: number;
    y1: number;
    x2?: number;
    y2?: number;
  };
  style: {
    color: string;
    width?: number;
    dashArray?: string;
  };
  text?: string;
  timestamp: number;
}

export interface SMCPattern {
  id: string;
  type: 'bos' | 'choch' | 'fvg' | 'orderblock' | 'liquidity';
  symbol: string;
  timeFrame: TimeFrame;
  startTime: number;
  endTime?: number;
  price: number;
  confidence: number;
  description: string;
  active: boolean;
}

export interface ChartState {
  // Chart data
  candlestickData: Record<string, Record<TimeFrame, CandlestickData[]>>;
  
  // Technical analysis
  indicators: Record<string, TechnicalIndicator[]>;
  
  // Chart annotations and drawings
  annotations: Record<string, ChartAnnotation[]>;
  
  // SMC patterns
  smcPatterns: Record<string, SMCPattern[]>;
  
  // Chart settings per symbol
  chartSettings: Record<string, {
    timeFrame: TimeFrame;
    visibleRange: { start: number; end: number };
    priceRange: { min: number; max: number };
    autoScale: boolean;
  }>;
  
  // Loading and error states
  isLoading: Record<string, boolean>;
  errors: Record<string, string | null>;
  
  // Actions
  setCandlestickData: (symbol: string, timeFrame: TimeFrame, data: CandlestickData[]) => void;
  addCandlestickData: (symbol: string, timeFrame: TimeFrame, data: CandlestickData) => void;
  
  // Indicator actions
  addIndicator: (symbol: string, indicator: TechnicalIndicator) => void;
  removeIndicator: (symbol: string, indicatorId: string) => void;
  updateIndicator: (symbol: string, indicatorId: string, updates: Partial<TechnicalIndicator>) => void;
  toggleIndicatorVisibility: (symbol: string, indicatorId: string) => void;
  
  // Annotation actions
  addAnnotation: (symbol: string, annotation: ChartAnnotation) => void;
  removeAnnotation: (symbol: string, annotationId: string) => void;
  updateAnnotation: (symbol: string, annotationId: string, updates: Partial<ChartAnnotation>) => void;
  clearAnnotations: (symbol: string) => void;
  
  // SMC pattern actions
  addSMCPattern: (symbol: string, pattern: SMCPattern) => void;
  removeSMCPattern: (symbol: string, patternId: string) => void;
  updateSMCPattern: (symbol: string, patternId: string, updates: Partial<SMCPattern>) => void;
  toggleSMCPattern: (symbol: string, patternId: string) => void;
  
  // Chart settings actions
  updateChartSettings: (symbol: string, settings: Partial<ChartState['chartSettings'][string]>) => void;
  
  // Loading and error actions
  setLoading: (symbol: string, loading: boolean) => void;
  setError: (symbol: string, error: string | null) => void;
  
  // Data fetching
  fetchCandlestickData: (symbol: string, timeFrame: TimeFrame, limit?: number) => Promise<void>;
  
  // Cleanup
  clearSymbolData: (symbol: string) => void;
  reset: () => void;
}

const defaultChartSettings = {
  timeFrame: '1h' as TimeFrame,
  visibleRange: { start: 0, end: 100 },
  priceRange: { min: 0, max: 100 },
  autoScale: true,
};

export const useChartStore = create<ChartState>()(immer((set, get) => ({
  // Initial state
  candlestickData: {},
  indicators: {},
  annotations: {},
  smcPatterns: {},
  chartSettings: {},
  isLoading: {},
  errors: {},

  // Candlestick data actions
  setCandlestickData: (symbol, timeFrame, data) => set((state) => {
    if (!state.candlestickData[symbol]) {
      state.candlestickData[symbol] = {} as Record<TimeFrame, CandlestickData[]>;
    }
    state.candlestickData[symbol][timeFrame] = data;
  }),

  addCandlestickData: (symbol, timeFrame, data) => set((state) => {
    if (!state.candlestickData[symbol]) {
      state.candlestickData[symbol] = {} as Record<TimeFrame, CandlestickData[]>;
    }
    if (!state.candlestickData[symbol][timeFrame]) {
      state.candlestickData[symbol][timeFrame] = [];
    }
    
    const existingData = state.candlestickData[symbol][timeFrame];
    const existingIndex = existingData.findIndex(item => item.timestamp === data.timestamp);
    
    if (existingIndex >= 0) {
      // Update existing candle
      existingData[existingIndex] = data;
    } else {
      // Add new candle and sort by timestamp
      existingData.push(data);
      existingData.sort((a, b) => a.timestamp - b.timestamp);
    }
  }),

  // Indicator actions
  addIndicator: (symbol, indicator) => set((state) => {
    if (!state.indicators[symbol]) {
      state.indicators[symbol] = [];
    }
    state.indicators[symbol].push(indicator);
  }),

  removeIndicator: (symbol, indicatorId) => set((state) => {
    if (state.indicators[symbol]) {
      state.indicators[symbol] = state.indicators[symbol].filter(ind => ind.id !== indicatorId);
    }
  }),

  updateIndicator: (symbol, indicatorId, updates) => set((state) => {
    if (state.indicators[symbol]) {
      const indicator = state.indicators[symbol].find(ind => ind.id === indicatorId);
      if (indicator) {
        Object.assign(indicator, updates);
      }
    }
  }),

  toggleIndicatorVisibility: (symbol, indicatorId) => set((state) => {
    if (state.indicators[symbol]) {
      const indicator = state.indicators[symbol].find(ind => ind.id === indicatorId);
      if (indicator) {
        indicator.visible = !indicator.visible;
      }
    }
  }),

  // Annotation actions
  addAnnotation: (symbol, annotation) => set((state) => {
    if (!state.annotations[symbol]) {
      state.annotations[symbol] = [];
    }
    state.annotations[symbol].push(annotation);
  }),

  removeAnnotation: (symbol, annotationId) => set((state) => {
    if (state.annotations[symbol]) {
      state.annotations[symbol] = state.annotations[symbol].filter(ann => ann.id !== annotationId);
    }
  }),

  updateAnnotation: (symbol, annotationId, updates) => set((state) => {
    if (state.annotations[symbol]) {
      const annotation = state.annotations[symbol].find(ann => ann.id === annotationId);
      if (annotation) {
        Object.assign(annotation, updates);
      }
    }
  }),

  clearAnnotations: (symbol) => set((state) => {
    if (state.annotations[symbol]) {
      state.annotations[symbol] = [];
    }
  }),

  // SMC pattern actions
  addSMCPattern: (symbol, pattern) => set((state) => {
    if (!state.smcPatterns[symbol]) {
      state.smcPatterns[symbol] = [];
    }
    state.smcPatterns[symbol].push(pattern);
  }),

  removeSMCPattern: (symbol, patternId) => set((state) => {
    if (state.smcPatterns[symbol]) {
      state.smcPatterns[symbol] = state.smcPatterns[symbol].filter(pattern => pattern.id !== patternId);
    }
  }),

  updateSMCPattern: (symbol, patternId, updates) => set((state) => {
    if (state.smcPatterns[symbol]) {
      const pattern = state.smcPatterns[symbol].find(p => p.id === patternId);
      if (pattern) {
        Object.assign(pattern, updates);
      }
    }
  }),

  toggleSMCPattern: (symbol, patternId) => set((state) => {
    if (state.smcPatterns[symbol]) {
      const pattern = state.smcPatterns[symbol].find(p => p.id === patternId);
      if (pattern) {
        pattern.active = !pattern.active;
      }
    }
  }),

  // Chart settings actions
  updateChartSettings: (symbol, settings) => set((state) => {
    if (!state.chartSettings[symbol]) {
      state.chartSettings[symbol] = { ...defaultChartSettings };
    }
    Object.assign(state.chartSettings[symbol], settings);
  }),

  // Loading and error actions
  setLoading: (symbol, loading) => set((state) => {
    state.isLoading[symbol] = loading;
  }),

  setError: (symbol, error) => set((state) => {
    state.errors[symbol] = error;
  }),

  // Data fetching
  fetchCandlestickData: async (symbol, timeFrame, limit = 500) => {
    const { setLoading, setError, setCandlestickData } = get();
    
    try {
      setLoading(symbol, true);
      setError(symbol, null);
      
      // This would integrate with your existing MarketDataService
      // For now, we'll create a placeholder implementation
      const response = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${timeFrame}&limit=${limit}`
      );
      
      if (!response.ok) {
        throw new Error(`Failed to fetch candlestick data: ${response.statusText}`);
      }
      
      const rawData = await response.json();
      
      const candlestickData: CandlestickData[] = rawData.map((item: any[]) => ({
        timestamp: item[0],
        open: parseFloat(item[1]),
        high: parseFloat(item[2]),
        low: parseFloat(item[3]),
        close: parseFloat(item[4]),
        volume: parseFloat(item[5]),
      }));
      
      setCandlestickData(symbol, timeFrame, candlestickData);
    } catch (error: any) {
      console.error(`Error fetching candlestick data for ${symbol}:`, error);
      setError(symbol, error.message);
    } finally {
      setLoading(symbol, false);
    }
  },

  // Cleanup actions
  clearSymbolData: (symbol) => set((state) => {
    delete state.candlestickData[symbol];
    delete state.indicators[symbol];
    delete state.annotations[symbol];
    delete state.smcPatterns[symbol];
    delete state.chartSettings[symbol];
    delete state.isLoading[symbol];
    delete state.errors[symbol];
  }),

  reset: () => set((state) => {
    state.candlestickData = {};
    state.indicators = {};
    state.annotations = {};
    state.smcPatterns = {};
    state.chartSettings = {};
    state.isLoading = {};
    state.errors = {};
  }),
})));

// Helper hooks for specific chart concerns
export const useCandlestickData = (symbol: string, timeFrame: TimeFrame) => 
  useChartStore(state => state.candlestickData[symbol]?.[timeFrame] || []);

export const useIndicators = (symbol: string) => 
  useChartStore(state => state.indicators[symbol] || []);

export const useAnnotations = (symbol: string) => 
  useChartStore(state => state.annotations[symbol] || []);

export const useSMCPatterns = (symbol: string) => 
  useChartStore(state => state.smcPatterns[symbol] || []);

export const useChartSettings = (symbol: string) => 
  useChartStore(state => state.chartSettings[symbol] || defaultChartSettings);