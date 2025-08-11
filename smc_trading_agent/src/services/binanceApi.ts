import { toast } from 'sonner';

// Enhanced interfaces based on official Binance API documentation
interface BinanceTicker {
  symbol: string;
  price: string;
  priceChange: string;
  priceChangePercent: string;
  volume: string;
  quoteVolume: string;
  highPrice: string;
  lowPrice: string;
  openPrice: string;
  count: number;
  openTime: number;
  closeTime: number;
  firstId: number;
  lastId: number;
  weightedAvgPrice: string;
}

interface BinanceKline {
  openTime: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
  closeTime: number;
  quoteAssetVolume: string;
  numberOfTrades: number;
  takerBuyBaseAssetVolume: string;
  takerBuyQuoteAssetVolume: string;
}

interface BinanceExchangeInfo {
  timezone: string;
  serverTime: number;
  rateLimits: Array<{
    rateLimitType: string;
    interval: string;
    intervalNum: number;
    limit: number;
  }>;
  exchangeFilters: any[];
  symbols: Array<{
    symbol: string;
    status: string;
    baseAsset: string;
    quoteAsset: string;
    baseAssetPrecision: number;
    quotePrecision: number;
    quoteAssetPrecision: number;
    orderTypes: string[];
    icebergAllowed: boolean;
    ocoAllowed: boolean;
    isSpotTradingAllowed: boolean;
    isMarginTradingAllowed: boolean;
    filters: any[];
    permissions: string[];
  }>;
}

interface BinanceOrderBook {
  lastUpdateId: number;
  bids: [string, string][];
  asks: [string, string][];
}

interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
}

interface WebSocketConnection {
  ws: WebSocket;
  pingInterval?: NodeJS.Timeout;
  lastPong: number;
  reconnectAttempts: number;
  isManualClose: boolean;
  pongTimeout?: NodeJS.Timeout;
  connectionTimeout?: NodeJS.Timeout;
}

// Rate limiting configuration
interface RateLimitConfig {
  requests: number;
  interval: number; // in milliseconds
  lastReset: number;
}

// Binance API Error codes
interface BinanceError {
  code: number;
  msg: string;
}

// User Data Stream interfaces
interface BinanceAccountUpdate {
  e: 'outboundAccountPosition';
  E: number; // Event time
  u: number; // Time of last account update
  B: Array<{
    a: string; // Asset
    f: string; // Free
    l: string; // Locked
  }>;
}

interface BinanceBalanceUpdate {
  e: 'balanceUpdate';
  E: number; // Event time
  a: string; // Asset
  d: string; // Balance Delta
  T: number; // Clear Time
}

interface BinanceOrderUpdate {
  e: 'executionReport';
  E: number; // Event time
  s: string; // Symbol
  c: string; // Client order ID
  S: string; // Side
  o: string; // Order type
  f: string; // Time in force
  q: string; // Order quantity
  p: string; // Order price
  P: string; // Stop price
  F: string; // Iceberg quantity
  g: number; // OrderListId
  C: string; // Original client order ID
  x: string; // Current execution type
  X: string; // Current order status
  r: string; // Order reject reason
  i: number; // Order ID
  l: string; // Last executed quantity
  z: string; // Cumulative filled quantity
  L: string; // Last executed price
  n: string; // Commission amount
  N: string; // Commission asset
  T: number; // Transaction time
  t: number; // Trade ID
  I: number; // Ignore
  w: boolean; // Is the order on the book?
  m: boolean; // Is this trade the maker side?
  M: boolean; // Ignore
  O: number; // Order creation time
  Z: string; // Cumulative quote asset transacted quantity
  Y: string; // Last quote asset transacted quantity
  Q: string; // Quote Order Qty
}

type UserDataStreamEvent = BinanceAccountUpdate | BinanceBalanceUpdate | BinanceOrderUpdate;

interface ListenKeyResponse {
  listenKey: string;
}

class BinanceApiService {
  private baseUrl = 'https://api.binance.com/api/v3';
  private wsUrl = 'wss://stream.binance.com:9443/ws';
  private alternativeWsUrl = 'wss://stream.binance.com:443/ws'; // Alternative WebSocket endpoint
  private websockets: Map<string, WebSocketConnection> = new Map();
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval = 30000; // 30 seconds as per Binance docs
  private pongTimeout = 10000; // 10 seconds timeout for pong response
  private connectionTimeout = 24 * 60 * 60 * 1000; // 24 hours
  
  // Rate limiting
  private rateLimits: Map<string, RateLimitConfig> = new Map();
  private defaultRateLimit: RateLimitConfig = {
    requests: 1200, // 1200 requests per minute
    interval: 60000, // 1 minute
    lastReset: Date.now()
  };
  
  // Cache for exchange info
  private exchangeInfoCache: BinanceExchangeInfo | null = null;
  private exchangeInfoCacheTime = 0;
  private exchangeInfoCacheTTL = 24 * 60 * 60 * 1000; // 24 hours
  
  // User Data Stream
  private currentListenKey: string | null = null;
  private listenKeyRefreshInterval: NodeJS.Timeout | null = null;
  private userDataStreamConnection: WebSocketConnection | null = null;

  // Rate limiting helper
  private async checkRateLimit(endpoint: string = 'default'): Promise<void> {
    const now = Date.now();
    const rateLimit = this.rateLimits.get(endpoint) || this.defaultRateLimit;
    
    // Reset counter if interval has passed
    if (now - rateLimit.lastReset >= rateLimit.interval) {
      rateLimit.requests = 0;
      rateLimit.lastReset = now;
      this.rateLimits.set(endpoint, rateLimit);
    }
    
    // Check if we've exceeded the limit
    if (rateLimit.requests >= (this.rateLimits.get(endpoint)?.requests || this.defaultRateLimit.requests)) {
      const waitTime = rateLimit.interval - (now - rateLimit.lastReset);
      throw new Error(`Rate limit exceeded. Please wait ${Math.ceil(waitTime / 1000)} seconds.`);
    }
    
    rateLimit.requests++;
    this.rateLimits.set(endpoint, rateLimit);
  }
  
  // Enhanced error handling
  private handleBinanceError(error: any, context: string): never {
    console.error(`Binance API error in ${context}:`, error);
    
    if (error.response?.data) {
      const binanceError: BinanceError = error.response.data;
      switch (binanceError.code) {
        case -1003:
          toast.error('Too many requests. Please slow down.');
          break;
        case -1021:
          toast.error('Request timestamp outside of recvWindow.');
          break;
        case -2010:
          toast.error('Invalid symbol or trading pair.');
          break;
        case -1100:
          toast.error('Invalid parameter sent.');
          break;
        default:
          toast.error(`Binance API Error: ${binanceError.msg}`);
      }
      throw new Error(`Binance API Error ${binanceError.code}: ${binanceError.msg}`);
    }
    
    if (error.message?.includes('rate limit')) {
      toast.error('Rate limit exceeded. Please wait before making more requests.');
    } else {
      toast.error(`Failed to fetch data from Binance: ${error.message}`);
    }
    
    throw error;
  }
  
  // Get server time
  async getServerTime(): Promise<number> {
    try {
      await this.checkRateLimit('serverTime');
      const response = await fetch(`${this.baseUrl}/time`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data.serverTime;
    } catch (error) {
      this.handleBinanceError(error, 'getServerTime');
    }
  }
  
  // Get exchange information
  async getExchangeInfo(symbol?: string): Promise<BinanceExchangeInfo> {
    try {
      // Check cache first
      const now = Date.now();
      if (this.exchangeInfoCache && (now - this.exchangeInfoCacheTime) < this.exchangeInfoCacheTTL && !symbol) {
        return this.exchangeInfoCache;
      }
      
      await this.checkRateLimit('exchangeInfo');
      const url = symbol ? `${this.baseUrl}/exchangeInfo?symbol=${symbol}` : `${this.baseUrl}/exchangeInfo`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: BinanceExchangeInfo = await response.json();
      
      // Cache the result if no specific symbol was requested
      if (!symbol) {
        this.exchangeInfoCache = data;
        this.exchangeInfoCacheTime = now;
      }
      
      return data;
    } catch (error) {
      this.handleBinanceError(error, 'getExchangeInfo');
    }
  }
  
  // Get order book
  async getOrderBook(symbol: string, limit: number = 100): Promise<BinanceOrderBook> {
    try {
      await this.checkRateLimit('orderBook');
      const response = await fetch(`${this.baseUrl}/depth?symbol=${symbol}&limit=${limit}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      this.handleBinanceError(error, 'getOrderBook');
    }
  }
  
  // Get 24hr ticker statistics for all symbols
  async getAllTickers(): Promise<MarketData[]> {
    try {
      await this.checkRateLimit('getAllTickers');
      const response = await fetch(`${this.baseUrl}/ticker/24hr`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const tickers: BinanceTicker[] = await response.json();
      
      // Filter for major trading pairs and convert to our format
      const majorPairs = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'LINKUSDT'];
      
      return tickers
        .filter(ticker => majorPairs.includes(ticker.symbol))
        .map(ticker => ({
          symbol: ticker.symbol,
          price: parseFloat(ticker.price),
          change: parseFloat(ticker.priceChange),
          changePercent: parseFloat(ticker.priceChangePercent),
          volume: parseFloat(ticker.volume),
          high: parseFloat(ticker.highPrice),
          low: parseFloat(ticker.lowPrice),
          open: parseFloat(ticker.openPrice)
        }));
    } catch (error) {
      this.handleBinanceError(error, 'getAllTickers');
      return [];
    }
  }

  // Get 24hr ticker price change statistics
  async get24hrTicker(symbol?: string): Promise<BinanceTicker[]> {
    try {
      await this.checkRateLimit('get24hrTicker');
      const url = symbol 
        ? `${this.baseUrl}/ticker/24hr?symbol=${symbol}`
        : `${this.baseUrl}/ticker/24hr`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return Array.isArray(data) ? data : [data];
    } catch (error) {
      this.handleBinanceError(error, 'get24hrTicker');
    }
  }

  // Get single ticker data
  async getTicker(symbol: string): Promise<BinanceTicker> {
    try {
      const tickers = await this.get24hrTicker(symbol);
      if (tickers.length === 0) {
        throw new Error(`No ticker data found for ${symbol}`);
      }
      return tickers[0];
    } catch (error) {
      this.handleBinanceError(error, `getTicker-${symbol}`);
    }
  }

  // Get specific symbol ticker
  async getSymbolTicker(symbol: string): Promise<MarketData | null> {
    try {
      await this.checkRateLimit('getSymbolTicker');
      const response = await fetch(`${this.baseUrl}/ticker/24hr?symbol=${symbol}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const ticker: BinanceTicker = await response.json();
      
      return {
        symbol: ticker.symbol,
        price: parseFloat(ticker.price),
        change: parseFloat(ticker.priceChange),
        changePercent: parseFloat(ticker.priceChangePercent),
        volume: parseFloat(ticker.volume),
        high: parseFloat(ticker.highPrice),
        low: parseFloat(ticker.lowPrice),
        open: parseFloat(ticker.openPrice)
      };
    } catch (error) {
      this.handleBinanceError(error, `getSymbolTicker-${symbol}`);
      return null;
    }
  }

  // Get kline/candlestick data
  async getKlines(symbol: string, interval: string = '1h', limit: number = 100, startTime?: number, endTime?: number): Promise<BinanceKline[]> {
    try {
      await this.checkRateLimit('getKlines');
      
      let url = `${this.baseUrl}/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`;
      if (startTime) url += `&startTime=${startTime}`;
      if (endTime) url += `&endTime=${endTime}`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const klines: any[][] = await response.json();
      
      return klines.map(kline => ({
        openTime: kline[0],
        open: kline[1],
        high: kline[2],
        low: kline[3],
        close: kline[4],
        volume: kline[5],
        closeTime: kline[6],
        quoteAssetVolume: kline[7],
        numberOfTrades: kline[8],
        takerBuyBaseAssetVolume: kline[9],
        takerBuyQuoteAssetVolume: kline[10]
      }));
    } catch (error) {
      this.handleBinanceError(error, `getKlines-${symbol}`);
      return [];
    }
  }

  // Enhanced WebSocket connection management
  private setupWebSocketConnection(wsKey: string, ws: WebSocket, callback: (data: MarketData) => void, symbolOrSymbols: string | string[]): WebSocketConnection {
    const connection: WebSocketConnection = {
      ws,
      lastPong: Date.now(),
      reconnectAttempts: 0,
      isManualClose: false
    };

    // Setup ping/pong mechanism
    connection.pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        // Send ping frame (WebSocket standard)
        ws.send(JSON.stringify({ ping: Date.now() }));
        
        // Check if we received pong within timeout
        setTimeout(() => {
          const timeSinceLastPong = Date.now() - connection.lastPong;
          if (timeSinceLastPong > this.pongTimeout) {
            console.warn(`No pong received for ${wsKey}, closing connection`);
            ws.close(1006, 'Pong timeout');
          }
        }, this.pongTimeout);
      }
    }, this.pingInterval);

    // Setup 24-hour connection timeout
    setTimeout(() => {
      if (!connection.isManualClose && ws.readyState === WebSocket.OPEN) {
        console.log(`24-hour timeout reached for ${wsKey}, reconnecting`);
        ws.close(1000, '24-hour timeout');
      }
    }, this.connectionTimeout);

    ws.addEventListener('pong', () => {
      connection.lastPong = Date.now();
    });

    ws.onopen = () => {
      console.log(`Connected to Binance WebSocket: ${wsKey}`);
      connection.reconnectAttempts = 0;
      toast.success(`Connected to ${Array.isArray(symbolOrSymbols) ? 'multiple symbols' : symbolOrSymbols} stream`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle different message types
        if (data.e === '24hrTicker') {
          const marketData: MarketData = {
            symbol: data.s,
            price: parseFloat(data.c),
            change: parseFloat(data.P),
            changePercent: parseFloat(data.P),
            volume: parseFloat(data.v),
            high: parseFloat(data.h),
            low: parseFloat(data.l),
            open: parseFloat(data.o)
          };
          callback(marketData);
        }
      } catch (error) {
        console.error(`Error parsing WebSocket message for ${wsKey}:`, error);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error for ${wsKey}:`, error);
      // Check if this might be related to IP ban
      const errorMsg = `Connection error for ${Array.isArray(symbolOrSymbols) ? 'market data' : symbolOrSymbols}`;
      if (connection.reconnectAttempts === 0) {
        toast.error(`${errorMsg}. If this persists, your IP might be temporarily banned by Binance.`);
      } else {
        console.warn(`WebSocket connection failed (attempt ${connection.reconnectAttempts})`);
      }
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed for ${wsKey}:`, event.code, event.reason);
      
      // Clear ping interval
      if (connection.pingInterval) {
        clearInterval(connection.pingInterval);
      }
      
      // Attempt to reconnect if not manually closed
      if (!connection.isManualClose && event.code !== 1000) {
        this.attemptReconnect(wsKey, symbolOrSymbols, callback, connection);
      }
    };

    return connection;
  }

  // Subscribe to real-time price updates via WebSocket
  subscribeToTicker(symbol: string, callback: (data: MarketData) => void): () => void {
    const streamName = `${symbol.toLowerCase()}@ticker`;
    const wsKey = `ticker_${symbol}`;
    
    // Close existing connection if any
    if (this.websockets.has(wsKey)) {
      const existingConnection = this.websockets.get(wsKey)!;
      existingConnection.isManualClose = true;
      existingConnection.ws.close(1000, 'Replacing connection');
    }

    const ws = new WebSocket(`${this.wsUrl}/${streamName}`);
    const connection = this.setupWebSocketConnection(wsKey, ws, callback, symbol);
    this.websockets.set(wsKey, connection);

    // Return unsubscribe function
    return () => {
      connection.isManualClose = true;
      if (connection.pingInterval) {
        clearInterval(connection.pingInterval);
      }
      ws.close(1000, 'Manual close');
      this.websockets.delete(wsKey);
    };
  }

  // Subscribe to multiple tickers
  subscribeToMultipleTickers(symbols: string[], callback: (data: MarketData) => void): () => void {
    const streams = symbols.map(symbol => `${symbol.toLowerCase()}@ticker`).join('/');
    const wsKey = 'multi_ticker';
    
    // Close existing connection if any
    if (this.websockets.has(wsKey)) {
      const existingConnection = this.websockets.get(wsKey)!;
      existingConnection.isManualClose = true;
      existingConnection.ws.close(1000, 'Replacing connection');
    }

    const ws = new WebSocket(`${this.wsUrl}/${streams}`);
    const connection = this.setupWebSocketConnection(wsKey, ws, callback, symbols);
    this.websockets.set(wsKey, connection);

    return () => {
      connection.isManualClose = true;
      if (connection.pingInterval) {
        clearInterval(connection.pingInterval);
      }
      ws.close(1000, 'Manual close');
      this.websockets.delete(wsKey);
    };
  }

  private attemptReconnect(wsKey: string, symbolOrSymbols: string | string[], callback: (data: MarketData) => void, connection: WebSocketConnection) {
    if (connection.reconnectAttempts < this.maxReconnectAttempts) {
      connection.reconnectAttempts++;
      
      const delay = this.reconnectDelay * Math.pow(2, connection.reconnectAttempts - 1); // Exponential backoff
      
      setTimeout(() => {
        if (!connection.isManualClose) {
          console.log(`Attempting to reconnect ${wsKey} (attempt ${connection.reconnectAttempts})`);
          
          if (Array.isArray(symbolOrSymbols)) {
            this.subscribeToMultipleTickers(symbolOrSymbols, callback);
          } else {
            this.subscribeToTicker(symbolOrSymbols, callback);
          }
        }
      }, delay);
    } else {
      console.error(`Max reconnection attempts reached for ${wsKey}`);
      toast.error('Lost connection to market data. Please refresh the page.');
      this.websockets.delete(wsKey);
    }
  }

  // Subscribe to kline/candlestick streams
  subscribeToKlines(symbol: string, interval: string, callback: (data: BinanceKline) => void): () => void {
    const streamName = `${symbol.toLowerCase()}@kline_${interval}`;
    const wsKey = `kline_${symbol}_${interval}`;
    
    // Close existing connection if any
    if (this.websockets.has(wsKey)) {
      const existingConnection = this.websockets.get(wsKey)!;
      existingConnection.isManualClose = true;
      existingConnection.ws.close(1000, 'Replacing connection');
    }

    const ws = new WebSocket(`${this.wsUrl}/${streamName}`);
    const connection: WebSocketConnection = {
      ws,
      lastPong: Date.now(),
      reconnectAttempts: 0,
      isManualClose: false
    };

    // Setup ping/pong and event handlers
    connection.pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          // Send ping frame (WebSocket standard)
          ws.send(JSON.stringify({ ping: Date.now() }));
        }
      }, this.pingInterval);

    ws.addEventListener('pong', () => {
      connection.lastPong = Date.now();
    });

    ws.onopen = () => {
      console.log(`Connected to Binance kline stream: ${symbol} ${interval}`);
      connection.reconnectAttempts = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.e === 'kline') {
          const kline = data.k;
          const binanceKline: BinanceKline = {
            openTime: kline.t,
            open: kline.o,
            high: kline.h,
            low: kline.l,
            close: kline.c,
            volume: kline.v,
            closeTime: kline.T,
            quoteAssetVolume: kline.q,
            numberOfTrades: kline.n,
            takerBuyBaseAssetVolume: kline.V,
            takerBuyQuoteAssetVolume: kline.Q
          };
          callback(binanceKline);
        }
      } catch (error) {
        console.error(`Error parsing kline message for ${wsKey}:`, error);
      }
    };

    ws.onerror = (error) => {
      console.error(`Kline WebSocket error for ${wsKey}:`, error);
    };

    ws.onclose = (event) => {
      console.log(`Kline WebSocket closed for ${wsKey}:`, event.code, event.reason);
      if (connection.pingInterval) {
        clearInterval(connection.pingInterval);
      }
      
      if (!connection.isManualClose && event.code !== 1000) {
        // Implement reconnect for klines if needed
        console.log(`Kline connection lost for ${wsKey}, manual reconnection required`);
      }
    };

    this.websockets.set(wsKey, connection);

    return () => {
      connection.isManualClose = true;
      if (connection.pingInterval) {
        clearInterval(connection.pingInterval);
      }
      ws.close(1000, 'Manual close');
      this.websockets.delete(wsKey);
    };
  }

  // Close all WebSocket connections
  closeAllConnections() {
    this.websockets.forEach((connection, key) => {
      connection.isManualClose = true;
      if (connection.pingInterval) {
        clearInterval(connection.pingInterval);
      }
      connection.ws.close(1000, 'Service shutdown');
    });
    this.websockets.clear();
    
    // Clear user data stream connection
    this.userDataStreamConnection = null;
    
    // Clear listen key refresh interval
    this.clearListenKeyRefresh();
    
    // Reset listen key
    this.currentListenKey = null;
  }

  // Check if service is connected
  isConnected(): boolean {
    return Array.from(this.websockets.values()).some(
      connection => connection.ws.readyState === WebSocket.OPEN
    );
  }

  // Get connection status for all WebSockets
  getConnectionStatus(): Record<string, string> {
    const status: Record<string, string> = {};
    this.websockets.forEach((connection, key) => {
      switch (connection.ws.readyState) {
        case WebSocket.CONNECTING:
          status[key] = 'connecting';
          break;
        case WebSocket.OPEN:
          status[key] = 'connected';
          break;
        case WebSocket.CLOSING:
          status[key] = 'closing';
          break;
        case WebSocket.CLOSED:
          status[key] = 'closed';
          break;
        default:
          status[key] = 'unknown';
      }
    });
    return status;
  }

  // Get detailed connection info
  getDetailedConnectionStatus(): Record<string, any> {
    const status: Record<string, any> = {};
    this.websockets.forEach((connection, key) => {
      status[key] = {
        readyState: connection.ws.readyState,
        reconnectAttempts: connection.reconnectAttempts,
        lastPong: new Date(connection.lastPong).toISOString(),
        isManualClose: connection.isManualClose
      };
    });
    return status;
  }

  // User Data Stream methods (requires API key and secret)
  async createListenKey(apiKey: string): Promise<string> {
    try {
      await this.checkRateLimit('createListenKey');
      const response = await fetch(`${this.baseUrl}/userDataStream`, {
        method: 'POST',
        headers: {
          'X-MBX-APIKEY': apiKey
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: ListenKeyResponse = await response.json();
      this.currentListenKey = data.listenKey;
      
      // Setup automatic refresh every 30 minutes
      this.setupListenKeyRefresh(apiKey);
      
      return data.listenKey;
    } catch (error) {
      this.handleBinanceError(error, 'createListenKey');
    }
  }

  async keepAliveListenKey(apiKey: string, listenKey?: string): Promise<void> {
    try {
      await this.checkRateLimit('keepAliveListenKey');
      const keyToUse = listenKey || this.currentListenKey;
      
      if (!keyToUse) {
        throw new Error('No listen key available');
      }
      
      const response = await fetch(`${this.baseUrl}/userDataStream`, {
        method: 'PUT',
        headers: {
          'X-MBX-APIKEY': apiKey,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `listenKey=${keyToUse}`
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      console.log('Listen key refreshed successfully');
    } catch (error) {
      this.handleBinanceError(error, 'keepAliveListenKey');
    }
  }

  async deleteListenKey(apiKey: string, listenKey?: string): Promise<void> {
    try {
      await this.checkRateLimit('deleteListenKey');
      const keyToUse = listenKey || this.currentListenKey;
      
      if (!keyToUse) {
        throw new Error('No listen key available');
      }
      
      const response = await fetch(`${this.baseUrl}/userDataStream`, {
        method: 'DELETE',
        headers: {
          'X-MBX-APIKEY': apiKey,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `listenKey=${keyToUse}`
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      this.currentListenKey = null;
      this.clearListenKeyRefresh();
      
      console.log('Listen key deleted successfully');
    } catch (error) {
      this.handleBinanceError(error, 'deleteListenKey');
    }
  }

  private setupListenKeyRefresh(apiKey: string): void {
    this.clearListenKeyRefresh();
    
    // Refresh every 30 minutes (Binance recommends every 60 minutes, but we do it more frequently for safety)
    this.listenKeyRefreshInterval = setInterval(async () => {
      try {
        await this.keepAliveListenKey(apiKey);
      } catch (error) {
        console.error('Failed to refresh listen key:', error);
        toast.error('Failed to refresh user data stream. Please reconnect.');
      }
    }, 30 * 60 * 1000); // 30 minutes
  }

  private clearListenKeyRefresh(): void {
    if (this.listenKeyRefreshInterval) {
      clearInterval(this.listenKeyRefreshInterval);
      this.listenKeyRefreshInterval = null;
    }
  }

  // Subscribe to User Data Stream
  subscribeToUserDataStream(
    apiKey: string,
    callbacks: {
      onAccountUpdate?: (data: BinanceAccountUpdate) => void;
      onBalanceUpdate?: (data: BinanceBalanceUpdate) => void;
      onOrderUpdate?: (data: BinanceOrderUpdate) => void;
    }
  ): Promise<() => void> {
    return new Promise(async (resolve, reject) => {
      try {
        // Create or use existing listen key
        const listenKey = this.currentListenKey || await this.createListenKey(apiKey);
        
        const wsKey = 'user_data_stream';
        
        // Close existing connection if any
        if (this.userDataStreamConnection) {
          this.userDataStreamConnection.isManualClose = true;
          this.userDataStreamConnection.ws.close(1000, 'Replacing connection');
        }

        const ws = new WebSocket(`${this.wsUrl}/${listenKey}`);
        const connection: WebSocketConnection = {
          ws,
          lastPong: Date.now(),
          reconnectAttempts: 0,
          isManualClose: false
        };

        // Setup ping/pong mechanism (send ping frame)
      connection.pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          // Send ping frame (WebSocket standard)
          ws.send(JSON.stringify({ ping: Date.now() }));
        }
      }, this.pingInterval);

        ws.addEventListener('pong', () => {
          connection.lastPong = Date.now();
        });

        ws.onopen = () => {
          console.log('Connected to Binance User Data Stream');
          connection.reconnectAttempts = 0;
          toast.success('Connected to account updates');
        };

        ws.onmessage = (event) => {
          try {
            const data: UserDataStreamEvent = JSON.parse(event.data);
            
            switch (data.e) {
              case 'outboundAccountPosition':
                callbacks.onAccountUpdate?.(data);
                break;
              case 'balanceUpdate':
                callbacks.onBalanceUpdate?.(data);
                break;
              case 'executionReport':
                callbacks.onOrderUpdate?.(data);
                break;
              default:
                console.log('Unknown user data stream event:', data);
            }
          } catch (error) {
            console.error('Error parsing user data stream message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('User Data Stream WebSocket error:', error);
          toast.error('User data stream connection error');
          reject(error);
        };

        ws.onclose = (event) => {
          console.log('User Data Stream WebSocket closed:', event.code, event.reason);
          
          if (connection.pingInterval) {
            clearInterval(connection.pingInterval);
          }
          
          if (!connection.isManualClose && event.code !== 1000) {
            console.log('User data stream connection lost, manual reconnection required');
            toast.error('Lost connection to account updates');
          }
        };

        this.userDataStreamConnection = connection;
        this.websockets.set(wsKey, connection);

        // Return unsubscribe function
        const unsubscribe = () => {
          connection.isManualClose = true;
          if (connection.pingInterval) {
            clearInterval(connection.pingInterval);
          }
          ws.close(1000, 'Manual close');
          this.websockets.delete(wsKey);
          this.userDataStreamConnection = null;
          
          // Optionally delete the listen key
          this.deleteListenKey(apiKey).catch(console.error);
        };

        resolve(unsubscribe);
      } catch (error) {
        reject(error);
      }
    });
  }

  // Combined streams for better performance
  subscribeToCombinedStreams(
    streams: string[],
    callbacks: {
      onTicker?: (data: BinanceTicker) => void;
      onKline?: (data: any) => void;
      onDepth?: (data: any) => void;
    }
  ): Promise<() => void> {
    return new Promise((resolve, reject) => {
      if (streams.length === 0) {
        reject(new Error('No streams specified'));
        return;
      }

      const wsKey = `combined_${streams.join('_')}`;
      
      // Close existing connection if any
      if (this.websockets.has(wsKey)) {
        const existingConnection = this.websockets.get(wsKey)!;
        existingConnection.isManualClose = true;
        existingConnection.ws.close(1000, 'Replacing connection');
        this.websockets.delete(wsKey);
      }

      // Create combined stream URL
      const streamParams = streams.join('/');
      const wsUrl = `${this.wsUrl}/stream?streams=${streamParams}`;
      
      const ws = new WebSocket(wsUrl);
      
      // Create connection manually for combined streams
      const connection: WebSocketConnection = {
        ws,
        lastPong: Date.now(),
        reconnectAttempts: 0,
        isManualClose: false
      };
      
      // Setup ping/pong mechanism
      connection.pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          // Send ping frame (WebSocket standard)
          ws.send(JSON.stringify({ ping: Date.now() }));
        }
      }, this.pingInterval);
      
      // Setup connection timeout (24 hours)
      connection.connectionTimeout = setTimeout(() => {
        if (!connection.isManualClose) {
          console.log('Combined streams connection timeout (24h), reconnecting...');
          connection.ws.close(1000, '24h timeout');
        }
      }, 24 * 60 * 60 * 1000);
      
      this.websockets.set(wsKey, connection);

      ws.onopen = () => {
        console.log(`Connected to Binance combined streams: ${streams.join(', ')}`);
        connection.reconnectAttempts = 0;
        toast.success(`Connected to ${streams.length} data streams`);
      };

      // Set up message handling with pong support
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle pong responses
          if (message.pong) {
            connection.lastPong = Date.now();
            return;
          }
          
          // Handle stream data
          if (message.stream && message.data) {
            const streamName = message.stream;
            const data = message.data;
            
            // Route data based on stream type
            if (streamName.includes('@ticker')) {
              callbacks.onTicker?.(data);
            } else if (streamName.includes('@kline')) {
              callbacks.onKline?.(data);
            } else if (streamName.includes('@depth')) {
              callbacks.onDepth?.(data);
            }
          }
        } catch (error) {
          console.error('Error parsing combined stream message:', error);
        }
      };

      ws.onerror = (error) => {
         console.error('Combined streams WebSocket error:', error);
         toast.error('Combined streams connection error');
       };
       
       ws.onclose = (event) => {
         console.log('Combined streams WebSocket closed:', event.code, event.reason);
         
         if (connection.pingInterval) {
           clearInterval(connection.pingInterval);
         }
         if (connection.connectionTimeout) {
           clearTimeout(connection.connectionTimeout);
         }
         
         if (!connection.isManualClose && event.code !== 1000) {
            // Attempt reconnection for combined streams
            if (connection.reconnectAttempts < 5) {
              connection.reconnectAttempts++;
              const delay = Math.min(1000 * Math.pow(2, connection.reconnectAttempts), 30000);
              
              console.log(`Attempting to reconnect combined streams (attempt ${connection.reconnectAttempts}/5) in ${delay}ms...`);
              
              setTimeout(() => {
                this.subscribeToCombinedStreams(streams, callbacks)
                  .then(resolve)
                  .catch(reject);
              }, delay);
            } else {
              console.error('Max reconnection attempts reached for combined streams');
              toast.error('Failed to reconnect to combined streams');
              this.websockets.delete(wsKey);
            }
          }
       };
       


      // Return unsubscribe function
      const unsubscribe = () => {
        connection.isManualClose = true;
        if (connection.pingInterval) {
          clearInterval(connection.pingInterval);
        }
        if (connection.pongTimeout) {
          clearTimeout(connection.pongTimeout);
        }
        if (connection.connectionTimeout) {
          clearTimeout(connection.connectionTimeout);
        }
        ws.close(1000, 'Manual close');
        this.websockets.delete(wsKey);
      };

      resolve(unsubscribe);
    });
  }

  // Helper method to create stream names
  static createStreamName(symbol: string, streamType: 'ticker' | 'kline' | 'depth', interval?: string): string {
    const lowerSymbol = symbol.toLowerCase();
    
    switch (streamType) {
      case 'ticker':
        return `${lowerSymbol}@ticker`;
      case 'kline':
        if (!interval) throw new Error('Interval required for kline stream');
        return `${lowerSymbol}@kline_${interval}`;
      case 'depth':
        return `${lowerSymbol}@depth`;
      default:
        throw new Error(`Unknown stream type: ${streamType}`);
    }
  }

  // Convenience method for subscribing to multiple tickers efficiently
  subscribeToMultipleTickersOptimized(
    symbols: string[],
    callback: (data: BinanceTicker) => void
  ): Promise<() => void> {
    const streams = symbols.map(symbol => 
      BinanceApiService.createStreamName(symbol, 'ticker')
    );
    
    return this.subscribeToCombinedStreams(streams, {
      onTicker: callback
    });
  }

  // Convenience method for subscribing to multiple klines efficiently
  subscribeToMultipleKlinesOptimized(
    symbolIntervals: Array<{ symbol: string; interval: string }>,
    callback: (data: any) => void
  ): Promise<() => void> {
    const streams = symbolIntervals.map(({ symbol, interval }) => 
      BinanceApiService.createStreamName(symbol, 'kline', interval)
    );
    
    return this.subscribeToCombinedStreams(streams, {
      onKline: callback
    });
  }
}

// Export singleton instance
export const binanceApi = new BinanceApiService();
export type { 
  MarketData, 
  BinanceKline, 
  BinanceTicker, 
  BinanceExchangeInfo, 
  BinanceOrderBook,
  BinanceError,
  BinanceAccountUpdate,
  BinanceBalanceUpdate,
  BinanceOrderUpdate,
  UserDataStreamEvent,
  ListenKeyResponse
};