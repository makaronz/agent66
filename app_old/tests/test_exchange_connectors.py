"""
Integration-like tests for exchange connectors (Binance, ByBit, OANDA).

These tests validate:
- WebSocket connect/subscribe/disconnect flow (mocked)
- REST fetch happy-path and error handling (mocked)
- Data normalization for trade/orderbook/kline payloads
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from data_pipeline.exchange_connectors.binance_connector import BinanceConnector
from data_pipeline.exchange_connectors.bybit_connector import ByBitConnector
from data_pipeline.exchange_connectors.oanda_connector import OANDAConnector
from data_pipeline.exchange_connectors import (
    RESTAPIError,
    DataNormalizationError,
)


def _mk_response(status: int = 200, payload: Dict[str, Any] | None = None):
    class _Resp:
        def __init__(self, st: int, data: Dict[str, Any] | None):
            self.status = st
            self._data = data or {}

        async def json(self):
            return self._data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    return _Resp(status, payload or {"ok": True})


@pytest.mark.asyncio
async def test_binance_ws_connect_subscribe_disconnect():
    config = {"websocket_url": "wss://stream.binance.com:9443/ws/"}
    connector = BinanceConnector(config)

    fake_ws = Mock()
    fake_ws.ping = AsyncMock(return_value=None)
    fake_ws.send = AsyncMock(return_value=None)
    fake_ws.recv = AsyncMock(return_value=b'{"result": null, "id": 1}')
    fake_ws.close = AsyncMock(return_value=None)

    with patch("data_pipeline.exchange_connectors.binance_connector.websockets.connect", new=AsyncMock(return_value=fake_ws)):
        assert await connector.connect_websocket() is True
        ok = await connector.subscribe_to_streams(["btcusdt@trade"])  # result==null → OK
        assert ok is True
        assert await connector.disconnect_websocket() is True


@pytest.mark.asyncio
async def test_bybit_ws_connect_subscribe_disconnect():
    connector = ByBitConnector({"websocket_url": "wss://stream.bybit.com/v5/public/spot"})

    fake_ws = Mock()
    fake_ws.ping = AsyncMock(return_value=None)
    fake_ws.send = AsyncMock(return_value=None)
    fake_ws.recv = AsyncMock(return_value=b'{"success": true, "op": "subscribe"}')
    fake_ws.close = AsyncMock(return_value=None)

    with patch("data_pipeline.exchange_connectors.bybit_connector.websockets.connect", new=AsyncMock(return_value=fake_ws)):
        assert await connector.connect_websocket() is True
        assert await connector.subscribe_to_streams(["orderbook.1.BTCUSDT"]) is True
        assert await connector.disconnect_websocket() is True


@pytest.mark.asyncio
async def test_oanda_ws_connect_subscribe_disconnect():
    connector = OANDAConnector({"api_key": "x", "account_id": "acc-1"})

    fake_ws = Mock()
    fake_ws.ping = AsyncMock(return_value=None)
    fake_ws.send = AsyncMock(return_value=None)
    # OANDA simple subscription: any non-error JSON treated as OK
    fake_ws.recv = AsyncMock(return_value=b'{"heartbeat": true}')
    fake_ws.close = AsyncMock(return_value=None)

    with patch("data_pipeline.exchange_connectors.oanda_connector.websockets.connect", new=AsyncMock(return_value=fake_ws)):
        assert await connector.connect_websocket() is True
        assert await connector.subscribe_to_streams(["EUR_USD"]) is True
        assert await connector.disconnect_websocket() is True


@pytest.mark.asyncio
async def test_binance_rest_happy_and_error():
    connector = BinanceConnector({})

    fake_session = Mock()
    fake_session.get = AsyncMock(return_value=_mk_response(200, {"pong": True}))

    with patch("data_pipeline.exchange_connectors.binance_connector.aiohttp.ClientSession", return_value=fake_session):
        data = await connector.fetch_rest_data("/api/v3/ping")
        assert data.get("pong") is True

    # Error path
    fake_session_err = Mock()
    fake_session_err.get = AsyncMock(return_value=_mk_response(500, {"error": "x"}))
    with patch("data_pipeline.exchange_connectors.binance_connector.aiohttp.ClientSession", return_value=fake_session_err):
        with pytest.raises(RESTAPIError):
            await connector.fetch_rest_data("/api/v3/ping")


@pytest.mark.asyncio
async def test_normalize_data_trade_and_orderbook():
    binance = BinanceConnector({})
    bybit = ByBitConnector({})
    oanda = OANDAConnector({})

    # Binance trade
    b_trade = {"s": "BTCUSDT", "p": "50000", "q": "0.01", "S": "BUY", "T": 1710000000000, "t": 1, "Q": "500"}
    out = await binance.normalize_data(b_trade, "trade")
    assert out["exchange"] == "binance"
    assert out["symbol"] == "BTCUSDT"

    # ByBit trade
    y_trade = {"s": "BTCUSDT", "p": "50000", "v": "0.02", "S": "Buy", "T": 1710000000001, "i": "2", "q": "1000"}
    out2 = await bybit.normalize_data(y_trade, "trade")
    assert out2["exchange"] == "bybit"

    # OANDA orderbook (simplified)
    ob = {"instrument": "EUR_USD", "time": 1710000000, "bids": [{"price": "1.1", "liquidity": 100}], "asks": [{"price": "1.2", "liquidity": 200}]}
    out3 = await oanda.normalize_data(ob, "orderbook")
    assert out3["exchange"] == "oanda"
    assert out3["symbol"] == "EUR_USD"

    # Wrong type
    with pytest.raises(DataNormalizationError):
        await binance.normalize_data({}, "unknown-type")


