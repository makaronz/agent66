"""
OANDA Exchange Connector

Implements WebSocket and REST API connections to OANDA exchange
for real-time forex market data ingestion.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import websockets
import aiohttp
from pydantic import BaseModel, Field

from . import ExchangeConnector, ExchangeConnectorError, WebSocketConnectionError, RESTAPIError, RateLimitError

logger = logging.getLogger(__name__)


class OANDATrade(BaseModel):
    """Normalized trade data model."""
    exchange: str = "oanda"
    symbol: str
    price: float
    quantity: float
    side: str  # buy or sell
    timestamp: float
    trade_id: str
    quote_quantity: float


class OANDAOrderBook(BaseModel):
    """Normalized order book data model."""
    exchange: str = "oanda"
    symbol: str
    timestamp: float
    bids: List[List[float]]  # [price, quantity]
    asks: List[List[float]]  # [price, quantity]
    sequence_number: int


class OANDAKline(BaseModel):
    """Normalized kline/candlestick data model."""
    exchange: str = "oanda"
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


class OANDAConnector(ExchangeConnector):
    """
    OANDA exchange connector implementation.
    
    Supports WebSocket streams for real-time data and REST API for historical data.
    Implements rate limiting, authentication, and automatic reconnection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OANDA connector.
        
        Args:
            config: OANDA configuration dictionary
        """
        super().__init__(config)
        self.name = "oanda"
        
        # Configuration
        self.api_key = config.get('api_key', '')
        self.account_id = config.get('account_id', '')
        self.websocket_url = config.get('websocket_url', 'wss://stream-fxtrade.oanda.com/v3/accounts/{account_id}/pricing/stream')
        self.rest_url = config.get('rest_url', 'https://api-fxtrade.oanda.com/v3')
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
        
        logger.info(f"Initialized OANDA connector for {self.rest_url}")
    
    async def connect_websocket(self) -> bool:
        """
        Establish WebSocket connection to OANDA.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Format WebSocket URL with account ID
            websocket_url = self.websocket_url.format(account_id=self.account_id)
            logger.info(f"Connecting to OANDA WebSocket: {websocket_url}")
            
            # Create WebSocket connection with authentication headers
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            self.websocket = await websockets.connect(
                websocket_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Test connection with ping
            pong_waiter = await self.websocket.ping()
            await pong_waiter
            
            logger.info("OANDA WebSocket connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to OANDA WebSocket: {e}")
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
                logger.info("OANDA WebSocket disconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect OANDA WebSocket: {e}")
            return False
    
    async def subscribe_to_streams(self, streams: List[str]) -> bool:
        """
        Subscribe to OANDA WebSocket streams.
        
        Args:
            streams: List of instrument names (e.g., ['EUR_USD', 'GBP_USD'])
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            if not self.websocket:
                raise WebSocketConnectionError("WebSocket not connected")
            
            # OANDA uses a simple subscription format
            for instrument in streams:
                subscription_message = {
                    "instruments": [instrument]
                }
                
                # Send subscription request
                await self.websocket.send(json.dumps(subscription_message))
                
                # Wait for subscription confirmation
                response = await self.websocket.recv()
                response_data = json.loads(response)
                
                if 'error' in response_data:
                    logger.error(f"Failed to subscribe to {instrument}: {response_data}")
                    return False
            
            # Add to subscribed streams
            self.subscribed_streams.update(streams)
            logger.info(f"Subscribed to OANDA streams: {streams}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to OANDA streams: {e}")
            return False
    
    async def fetch_rest_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Fetch data from OANDA REST API.
        
        Args:
            endpoint: API endpoint path (e.g., '/accounts/{account_id}/instruments')
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
            
            # Add authentication headers
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Make request
            async with self.rest_session.get(url, params=request_params, headers=headers) as response:
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
        Normalize OANDA data to unified format.
        
        Args:
            raw_data: Raw data from OANDA
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
        Get current health status of the OANDA connector.
        
        Returns:
            Dict: Health status information
        """
        try:
            # Test REST API connection
            rest_health = await self._test_rest_connection()
            
            # Test WebSocket connection
            websocket_health = await self._test_websocket_connection()
            
            return {
                "exchange": "oanda",
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
                "exchange": "oanda",
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
                    if 'type' in data:
                        message_type = data['type']
                        
                        if message_type == 'PRICE':
                            # Price update message
                            normalized_data = await self.normalize_data(data, 'orderbook')
                            await callback(normalized_data)
                            
                        elif message_type == 'HEARTBEAT':
                            # Heartbeat message - just log
                            logger.debug("Received OANDA heartbeat")
                            
                        else:
                            logger.warning(f"Unknown message type: {message_type}")
                            
                    else:
                        logger.warning(f"Unknown message format: {data}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("OANDA WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"WebSocket listening error: {e}")
            self.connected = False
    
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
            endpoint = f"/accounts/{self.account_id}"
            await self.fetch_rest_data(endpoint)
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
            # OANDA trade data structure (if available)
            trade = OANDATrade(
                symbol=raw_data.get('instrument', ''),
                price=float(raw_data.get('price', 0)),
                quantity=float(raw_data.get('units', 0)),
                side=raw_data.get('side', 'buy'),
                timestamp=float(raw_data.get('time', time.time())),
                trade_id=raw_data.get('id', ''),
                quote_quantity=float(raw_data.get('quote_quantity', 0))
            )
            return trade.model_dump()
        except Exception as e:
            raise DataNormalizationError(f"Trade data normalization failed: {e}")
    
    async def _normalize_orderbook_data(self, raw_data: Dict) -> Dict:
        """Normalize order book data to unified format."""
        try:
            # OANDA price data structure
            orderbook = OANDAOrderBook(
                symbol=raw_data['instrument'],
                timestamp=float(raw_data['time']),
                bids=[[float(raw_data['bids'][0]['price']), float(raw_data['bids'][0]['liquidity'])]],
                asks=[[float(raw_data['asks'][0]['price']), float(raw_data['asks'][0]['liquidity'])]],
                sequence_number=int(raw_data.get('sequence', 0))
            )
            return orderbook.model_dump()
        except Exception as e:
            raise DataNormalizationError(f"Order book data normalization failed: {e}")
    
    async def _normalize_kline_data(self, raw_data: Dict) -> Dict:
        """Normalize kline data to unified format."""
        try:
            # OANDA candle data structure
            candle = raw_data['candles'][0]
            normalized_kline = OANDAKline(
                symbol=raw_data['instrument'],
                interval=candle['granularity'],
                open_time=float(candle['time']),
                close_time=float(candle['completeTime']),
                open_price=float(candle['mid']['o']),
                high_price=float(candle['mid']['h']),
                low_price=float(candle['mid']['l']),
                close_price=float(candle['mid']['c']),
                volume=float(candle['volume']),
                quote_volume=float(candle['volume']),  # OANDA doesn't separate quote volume
                trade_count=int(candle.get('tradeCount', 0))
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
