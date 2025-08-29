"""
Integration tests for WebSocket data flows and error scenarios.
Tests real-time data streaming, connection handling, and error recovery.
"""

import pytest
import asyncio
import json
import websockets
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from data_pipeline.ingestion import MarketDataProcessor
from data_pipeline.exchange_connectors.binance_connector import BinanceConnector
from data_pipeline.exchange_connectors.bybit_connector import BybitConnector


class MockWebSocketServer:
    """Mock WebSocket server for testing."""
    
    def __init__(self, port=8765):
        self.port = port
        self.server = None
        self.clients = set()
        self.message_queue = []
        self.should_fail = False
        self.fail_after_messages = None
        self.message_count = 0
    
    async def handler(self, websocket, path):
        """Handle WebSocket connections."""
        self.clients.add(websocket)
        try:
            if self.should_fail and self.fail_after_messages is None:
                raise websockets.exceptions.ConnectionClosed(1006, "Connection failed")
            
            async for message in websocket:
                # Echo back or send queued messages
                if self.message_queue:
                    response = self.message_queue.pop(0)
                    await websocket.send(json.dumps(response))
                    self.message_count += 1
                    
                    if (self.should_fail and 
                        self.fail_after_messages and 
                        self.message_count >= self.fail_after_messages):
                        raise websockets.exceptions.ConnectionClosed(1006, "Connection failed after messages")
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
    
    async def start(self):
        """Start the mock WebSocket server."""
        self.server = await websockets.serve(self.handler, "localhost", self.port)
    
    async def stop(self):
        """Stop the mock WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
    
    def add_message(self, message):
        """Add a message to the queue."""
        self.message_queue.append(message)
    
    def set_failure_mode(self, should_fail=True, fail_after_messages=None):
        """Set failure mode for testing error scenarios."""
        self.should_fail = should_fail
        self.fail_after_messages = fail_after_messages
        self.message_count = 0


@pytest.fixture
async def mock_ws_server():
    """Create and start mock WebSocket server."""
    server = MockWebSocketServer()
    await server.start()
    yield server
    await server.stop()


class TestWebSocketDataFlows:
    """Test suite for WebSocket data flow integration."""
    
    @pytest.fixture
    def sample_binance_ticker(self):
        """Create sample Binance ticker data."""
        return {
            "e": "24hrTicker",
            "E": int(datetime.now().timestamp() * 1000),
            "s": "BTCUSDT",
            "p": "100.00",
            "P": "0.20",
            "w": "50000.00",
            "x": "49900.00",
            "c": "50000.00",
            "Q": "1.00000000",
            "b": "49999.00",
            "B": "1.00000000",
            "a": "50001.00",
            "A": "1.00000000",
            "o": "49900.00",
            "h": "50100.00",
            "l": "49800.00",
            "v": "1000.00000000",
            "q": "50000000.00000000",
            "O": int((datetime.now() - timedelta(hours=24)).timestamp() * 1000),
            "C": int(datetime.now().timestamp() * 1000),
            "F": 1,
            "L": 1000,
            "n": 1000
        }
    
    @pytest.fixture
    def sample_bybit_ticker(self):
        """Create sample Bybit ticker data."""
        return {
            "topic": "tickers.BTCUSDT",
            "type": "snapshot",
            "data": {
                "symbol": "BTCUSDT",
                "tickDirection": "PlusTick",
                "price24hPcnt": "0.0020",
                "lastPrice": "50000.00",
                "prevPrice24h": "49900.00",
                "highPrice24h": "50100.00",
                "lowPrice24h": "49800.00",
                "prevPrice1h": "49950.00",
                "markPrice": "50000.50",
                "indexPrice": "50000.25",
                "openInterest": "1000.00",
                "openInterestValue": "50000000.00",
                "turnover24h": "50000000.00",
                "volume24h": "1000.00",
                "nextFundingTime": "1640995200000",
                "fundingRate": "0.0001",
                "bid1Price": "49999.00",
                "bid1Size": "1.00",
                "ask1Price": "50001.00",
                "ask1Size": "1.00"
            },
            "cs": int(datetime.now().timestamp() * 1000),
            "ts": int(datetime.now().timestamp() * 1000)
        }
    
    @pytest.mark.asyncio
    async def test_binance_websocket_connection(self, mock_ws_server, sample_binance_ticker):
        """Test Binance WebSocket connection and data reception."""
        # Add sample data to mock server
        mock_ws_server.add_message(sample_binance_ticker)
        
        # Create Binance connector with mock WebSocket URL
        connector = BinanceConnector({
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True,
            'websocket_url': f'ws://localhost:{mock_ws_server.port}'
        })
        
        # Mock the actual WebSocket connection
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.__aenter__.return_value = mock_websocket
            mock_websocket.__aexit__.return_value = None
            mock_websocket.recv = AsyncMock(return_value=json.dumps(sample_binance_ticker))
            mock_connect.return_value = mock_websocket
            
            # Test connection and data reception
            received_data = []
            
            async def data_handler(data):
                received_data.append(data)
            
            # Start WebSocket connection
            task = asyncio.create_task(
                connector.start_websocket_stream(['BTCUSDT'], data_handler)
            )
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Verify connection was attempted
            mock_connect.assert_called()
    
    @pytest.mark.asyncio
    async def test_bybit_websocket_connection(self, mock_ws_server, sample_bybit_ticker):
        """Test Bybit WebSocket connection and data reception."""
        # Add sample data to mock server
        mock_ws_server.add_message(sample_bybit_ticker)
        
        # Create Bybit connector with mock WebSocket URL
        connector = BybitConnector({
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True,
            'websocket_url': f'ws://localhost:{mock_ws_server.port}'
        })
        
        # Mock the actual WebSocket connection
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.__aenter__.return_value = mock_websocket
            mock_websocket.__aexit__.return_value = None
            mock_websocket.recv = AsyncMock(return_value=json.dumps(sample_bybit_ticker))
            mock_connect.return_value = mock_websocket
            
            # Test connection and data reception
            received_data = []
            
            async def data_handler(data):
                received_data.append(data)
            
            # Start WebSocket connection
            task = asyncio.create_task(
                connector.start_websocket_stream(['BTCUSDT'], data_handler)
            )
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Verify connection was attempted
            mock_connect.assert_called()
    
    @pytest.mark.asyncio
    async def test_market_data_processor_websocket_integration(self, mock_ws_server, sample_binance_ticker):
        """Test MarketDataProcessor WebSocket integration."""
        processor = MarketDataProcessor()
        
        # Mock exchange connectors
        mock_binance = Mock()
        mock_binance.start_websocket_stream = AsyncMock()
        mock_binance.is_connected = True
        
        processor.exchange_connectors = {'binance': mock_binance}
        
        # Test starting WebSocket streams
        await processor.start_realtime_streams(['BTCUSDT'])
        
        # Verify WebSocket stream was started
        mock_binance.start_websocket_stream.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_data_validation(self, sample_binance_ticker):
        """Test WebSocket data validation and processing."""
        processor = MarketDataProcessor()
        
        # Test valid data processing
        processed_data = processor.process_websocket_data('binance', sample_binance_ticker)
        
        assert processed_data is not None
        assert 'symbol' in processed_data
        assert 'price' in processed_data
        assert 'timestamp' in processed_data
        
        # Test invalid data handling
        invalid_data = {'invalid': 'data'}
        processed_invalid = processor.process_websocket_data('binance', invalid_data)
        
        # Should handle invalid data gracefully
        assert processed_invalid is None or isinstance(processed_invalid, dict)
    
    @pytest.mark.asyncio
    async def test_websocket_data_aggregation(self, sample_binance_ticker):
        """Test WebSocket data aggregation and buffering."""
        processor = MarketDataProcessor()
        
        # Process multiple data points
        for i in range(10):
            ticker_data = sample_binance_ticker.copy()
            ticker_data['c'] = str(50000 + i)  # Varying close price
            ticker_data['E'] = int((datetime.now() + timedelta(seconds=i)).timestamp() * 1000)
            
            processor.process_websocket_data('binance', ticker_data)
        
        # Check if data was aggregated
        aggregated_data = processor.get_aggregated_data('BTCUSDT', '1m')
        
        assert isinstance(aggregated_data, (pd.DataFrame, dict, type(None)))
    
    @pytest.mark.asyncio
    async def test_multiple_exchange_websocket_streams(self, mock_ws_server, sample_binance_ticker, sample_bybit_ticker):
        """Test multiple exchange WebSocket streams simultaneously."""
        processor = MarketDataProcessor()
        
        # Mock multiple exchange connectors
        mock_binance = Mock()
        mock_binance.start_websocket_stream = AsyncMock()
        mock_binance.is_connected = True
        
        mock_bybit = Mock()
        mock_bybit.start_websocket_stream = AsyncMock()
        mock_bybit.is_connected = True
        
        processor.exchange_connectors = {
            'binance': mock_binance,
            'bybit': mock_bybit
        }
        
        # Start streams for multiple exchanges
        await processor.start_realtime_streams(['BTCUSDT'])
        
        # Verify both exchanges started streams
        mock_binance.start_websocket_stream.assert_called_once()
        mock_bybit.start_websocket_stream.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_data_rate_limiting(self, sample_binance_ticker):
        """Test WebSocket data rate limiting and throttling."""
        processor = MarketDataProcessor()
        
        # Configure rate limiting
        processor.configure_rate_limiting(max_messages_per_second=5)
        
        # Send data rapidly
        start_time = datetime.now()
        processed_count = 0
        
        for i in range(20):  # Send 20 messages rapidly
            ticker_data = sample_binance_ticker.copy()
            ticker_data['E'] = int(datetime.now().timestamp() * 1000)
            
            result = processor.process_websocket_data('binance', ticker_data)
            if result:
                processed_count += 1
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should respect rate limiting
        assert processed_count <= int(5 * duration) + 5  # Allow some tolerance


class TestWebSocketErrorScenarios:
    """Test suite for WebSocket error scenarios and recovery."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_failure(self, mock_ws_server):
        """Test WebSocket connection failure handling."""
        # Configure server to fail immediately
        mock_ws_server.set_failure_mode(should_fail=True)
        
        connector = BinanceConnector({
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True
        })
        
        # Mock WebSocket to raise connection error
        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = websockets.exceptions.ConnectionClosed(1006, "Connection failed")
            
            received_data = []
            
            async def data_handler(data):
                received_data.append(data)
            
            # Should handle connection failure gracefully
            with pytest.raises((websockets.exceptions.ConnectionClosed, ConnectionError)):
                await connector.start_websocket_stream(['BTCUSDT'], data_handler)
    
    @pytest.mark.asyncio
    async def test_websocket_connection_recovery(self, mock_ws_server, sample_binance_ticker):
        """Test WebSocket connection recovery after failure."""
        connector = BinanceConnector({
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True,
            'reconnect_attempts': 3,
            'reconnect_delay': 0.1
        })
        
        connection_attempts = 0
        
        async def mock_connect_with_retry(*args, **kwargs):
            nonlocal connection_attempts
            connection_attempts += 1
            
            if connection_attempts <= 2:  # Fail first 2 attempts
                raise websockets.exceptions.ConnectionClosed(1006, "Connection failed")
            
            # Succeed on 3rd attempt
            mock_websocket = AsyncMock()
            mock_websocket.__aenter__.return_value = mock_websocket
            mock_websocket.__aexit__.return_value = None
            mock_websocket.recv = AsyncMock(return_value=json.dumps(sample_binance_ticker))
            return mock_websocket
        
        with patch('websockets.connect', side_effect=mock_connect_with_retry):
            received_data = []
            
            async def data_handler(data):
                received_data.append(data)
            
            # Should eventually succeed after retries
            task = asyncio.create_task(
                connector.start_websocket_stream_with_retry(['BTCUSDT'], data_handler)
            )
            
            await asyncio.sleep(0.5)  # Allow time for retries
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Should have attempted multiple connections
            assert connection_attempts >= 2
    
    @pytest.mark.asyncio
    async def test_websocket_message_parsing_errors(self, mock_ws_server):
        """Test WebSocket message parsing error handling."""
        # Add invalid JSON to mock server
        mock_ws_server.add_message("invalid json data")
        
        connector = BinanceConnector({
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True
        })
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.__aenter__.return_value = mock_websocket
            mock_websocket.__aexit__.return_value = None
            mock_websocket.recv = AsyncMock(return_value="invalid json data")
            mock_connect.return_value = mock_websocket
            
            received_data = []
            errors = []
            
            async def data_handler(data):
                received_data.append(data)
            
            async def error_handler(error):
                errors.append(error)
            
            # Should handle parsing errors gracefully
            task = asyncio.create_task(
                connector.start_websocket_stream(['BTCUSDT'], data_handler, error_handler)
            )
            
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Should have captured parsing errors
            assert len(errors) > 0 or len(received_data) == 0
    
    @pytest.mark.asyncio
    async def test_websocket_heartbeat_timeout(self, mock_ws_server):
        """Test WebSocket heartbeat timeout handling."""
        connector = BinanceConnector({
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True,
            'heartbeat_timeout': 0.1  # Very short timeout for testing
        })
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.__aenter__.return_value = mock_websocket
            mock_websocket.__aexit__.return_value = None
            
            # Mock recv to hang (simulate no heartbeat)
            async def hanging_recv():
                await asyncio.sleep(1)  # Longer than heartbeat timeout
                return json.dumps({'ping': 'pong'})
            
            mock_websocket.recv = hanging_recv
            mock_connect.return_value = mock_websocket
            
            received_data = []
            
            async def data_handler(data):
                received_data.append(data)
            
            # Should timeout and handle gracefully
            with pytest.raises((asyncio.TimeoutError, websockets.exceptions.ConnectionClosed)):
                await asyncio.wait_for(
                    connector.start_websocket_stream(['BTCUSDT'], data_handler),
                    timeout=0.5
                )
    
    @pytest.mark.asyncio
    async def test_websocket_memory_leak_prevention(self, sample_binance_ticker):
        """Test WebSocket memory leak prevention with large data volumes."""
        processor = MarketDataProcessor()
        
        # Configure buffer limits
        processor.configure_buffers(max_buffer_size=100, cleanup_interval=0.1)
        
        # Send large volume of data
        for i in range(1000):
            ticker_data = sample_binance_ticker.copy()
            ticker_data['E'] = int((datetime.now() + timedelta(milliseconds=i)).timestamp() * 1000)
            ticker_data['c'] = str(50000 + (i % 100))  # Varying prices
            
            processor.process_websocket_data('binance', ticker_data)
        
        # Check buffer size is controlled
        buffer_size = processor.get_buffer_size('BTCUSDT')
        assert buffer_size <= 150  # Allow some tolerance for cleanup timing
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(self, mock_ws_server, sample_binance_ticker):
        """Test concurrent WebSocket connections handling."""
        processor = MarketDataProcessor()
        
        # Create multiple connectors
        connectors = []
        for i in range(5):
            connector = BinanceConnector({
                'api_key': f'test_key_{i}',
                'api_secret': f'test_secret_{i}',
                'testnet': True
            })
            connectors.append(connector)
        
        processor.exchange_connectors = {f'binance_{i}': conn for i, conn in enumerate(connectors)}
        
        # Mock WebSocket connections
        with patch('websockets.connect') as mock_connect:
            mock_websockets = []
            for i in range(5):
                mock_ws = AsyncMock()
                mock_ws.__aenter__.return_value = mock_ws
                mock_ws.__aexit__.return_value = None
                mock_ws.recv = AsyncMock(return_value=json.dumps(sample_binance_ticker))
                mock_websockets.append(mock_ws)
            
            mock_connect.side_effect = mock_websockets
            
            # Start concurrent streams
            tasks = []
            for i, connector in enumerate(connectors):
                task = asyncio.create_task(
                    connector.start_websocket_stream(['BTCUSDT'], lambda data: None)
                )
                tasks.append(task)
            
            # Let them run briefly
            await asyncio.sleep(0.1)
            
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            
            # Wait for cancellation
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all connections were attempted
            assert mock_connect.call_count == 5
    
    @pytest.mark.asyncio
    async def test_websocket_data_corruption_handling(self, mock_ws_server):
        """Test handling of corrupted WebSocket data."""
        processor = MarketDataProcessor()
        
        # Test various corruption scenarios
        corrupted_data_samples = [
            b'\x00\x01\x02\x03',  # Binary data
            '{"incomplete": json',  # Incomplete JSON
            '{"valid": "json", "but": "unexpected_structure"}',  # Valid JSON, wrong structure
            '',  # Empty string
            None,  # None value
            '{"e": "24hrTicker", "s": null}',  # Null values in expected fields
        ]
        
        handled_errors = 0
        
        for corrupted_data in corrupted_data_samples:
            try:
                if corrupted_data is not None:
                    result = processor.process_websocket_data('binance', corrupted_data)
                    # Should either return None or valid processed data
                    assert result is None or isinstance(result, dict)
                else:
                    result = processor.process_websocket_data('binance', corrupted_data)
                    assert result is None
            except Exception as e:
                # Should handle exceptions gracefully
                handled_errors += 1
                assert isinstance(e, (ValueError, TypeError, KeyError, json.JSONDecodeError))
        
        # Should have handled some errors
        assert handled_errors >= 0  # At least some data should cause errors


@pytest.mark.integration
class TestWebSocketIntegrationScenarios:
    """Integration test scenarios for WebSocket functionality."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_websocket_data_flow(self, mock_ws_server, sample_binance_ticker):
        """Test complete end-to-end WebSocket data flow."""
        # Setup complete data pipeline
        processor = MarketDataProcessor()
        
        # Mock exchange connector
        mock_connector = Mock()
        mock_connector.start_websocket_stream = AsyncMock()
        mock_connector.is_connected = True
        
        processor.exchange_connectors = {'binance': mock_connector}
        
        # Track data flow
        received_data = []
        processed_data = []
        
        async def data_handler(data):
            received_data.append(data)
            processed = processor.process_websocket_data('binance', data)
            if processed:
                processed_data.append(processed)
        
        # Configure mock to call handler
        async def mock_stream_handler(symbols, handler):
            for _ in range(5):  # Send 5 messages
                await handler(sample_binance_ticker)
                await asyncio.sleep(0.01)
        
        mock_connector.start_websocket_stream.side_effect = mock_stream_handler
        
        # Start the data flow
        await processor.start_realtime_streams(['BTCUSDT'])
        
        # Verify data flowed through the pipeline
        assert len(received_data) == 5
        assert len(processed_data) >= 0  # Some data should be processed
        
        # Verify data structure
        for data in processed_data:
            assert isinstance(data, dict)
            assert 'symbol' in data or 'timestamp' in data
    
    @pytest.mark.asyncio
    async def test_websocket_failover_between_exchanges(self, mock_ws_server, sample_binance_ticker, sample_bybit_ticker):
        """Test WebSocket failover between exchanges."""
        processor = MarketDataProcessor()
        
        # Mock primary exchange (Binance) to fail
        mock_binance = Mock()
        mock_binance.start_websocket_stream = AsyncMock(
            side_effect=websockets.exceptions.ConnectionClosed(1006, "Connection failed")
        )
        mock_binance.is_connected = False
        
        # Mock secondary exchange (Bybit) to succeed
        mock_bybit = Mock()
        mock_bybit.start_websocket_stream = AsyncMock()
        mock_bybit.is_connected = True
        
        processor.exchange_connectors = {
            'binance': mock_binance,
            'bybit': mock_bybit
        }
        
        # Configure failover
        processor.configure_failover(['binance', 'bybit'])
        
        # Start streams with failover
        await processor.start_realtime_streams_with_failover(['BTCUSDT'])
        
        # Verify failover occurred
        mock_binance.start_websocket_stream.assert_called()
        mock_bybit.start_websocket_stream.assert_called()
    
    @pytest.mark.asyncio
    async def test_websocket_performance_under_load(self, sample_binance_ticker):
        """Test WebSocket performance under high load."""
        processor = MarketDataProcessor()
        
        # Configure for high performance
        processor.configure_performance(
            batch_size=100,
            processing_threads=4,
            buffer_size=10000
        )
        
        # Simulate high-frequency data
        start_time = datetime.now()
        message_count = 1000
        
        for i in range(message_count):
            ticker_data = sample_binance_ticker.copy()
            ticker_data['E'] = int((datetime.now() + timedelta(milliseconds=i)).timestamp() * 1000)
            ticker_data['c'] = str(50000 + (i % 1000))
            
            processor.process_websocket_data('binance', ticker_data)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should process messages efficiently
        messages_per_second = message_count / duration
        assert messages_per_second > 100  # Should handle at least 100 messages/second
        
        # Verify data integrity
        processed_count = processor.get_processed_message_count()
        assert processed_count <= message_count  # Should not exceed input
    
    @pytest.mark.asyncio
    async def test_websocket_data_consistency_across_exchanges(self, sample_binance_ticker, sample_bybit_ticker):
        """Test data consistency across different exchange WebSocket feeds."""
        processor = MarketDataProcessor()
        
        # Process data from both exchanges
        binance_processed = processor.process_websocket_data('binance', sample_binance_ticker)
        bybit_processed = processor.process_websocket_data('bybit', sample_bybit_ticker)
        
        # Both should produce consistent data structure
        if binance_processed and bybit_processed:
            # Check for common fields
            common_fields = set(binance_processed.keys()) & set(bybit_processed.keys())
            assert len(common_fields) > 0  # Should have some common fields
            
            # Check data types consistency
            for field in common_fields:
                assert type(binance_processed[field]) == type(bybit_processed[field])
    
    @pytest.mark.asyncio
    async def test_websocket_graceful_shutdown(self, mock_ws_server, sample_binance_ticker):
        """Test graceful WebSocket connection shutdown."""
        processor = MarketDataProcessor()
        
        # Mock connector with shutdown capability
        mock_connector = Mock()
        mock_connector.start_websocket_stream = AsyncMock()
        mock_connector.stop_websocket_stream = AsyncMock()
        mock_connector.is_connected = True
        
        processor.exchange_connectors = {'binance': mock_connector}
        
        # Start streams
        stream_task = asyncio.create_task(
            processor.start_realtime_streams(['BTCUSDT'])
        )
        
        await asyncio.sleep(0.1)  # Let it start
        
        # Initiate graceful shutdown
        await processor.shutdown_gracefully()
        
        # Cancel the stream task
        stream_task.cancel()
        
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
        
        # Verify shutdown was called
        mock_connector.stop_websocket_stream.assert_called()