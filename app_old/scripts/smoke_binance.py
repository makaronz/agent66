#!/usr/bin/env python3
"""
Optional Binance smoke (testnet).

Requires:
  - python-binance installed (pip install python-binance)
  - BINANCE_TESTNET=true, BINANCE_API_KEY, BINANCE_API_SECRET

This script does not place orders by default; set PLACE_ORDER=1 to try a tiny
market order (use at your own risk, testnet recommended).
"""
import os
import sys
import os as _os
sys.path.append(_os.path.dirname(_os.path.dirname(__file__)))
import asyncio
from interfaces import Orders
from providers.binance import BinanceExecutorClient


async def main():
    client = BinanceExecutorClient(config={})
    place = str(os.getenv("PLACE_ORDER", "0")).lower() in ("1", "true", "yes")

    if not place:
        print("Dry run: not placing orders. Set PLACE_ORDER=1 to send a tiny testnet order.")
        return

    # Tiny MARKET order example (testnet)
    orders = Orders(items=[{
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quantity": 0.001,
    }])

    report = await client.execute(orders)
    print("accepted:", report.accepted)
    print("rejected:", report.rejected)


if __name__ == "__main__":
    asyncio.run(main())
