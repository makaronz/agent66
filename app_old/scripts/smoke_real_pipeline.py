#!/usr/bin/env python3
"""
Smoke test for RealAnalyzer + RealDecisionEngine pipeline (no execution).

Generates a small dummy OHLCV DataFrame and checks that the pipeline
completes without raising. Requires pandas + numpy; indicators will
degrade gracefully if numba or internals unavailable.
"""
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from interfaces import MarketBatch
from providers.real import RealAnalyzer, RealDecisionEngine


def _dummy_ohlcv(n: int = 120) -> pd.DataFrame:
    ts0 = datetime.utcnow() - timedelta(minutes=n)
    idx = [ts0 + timedelta(minutes=i) for i in range(n)]
    prices = np.cumsum(np.random.normal(0, 1, n)) + 30000
    highs = prices + np.random.uniform(0, 5, n)
    lows = prices - np.random.uniform(0, 5, n)
    opens = prices + np.random.uniform(-1, 1, n)
    closes = prices + np.random.uniform(-1, 1, n)
    vols = np.random.uniform(10, 100, n)
    return pd.DataFrame({
        'timestamp': idx,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': vols,
    })


async def main():
    config = {}
    analyzer = RealAnalyzer(config)
    de = RealDecisionEngine(config)

    df = _dummy_ohlcv()
    batch = MarketBatch(exchange="mock", symbol="BTCUSDT", ohlcv=df)
    decisions = await analyzer.analyze(batch)
    orders = await de.process(decisions)
    print("decisions:", len(decisions.items), "orders:", len(orders.items))


if __name__ == "__main__":
    asyncio.run(main())
