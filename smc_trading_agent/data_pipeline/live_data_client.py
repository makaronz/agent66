"""
Live Data Client for SMC Trading Agent

Fetches live OHLCV market data from TypeScript backend API.
Replaces direct exchange connections and Kafka for simplified architecture.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
import pandas as pd
import aiohttp
from datetime import datetime


logger = logging.getLogger(__name__)


class LiveDataClient:
    """
    Client to fetch live OHLCV data from TypeScript backend API.
    
    This replaces the MarketDataProcessor that used mock data,
    providing real live market data from WebSocket connections
    maintained by the TypeScript backend.
    """
    
    def __init__(self, base_url: str = "http://localhost:3001", timeout: int = 10):
        """
        Initialize live data client.
        
        Args:
            base_url: Base URL of TypeScript backend API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Live Data Client initialized for {base_url}")
        
        # Performance metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_latency': 0.0,
            'last_fetch_time': 0
        }
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
    
    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.info("Live Data Client session closed")
    
    async def get_latest_ohlcv_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Fetch live OHLCV data for a symbol.
        
        This method signature matches the original MarketDataProcessor
        for drop-in replacement compatibility.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe ('1h', '1m', etc.)
            limit: Number of candles to fetch
        
        Returns:
            pandas DataFrame with OHLCV data, or None if failed
        """
        start_time = time.time()
        self.metrics['total_requests'] += 1
        
        try:
            # Ensure session exists
            await self._ensure_session()
            
            # Normalize symbol format (BTC/USDT -> BTCUSDT for API)
            api_symbol = symbol.replace('/', '')
            
            # Build API URL
            url = f"{self.base_url}/api/trading/live-ohlcv"
            params = {
                'symbol': api_symbol,
                'timeframe': timeframe,
                'limit': limit
            }
            
            # Make request
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(
                        f"API request failed: {response.status} - {error_text}"
                    )
                    self.metrics['failed_requests'] += 1
                    return None
                
                data = await response.json()
                
                if not data.get('success'):
                    self.logger.error(f"API returned error: {data.get('error')}")
                    self.metrics['failed_requests'] += 1
                    return None
                
                # Convert to DataFrame
                ohlcv_data = data.get('data', [])
                if not ohlcv_data:
                    self.logger.warning(f"No OHLCV data returned for {symbol}")
                    return None
                
                df = pd.DataFrame(ohlcv_data)
                
                # Convert timestamp to datetime and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Ensure numeric columns
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Log latency
                latency = (time.time() - start_time) * 1000
                self.metrics['total_latency'] += latency
                self.metrics['successful_requests'] += 1
                self.metrics['last_fetch_time'] = time.time()
                
                self.logger.info(
                    f"📊 Fetched {len(df)} bars of live data for {symbol} {timeframe}"
                    f" (latency: {latency:.1f}ms, source: {data.get('source', 'unknown')})"
                )
                
                return df
                
        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout fetching data for {symbol}")
            self.metrics['failed_requests'] += 1
            return None
            
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error fetching data for {symbol}: {str(e)}")
            self.metrics['failed_requests'] += 1
            return None
            
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching data for {symbol}: {str(e)}",
                exc_info=True
            )
            self.metrics['failed_requests'] += 1
            return None
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check health of TypeScript backend API.
        
        Returns:
            Dictionary with health status
        """
        try:
            await self._ensure_session()
            
            url = f"{self.base_url}/api/health"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'healthy': True,
                        'backend_status': data,
                        'timestamp': time.time()
                    }
                else:
                    return {
                        'healthy': False,
                        'status_code': response.status,
                        'timestamp': time.time()
                    }
                    
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the client.
        
        Returns:
            Dictionary with metrics
        """
        avg_latency = (
            self.metrics['total_latency'] / self.metrics['successful_requests']
            if self.metrics['successful_requests'] > 0
            else 0
        )
        
        success_rate = (
            self.metrics['successful_requests'] / self.metrics['total_requests'] * 100
            if self.metrics['total_requests'] > 0
            else 0
        )
        
        return {
            'total_requests': self.metrics['total_requests'],
            'successful_requests': self.metrics['successful_requests'],
            'failed_requests': self.metrics['failed_requests'],
            'success_rate': success_rate,
            'average_latency_ms': avg_latency,
            'last_fetch_time': self.metrics['last_fetch_time'],
            'last_fetch_ago_seconds': time.time() - self.metrics['last_fetch_time']
        }
    
    # Backwards compatibility - sync method wrapper
    def get_latest_ohlcv_data_sync(
        self,
        symbol: str,
        timeframe: str = "1h"
    ) -> Optional[pd.DataFrame]:
        """
        Synchronous wrapper for get_latest_ohlcv_data.
        
        For compatibility with synchronous code.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.get_latest_ohlcv_data(symbol, timeframe)
                    )
                    return future.result(timeout=self.timeout)
            else:
                # Not in async context, can use asyncio.run
                return asyncio.run(self.get_latest_ohlcv_data(symbol, timeframe))
                
        except Exception as e:
            self.logger.error(f"Sync fetch failed: {str(e)}")
            return None


# Singleton instance for easy access
_live_data_client_instance: Optional[LiveDataClient] = None


def get_live_data_client(base_url: str = "http://localhost:3001") -> LiveDataClient:
    """
    Get or create singleton instance of LiveDataClient.
    
    Args:
        base_url: Base URL of TypeScript backend API
    
    Returns:
        LiveDataClient instance
    """
    global _live_data_client_instance
    
    if _live_data_client_instance is None:
        _live_data_client_instance = LiveDataClient(base_url=base_url)
    
    return _live_data_client_instance

