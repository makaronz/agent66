"""
Binance Exchange Connector

Implements WebSocket and REST API connections to Binance exchange
for real-time market data ingestion.
"""

import asyncio
import json
import time
import hmac
import hashlib
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import websockets
import aiohttp
from pydantic import BaseModel, Field

from . import ExchangeConnector, WebSocketConnectionError, RESTAPIError, RateLimitError

logger = logging.getLogger(__name__)


class BinanceTrade(BaseModel):
    """Normalized trade data model."""
    exchange: str = "binance"
    symbol: str
    price: float
    quantity: float
    side: str  # BUY or SELL
    timestamp: float
    trade_id: int
    quote_quantity: float = Field(alias="quoteQty")


class BinanceOrderBook(BaseModel):
    """Normalized order book data model."""
    exchange: str = "binance"
    symbol: str
    timestamp: float
    bids: List[List[float]]  # [price, quantity]
    asks: List[List[float]]  # [price, quantity]
    last_update_id: int


class BinanceKline(BaseModel):
    """Normalized kline/candlestick data model."""
    exchange: str = "binance"
    symbol: str
    interval: str
    open_time: float
    close_time: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    quote_volume: float
    trade_count: int


class BinanceConnector(ExchangeConnector):
    """
    Binance exchange connector implementation.
    
    Supports WebSocket streams for real-time data and REST API for historical data.
    Implements rate limiting, authentication, and automatic reconnection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Binance connector.
        
        Args:
            config: Binance configuration dictionary
        """
        super().__init__(config)
        self.name = "binance"
        
        # Configuration
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.websocket_url = config.get('websocket_url', 'wss://stream.binance.com:9443/ws/')
        self.rest_url = config.get('rest_url', 'https://api.binance.com')
        self.rate_limit = config.get('rate_limit', 1200)  # requests per minute
        
        # Connection state
        self.websocket = None
        self.rest_session = None
        self.subscribed_streams = set()
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_reset_time = time.time() + 60
        
        # Data handlers
        self.data_handlers = {
            'trade': self._handle_trade_data,
            'orderbook': self._handle_orderbook_data,
            'kline': self._handle_kline_data,
        }
        
        logger.info(f"Initialized Binance connector for {self.rest_url}")
    
    async def connect_websocket(self) -> bool:
        """
        Establish WebSocket connection to Binance.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to Binance WebSocket: {self.websocket_url}")
            
            # Create WebSocket connection
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Test connection with ping
            pong_waiter = await self.websocket.ping()
            await pong_waiter
            
            logger.info("Binance WebSocket connection established successfully")
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance WebSocket: {e}")
            raise WebSocketConnectionError(f"WebSocket connection failed: {e}")
    
    async def disconnect_websocket(self) -> bool:
        """
        Disconnect WebSocket connection.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                self.subscribed_streams.clear()
                logger.info("Binance WebSocket disconnected successfully")
            self.connected = False
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect Binance WebSocket: {e}")
            return False
    
    async def subscribe_to_streams(self, streams: List[str]) -> bool:
        """
        Subscribe to Binance WebSocket streams.
        
        Args:
            streams: List of stream names (e.g., ['btcusdt@trade', 'btcusdt@depth'])
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            if not self.websocket:
                raise WebSocketConnectionError("WebSocket not connected")
            
            # Create subscription message
            subscription_message = {
                "method": "SUBSCRIBE",
                "params": streams,
                "id": int(time.time() * 1000)
            }
            
            # Send subscription request
            await self.websocket.send(json.dumps(subscription_message))
            
            # Wait for subscription confirmation
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get('result') is None:
                logger.error(f"Failed to subscribe to streams: {response_data}")
                return False
            
            # Add to subscribed streams
            self.subscribed_streams.update(streams)
            logger.info(f"Subscribed to Binance streams: {streams}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to Binance streams: {e}")
            return False
    
    async def fetch_rest_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Fetch data from Binance REST API.
        
        Args:
            endpoint: API endpoint path (e.g., '/api/v3/ticker/24hr')
            params: Query parameters
            
        Returns:
            Dict: API response data
        """
        try:
            # Check rate limit
            await self._check_rate_limit()
            
            # Initialize session if needed
            if not self.rest_session:
                self.rest_session = aiohttp.ClientSession()
            
            # Prepare URL and parameters
            url = f"{self.rest_url}{endpoint}"
            request_params = params or {}
            
            # Add authentication if required
            if self.api_key and self.api_secret:
                request_params = await self._add_authentication(request_params)
            
            # Make request
            async with self.rest_session.get(url, params=request_params) as response:
                if response.status == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status != 200:
                    raise RESTAPIError(f"API request failed: {response.status}")
                
                data = await response.json()
                
                # Update rate limit tracking
                self._update_rate_limit()
                
                return data
                
        except Exception as e:
            logger.error(f"REST API request failed: {e}")
            raise RESTAPIError(f"REST API request failed: {e}")
    
    async def normalize_data(self, raw_data: Dict, data_type: str) -> Dict:
        """
        Normalize Binance data to unified format.
        
        Args:
            raw_data: Raw data from Binance
            data_type: Type of data (trade, orderbook, kline)
            
        Returns:
            Dict: Normalized data in unified format
        """
        try:
            if data_type == 'trade':
                return await self._normalize_trade_data(raw_data)
            elif data_type == 'orderbook':
                return await self._normalize_orderbook_data(raw_data)
            elif data_type == 'kline':
                return await self._normalize_kline_data(raw_data)
            else:
                raise DataNormalizationError(f"Unknown data type: {data_type}")
                
        except Exception as e:
            logger.error(f"Data normalization failed: {e}")
            raise DataNormalizationError(f"Data normalization failed: {e}")
    
    async def get_health_status(self) -> Dict:
        """
        Get current health status of the Binance connector.
        
        Returns:
            Dict: Health status information
        """
        try:
            # Test REST API connection
            rest_health = await self._test_rest_connection()
            
            # Test WebSocket connection
            websocket_health = await self._test_websocket_connection()
            
            return {
                "exchange": "binance",
                "connected": self.connected,
                "websocket_connected": websocket_health,
                "rest_api_healthy": rest_health,
                "subscribed_streams": list(self.subscribed_streams),
                "rate_limit_remaining": self._get_remaining_rate_limit(),
                "last_request_time": self.last_request_time,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "exchange": "binance",
                "connected": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def listen_for_messages(self, callback):
        """
        Listen for WebSocket messages and process them.
        
        Args:
            callback: Function to call with normalized data
        """
        if not self.websocket:
            raise WebSocketConnectionError("WebSocket not connected")
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Handle different message types
                    if 'stream' in data:
                        # Stream data message
                        stream_name = data['stream']
                        stream_data = data['data']
                        
                        # Determine data type from stream name
                        if '@trade' in stream_name:
                            normalized_data = await self.normalize_data(stream_data, 'trade')
                        elif '@depth' in stream_name:
                            normalized_data = await self.normalize_data(stream_data, 'orderbook')
                        elif '@kline' in stream_name:
                            normalized_data = await self.normalize_data(stream_data, 'kline')
                        else:
                            logger.warning(f"Unknown stream type: {stream_name}")
                            continue
                        
                        # Call callback with normalized data
                        await callback(normalized_data)
                        
                    elif 'result' in data:
                        # Subscription confirmation
                        logger.info(f"Subscription confirmed: {data}")
                        
                    else:
                        logger.warning(f"Unknown message format: {data}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Binance WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"WebSocket listening error: {e}")
            self.connected = False
    
    async def _add_authentication(self, params: Dict) -> Dict:
        """Add authentication to API request parameters."""
        # Add timestamp
        params['timestamp'] = int(time.time() * 1000)
        
        # Create query string
        query_string = urlencode(sorted(params.items()))
        
        # Generate signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to parameters
        params['signature'] = signature
        
        return params
    
    async def _check_rate_limit(self):
        """Check if rate limit allows new request."""
        current_time = time.time()
        
        # Reset counter if minute has passed
        if current_time >= self.rate_limit_reset_time:
            self.request_count = 0
            self.rate_limit_reset_time = current_time + 60
        
        # Check if limit exceeded
        if self.request_count >= self.rate_limit:
            wait_time = self.rate_limit_reset_time - current_time
            if wait_time > 0:
                logger.warning(f"Rate limit exceeded, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.rate_limit_reset_time = time.time() + 60
    
    def _update_rate_limit(self):
        """Update rate limit tracking."""
        self.request_count += 1
        self.last_request_time = time.time()
    
    def _get_remaining_rate_limit(self) -> int:
        """Get remaining rate limit requests."""
        return max(0, self.rate_limit - self.request_count)
    
    async def _test_rest_connection(self) -> bool:
        """Test REST API connection."""
        try:
            await self.fetch_rest_data('/api/v3/ping')
            return True
        except Exception:
            return False
    
    async def _test_websocket_connection(self) -> bool:
        """Test WebSocket connection."""
        try:
            if self.websocket:
                pong_waiter = await self.websocket.ping()
                await pong_waiter
                return True
            return False
        except Exception:
            return False
    
    async def _normalize_trade_data(self, raw_data: Dict) -> Dict:
        """Normalize trade data to unified format."""
        try:
            trade = BinanceTrade(
                symbol=raw_data['s'],
                price=float(raw_data['p']),
                quantity=float(raw_data['q']),
                side=raw_data['S'],
                timestamp=float(raw_data['T']),
                trade_id=int(raw_data['t']),
                quoteQty=float(raw_data['Q'])
            )
            return trade.model_dump()
        except Exception as e:
            raise DataNormalizationError(f"Trade data normalization failed: {e}")
    
    async def _normalize_orderbook_data(self, raw_data: Dict) -> Dict:
        """Normalize order book data to unified format."""
        try:
            orderbook = BinanceOrderBook(
                symbol=raw_data['s'],
                timestamp=float(raw_data['E']),
                bids=[[float(price), float(qty)] for price, qty in raw_data['b']],
                asks=[[float(price), float(qty)] for price, qty in raw_data['a']],
                last_update_id=int(raw_data['u'])
            )
            return orderbook.model_dump()
        except Exception as e:
            raise DataNormalizationError(f"Order book data normalization failed: {e}")
    
    async def _normalize_kline_data(self, raw_data: Dict) -> Dict:
        """Normalize kline data to unified format."""
        try:
            kline = raw_data['k']
            normalized_kline = BinanceKline(
                symbol=kline['s'],
                interval=kline['i'],
                open_time=float(kline['t']),
                close_time=float(kline['T']),
                open_price=float(kline['o']),
                high_price=float(kline['h']),
                low_price=float(kline['l']),
                close_price=float(kline['c']),
                volume=float(kline['v']),
                quote_volume=float(kline['q']),
                trade_count=int(kline['n'])
            )
            return normalized_kline.model_dump()
        except Exception as e:
            raise DataNormalizationError(f"Kline data normalization failed: {e}")
    
    async def _handle_trade_data(self, data: Dict):
        """Handle incoming trade data."""
        logger.debug(f"Received trade data: {data['symbol']} @ {data['price']}")
    
    async def _handle_orderbook_data(self, data: Dict):
        """Handle incoming order book data."""
        logger.debug(f"Received order book data: {data['symbol']}")
    
    async def _handle_kline_data(self, data: Dict):
        """Handle incoming kline data."""
        logger.debug(f"Received kline data: {data['symbol']} {data['interval']}")
