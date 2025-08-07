"""
ByBit Exchange Connector

Implements WebSocket and REST API connections to ByBit exchange
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

from . import ExchangeConnector, ExchangeConnectorError, WebSocketConnectionError, RESTAPIError, RateLimitError

logger = logging.getLogger(__name__)


class ByBitTrade(BaseModel):
    """Normalized trade data model."""
    exchange: str = "bybit"
    symbol: str
    price: float
    quantity: float
    side: str  # Buy or Sell
    timestamp: float
    trade_id: str
    quote_quantity: float


class ByBitOrderBook(BaseModel):
    """Normalized order book data model."""
    exchange: str = "bybit"
    symbol: str
    timestamp: float
    bids: List[List[float]]  # [price, quantity]
    asks: List[List[float]]  # [price, quantity]
    sequence_number: int


class ByBitKline(BaseModel):
    """Normalized kline/candlestick data model."""
    exchange: str = "bybit"
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


class ByBitConnector(ExchangeConnector):
    """
    ByBit exchange connector implementation.
    
    Supports WebSocket streams for real-time data and REST API for historical data.
    Implements rate limiting, authentication, and automatic reconnection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ByBit connector.
        
        Args:
            config: ByBit configuration dictionary
        """
        super().__init__(config)
        self.name = "bybit"
        
        # Configuration
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.websocket_url = config.get('websocket_url', 'wss://stream.bybit.com/v5/public/spot')
        self.rest_url = config.get('rest_url', 'https://api.bybit.com')
        self.rate_limit = config.get('rate_limit', 120)  # requests per second
        
        # Connection state
        self.websocket = None
        self.rest_session = None
        self.subscribed_streams = set()
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_reset_time = time.time() + 1  # 1 second window
        
        # Data handlers
        self.data_handlers = {
            'trade': self._handle_trade_data,
            'orderbook': self._handle_orderbook_data,
            'kline': self._handle_kline_data,
        }
        
        logger.info(f"Initialized ByBit connector for {self.rest_url}")
    
    async def connect_websocket(self) -> bool:
        """
        Establish WebSocket connection to ByBit.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to ByBit WebSocket: {self.websocket_url}")
            
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
            
            logger.info("ByBit WebSocket connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ByBit WebSocket: {e}")
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
                logger.info("ByBit WebSocket disconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect ByBit WebSocket: {e}")
            return False
    
    async def subscribe_to_streams(self, streams: List[str]) -> bool:
        """
        Subscribe to ByBit WebSocket streams.
        
        Args:
            streams: List of stream names (e.g., ['orderbook.1.BTCUSDT', 'publicTrade.BTCUSDT'])
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            if not self.websocket:
                raise WebSocketConnectionError("WebSocket not connected")
            
            # Create subscription message for ByBit V5 API
            subscription_message = {
                "op": "subscribe",
                "args": streams
            }
            
            # Send subscription request
            await self.websocket.send(json.dumps(subscription_message))
            
            # Wait for subscription confirmation
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get('success') != True:
                logger.error(f"Failed to subscribe to streams: {response_data}")
                return False
            
            # Add to subscribed streams
            self.subscribed_streams.update(streams)
            logger.info(f"Subscribed to ByBit streams: {streams}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to ByBit streams: {e}")
            return False
    
    async def fetch_rest_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Fetch data from ByBit REST API.
        
        Args:
            endpoint: API endpoint path (e.g., '/v5/market/tickers')
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
        Normalize ByBit data to unified format.
        
        Args:
            raw_data: Raw data from ByBit
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
        Get current health status of the ByBit connector.
        
        Returns:
            Dict: Health status information
        """
        try:
            # Test REST API connection
            rest_health = await self._test_rest_connection()
            
            # Test WebSocket connection
            websocket_health = await self._test_websocket_connection()
            
            return {
                "exchange": "bybit",
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
                "exchange": "bybit",
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
                    if 'topic' in data:
                        # Stream data message
                        topic = data['topic']
                        topic_data = data.get('data', {})
                        
                        # Determine data type from topic
                        if 'publicTrade' in topic:
                            normalized_data = await self.normalize_data(topic_data, 'trade')
                        elif 'orderbook' in topic:
                            normalized_data = await self.normalize_data(topic_data, 'orderbook')
                        elif 'kline' in topic:
                            normalized_data = await self.normalize_data(topic_data, 'kline')
                        else:
                            logger.warning(f"Unknown topic type: {topic}")
                            continue
                        
                        # Call callback with normalized data
                        await callback(normalized_data)
                        
                    elif 'success' in data:
                        # Subscription confirmation
                        logger.info(f"Subscription confirmed: {data}")
                        
                    else:
                        logger.warning(f"Unknown message format: {data}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("ByBit WebSocket connection closed")
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
        params['sign'] = signature
        
        return params
    
    async def _check_rate_limit(self):
        """Check if rate limit allows new request."""
        current_time = time.time()
        
        # Reset counter if second has passed
        if current_time >= self.rate_limit_reset_time:
            self.request_count = 0
            self.rate_limit_reset_time = current_time + 1
        
        # Check if limit exceeded
        if self.request_count >= self.rate_limit:
            wait_time = self.rate_limit_reset_time - current_time
            if wait_time > 0:
                logger.warning(f"Rate limit exceeded, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.rate_limit_reset_time = time.time() + 1
    
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
            await self.fetch_rest_data('/v5/market/time')
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
            # ByBit trade data structure
            trade = ByBitTrade(
                symbol=raw_data['s'],
                price=float(raw_data['p']),
                quantity=float(raw_data['v']),
                side=raw_data['S'],
                timestamp=float(raw_data['T']),
                trade_id=raw_data['i'],
                quote_quantity=float(raw_data['q'])
            )
            return trade.model_dump()
        except Exception as e:
            raise DataNormalizationError(f"Trade data normalization failed: {e}")
    
    async def _normalize_orderbook_data(self, raw_data: Dict) -> Dict:
        """Normalize order book data to unified format."""
        try:
            orderbook = ByBitOrderBook(
                symbol=raw_data['s'],
                timestamp=float(raw_data['ts']),
                bids=[[float(price), float(qty)] for price, qty in raw_data['b']],
                asks=[[float(price), float(qty)] for price, qty in raw_data['a']],
                sequence_number=int(raw_data['u'])
            )
            return orderbook.model_dump()
        except Exception as e:
            raise DataNormalizationError(f"Order book data normalization failed: {e}")
    
    async def _normalize_kline_data(self, raw_data: Dict) -> Dict:
        """Normalize kline data to unified format."""
        try:
            kline = raw_data
            normalized_kline = ByBitKline(
                symbol=kline['symbol'],
                interval=kline['interval'],
                open_time=float(kline['start']),
                close_time=float(kline['end']),
                open_price=float(kline['open']),
                high_price=float(kline['high']),
                low_price=float(kline['low']),
                close_price=float(kline['close']),
                volume=float(kline['volume']),
                quote_volume=float(kline['turnover']),
                trade_count=int(kline['tradeCount'])
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
