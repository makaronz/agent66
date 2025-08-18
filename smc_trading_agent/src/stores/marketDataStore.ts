import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { marketDataService } from '../services/MarketDataService';

export interface TickerData {
  symbol: string;
  price: string;
  priceChange: string;
  priceChangePercent: string;
  volume: string;
  high: string;
  low: string;
  open: string;
  timestamp: number;
}

export interface OrderBookData {
  symbol: string;
  bids: [string, string][];
  asks: [string, string][];
  timestamp: number;
}

export interface ExchangeInfo {
  symbols: Array<{
    symbol: string;
    status: string;
    baseAsset: string;
    quoteAsset: string;
    filters: any[];
  }>;
  serverTime: number;
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  reconnectAttempts: number;
  lastError: string | null;
}

export interface MarketDataState {
  // Market data
  tickers: Record<string, TickerData>;
  orderBooks: Record<string, OrderBookData>;
  exchangeInfo: ExchangeInfo | null;
  
  // WebSocket state
  wsState: WebSocketState;
  
  // Connection properties for compatibility
  isConnected: boolean;
  connectionStatus: string;
  connect: () => void;
  
  // UI state
  selectedSymbols: string[];
  isLoading: boolean;
  error: string | null;
  lastUpdate: number;
  
  // Actions
  setTicker: (symbol: string, data: TickerData) => void;
  setOrderBook: (symbol: string, data: OrderBookData) => void;
  setExchangeInfo: (info: ExchangeInfo) => void;
  setWebSocketState: (state: Partial<WebSocketState>) => void;
  setSelectedSymbols: (symbols: string[]) => void;
  addSelectedSymbol: (symbol: string) => void;
  removeSelectedSymbol: (symbol: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateLastUpdate: () => void;
  
  // Market data methods
  fetchTicker: (symbol: string) => Promise<void>;
  fetchOrderBook: (symbol: string) => Promise<void>;
  fetchExchangeInfo: () => Promise<void>;
  
  // WebSocket methods
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  subscribeToTicker: (symbol: string) => void;
  unsubscribeFromTicker: (symbol: string) => void;
  
  // Bulk operations
  fetchMultipleTickers: (symbols: string[]) => Promise<void>;
  subscribeToMultipleTickers: (symbols: string[]) => void;
  
  // Cleanup
  reset: () => void;
}

const initialWebSocketState: WebSocketState = {
  isConnected: false,
  isConnecting: false,
  reconnectAttempts: 0,
  lastError: null,
};

const DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'];

export const useMarketDataStore = create<MarketDataState>()(immer((set, get) => ({
  // Initial state
  tickers: {},
  orderBooks: {},
  exchangeInfo: null,
  wsState: initialWebSocketState,
  selectedSymbols: DEFAULT_SYMBOLS,
  isLoading: false,
  error: null,
  lastUpdate: 0,
  
  // Connection properties for compatibility
  isConnected: false,
  connectionStatus: 'disconnected',
  connect: () => {
    set((state) => {
      state.isConnected = true;
      state.connectionStatus = 'connected';
      state.wsState.isConnected = true;
    });
  },

  // State setters
  setTicker: (symbol, data) => set((state) => {
    state.tickers[symbol] = data;
    state.lastUpdate = Date.now();
  }),
  
  setOrderBook: (symbol, data) => set((state) => {
    state.orderBooks[symbol] = data;
    state.lastUpdate = Date.now();
  }),
  
  setExchangeInfo: (info) => set((state) => {
    state.exchangeInfo = info;
  }),
  
  setWebSocketState: (wsState) => set((state) => {
    Object.assign(state.wsState, wsState);
  }),
  
  setSelectedSymbols: (symbols) => set((state) => {
    state.selectedSymbols = symbols;
  }),
  
  addSelectedSymbol: (symbol) => set((state) => {
    if (!state.selectedSymbols.includes(symbol)) {
      state.selectedSymbols.push(symbol);
    }
  }),
  
  removeSelectedSymbol: (symbol) => set((state) => {
    state.selectedSymbols = state.selectedSymbols.filter(s => s !== symbol);
  }),
  
  setLoading: (loading) => set((state) => {
    state.isLoading = loading;
  }),
  
  setError: (error) => set((state) => {
    state.error = error;
  }),
  
  updateLastUpdate: () => set((state) => {
    state.lastUpdate = Date.now();
  }),

  // Market data methods
  fetchTicker: async (symbol) => {
    try {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      // Use fetchMarketData instead of getTicker
      await marketDataService.fetchMarketData([symbol]);
      const data = marketDataService.getSymbolData(symbol);
      
      if (data) {
         // Convert MarketData to TickerData format
         const tickerData: TickerData = {
           symbol: data.symbol,
           price: data.price.toString(),
           priceChange: data.change.toString(),
           priceChangePercent: data.changePercent.toString(),
           volume: data.volume.toString(),
           high: data.high.toString(),
           low: data.low.toString(),
           open: data.open.toString(),
           timestamp: Date.now()
         };
         get().setTicker(symbol, tickerData);
       } else {
         throw new Error('No data received for symbol');
       }
    } catch (error: any) {
      console.error(`Error fetching ticker for ${symbol}:`, error);
      set((state) => {
        state.error = error.message;
      });
    } finally {
      set((state) => {
        state.isLoading = false;
      });
    }
  },
  
  fetchOrderBook: async (symbol) => {
    try {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      // TODO: Order book functionality not yet implemented in MarketDataService
      console.log('Order book functionality not yet implemented for:', symbol);
      
      set((state) => {
        state.isLoading = false;
      });
    } catch (error: any) {
      console.error(`Error fetching order book for ${symbol}:`, error);
      set((state) => {
        state.error = error.message;
        state.isLoading = false;
      });
    }
  },
  
  fetchExchangeInfo: async () => {
    try {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      // TODO: Exchange info functionality not yet implemented in MarketDataService
      console.log('Exchange info functionality not yet implemented');
      
      set((state) => {
        state.isLoading = false;
      });
    } catch (error: any) {
      console.error('Error fetching exchange info:', error);
      set((state) => {
        state.error = error.message;
        state.isLoading = false;
      });
    }
  },

  // WebSocket methods - temporarily disabled until WebSocket service is implemented
  connectWebSocket: () => {
    console.log('WebSocket connection not implemented yet');
    set((state) => {
      state.wsState.isConnected = false;
      state.wsState.isConnecting = false;
    });
  },
  
  disconnectWebSocket: () => {
    console.log('WebSocket disconnection not implemented yet');
    set((state) => {
      state.wsState = { ...initialWebSocketState };
    });
  },
  
  subscribeToTicker: (symbol) => {
    console.log(`Ticker subscription for ${symbol} not implemented yet`);
  },
  
  unsubscribeFromTicker: (symbol) => {
    console.log(`Ticker unsubscription for ${symbol} not implemented yet`);
  },

  // Bulk operations
  fetchMultipleTickers: async (symbols) => {
    try {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });
      
      const promises = symbols.map(symbol => get().fetchTicker(symbol));
      await Promise.allSettled(promises);
    } finally {
      set((state) => {
        state.isLoading = false;
      });
    }
  },
  
  subscribeToMultipleTickers: (symbols) => {
    console.log(`Multiple ticker subscription for ${symbols.join(', ')} not implemented yet`);
  },

  // Cleanup
  reset: () => set((state) => {
    state.tickers = {};
    state.orderBooks = {};
    state.exchangeInfo = null;
    state.wsState = { ...initialWebSocketState };
    state.selectedSymbols = DEFAULT_SYMBOLS;
    state.isLoading = false;
    state.error = null;
    state.lastUpdate = 0;
  }),
})));

// Initialize market data on store creation
const initializeMarketData = async () => {
  const store = useMarketDataStore.getState();
  
  try {
    // Fetch exchange info first
    await store.fetchExchangeInfo();
    
    // Fetch initial ticker data for default symbols
    await store.fetchMultipleTickers(store.selectedSymbols);
    
    // Connect WebSocket for real-time updates
    store.connectWebSocket();
    
    // Subscribe to default symbols
    store.subscribeToMultipleTickers(store.selectedSymbols);
  } catch (error) {
    console.error('Failed to initialize market data:', error);
  }
};

// Auto-initialize when store is created
if (typeof window !== 'undefined') {
  initializeMarketData();
}