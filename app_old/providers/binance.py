"""
Binance ExecutorClient (Python) for Option B: native SDK for a single venue.

Safe-by-default: if python-binance or credentials are missing, the client
degrades gracefully and returns a rejected ExecReport without raising.
"""
from __future__ import annotations

import os
import logging
from typing import List, Mapping, Any

from interfaces import Orders, ExecReport


class BinanceExecutorClient:
    def __init__(self, config: dict):
        self.config = config
        self._ready = False
        self._client = None

        api_key = os.getenv("BINANCE_API_KEY") or self.config.get("binance_api_key")
        api_secret = os.getenv("BINANCE_API_SECRET") or self.config.get("binance_api_secret")
        use_testnet = str(os.getenv("BINANCE_TESTNET", "true")).lower() in ("1", "true", "yes")

        try:
            from binance.client import Client  # type: ignore
        except Exception as e:
            logging.warning(f"python-binance not available: {e}")
            return

        if not api_key or not api_secret:
            logging.warning("Binance credentials not provided; executor will run in dry-reject mode")
            return

        try:
            self._client = Client(api_key, api_secret, testnet=use_testnet)
            # ping readiness
            self._client.ping()
            # simple warm-up: fetch account and exchangeInfo (best-effort)
            try:
                _ = self._client.get_account()
                _ = self._client.get_exchange_info()
            except Exception as inner:
                logging.debug("Binance warm-up non-fatal: %s", inner)
            self._ready = True
            logging.info("BinanceExecutorClient ready (testnet=%s)", use_testnet)
        except Exception as e:
            logging.warning(f"Binance client initialization failed: {e}")

    async def execute(self, orders: Orders) -> ExecReport:
        accepted: List[Mapping[str, Any]] = []
        rejected: List[Mapping[str, Any]] = []

        if not self._client or not self._ready:
            for item in orders.items:
                rejected.append({"order": item, "reason": "binance not ready"})
            return ExecReport(accepted=accepted, rejected=rejected)

        for item in orders.items:
            try:
                symbol = item.get("symbol")
                side = item.get("side", "BUY").upper()
                order_type = item.get("type", "MARKET").upper()
                qty = item.get("quantity")
                price = item.get("price")

                if order_type == "LIMIT":
                    resp = self._client.create_order(
                        symbol=symbol,
                        side=side,
                        type=order_type,
                        timeInForce="GTC",
                        quantity=qty,
                        price=str(price),
                    )
                else:
                    resp = self._client.create_order(
                        symbol=symbol,
                        side=side,
                        type=order_type,
                        quantity=qty,
                    )
                accepted.append({"order": item, "ack": resp})
            except Exception as e:
                logging.warning("Order rejected: %s", e)
                rejected.append({"order": item, "reason": str(e)})

        return ExecReport(accepted=accepted, rejected=rejected)

    # Optional readiness hook
    def ready(self) -> bool:
        return self._ready


__all__ = ["BinanceExecutorClient"]
