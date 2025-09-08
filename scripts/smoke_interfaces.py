#!/usr/bin/env python3
"""Lightweight smoke to validate interface wiring with mocks."""
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from interfaces import MarketBatch
from providers.mock import MockDataFeed, MockAnalyzer, MockDecisionEngine, MockExecutorClient, MockRiskManager


async def main():
    data_feed = MockDataFeed()
    analyzer = MockAnalyzer()
    decision_engine = MockDecisionEngine()
    executor = MockExecutorClient()
    risk = MockRiskManager()

    batch = await data_feed.get_latest_data()
    if batch is None:
        print("OK: data_feed returns None in mock mode")
    else:
        print("WARN: unexpected batch in mock mode")

    # Provide a dummy batch to analyzer
    dummy = MarketBatch(exchange="mock", symbol="BTCUSDT", ohlcv=None)
    decisions = await analyzer.analyze(dummy)
    orders = await decision_engine.process(decisions)
    report = await executor.execute(orders)
    state = await risk.assess(report)
    print("OK: pipeline executed; risk.ok=", state.ok)


if __name__ == "__main__":
    asyncio.run(main())
