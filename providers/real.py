"""
Real providers for online mode (safe-by-default).

Analyzer attempts to use smc_detector.SMCIndicators if available and returns
decisions from detected patterns. DecisionEngine translates decisions to Order
intents with a simple heuristic. ExecutorClient remains a stub unless replaced
by an exchange-specific client (e.g., providers.binance.BinanceExecutorClient).
"""
import logging
from typing import Optional

from interfaces import (
    MarketBatch, Decisions, Orders, ExecReport, RiskState,
    DataFeed, Analyzer, DecisionEngine, ExecutorClient, RiskManager,
)


class RealDataFeed(DataFeed):
    def __init__(self, config: dict):
        self.config = config
        # In a real impl, initialize websockets/connectors here

    async def get_latest_data(self) -> Optional[MarketBatch]:
        # TODO: wire to data_pipeline if available (or Kafka consumer)
        logging.debug("RealDataFeed.get_latest_data -> not yet implemented")
        return None


class RealAnalyzer(Analyzer):
    def __init__(self, config: dict):
        self.config = config
        self._indicators = None
        try:
            from smc_detector.indicators import SMCIndicators  # type: ignore
            self._indicators = SMCIndicators()
        except Exception as e:
            logging.warning("RealAnalyzer: SMCIndicators unavailable: %s", e)

    # Optional warm-up to help readiness
    def warm_up(self):
        try:
            if self._indicators is None:
                return False
            import pandas as pd  # type: ignore
            import numpy as np  # type: ignore
            from datetime import datetime, timedelta
            n = 60
            ts0 = datetime.utcnow() - timedelta(minutes=n)
            idx = [ts0 + timedelta(minutes=i) for i in range(n)]
            prices = np.cumsum(np.random.normal(0, 1, n)) + 30000
            highs = prices + np.random.uniform(0, 5, n)
            lows = prices - np.random.uniform(0, 5, n)
            opens = prices + np.random.uniform(-1, 1, n)
            closes = prices + np.random.uniform(-1, 1, n)
            vols = np.random.uniform(10, 100, n)
            df = pd.DataFrame({
                'timestamp': idx, 'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': vols
            })
            _ = self._indicators.liquidity_sweep_detection(df)
            return True
        except Exception as e:
            logging.debug("RealAnalyzer warm_up skipped: %s", e)
            return False

    async def analyze(self, batch: MarketBatch) -> Decisions:
        if self._indicators is None or batch.ohlcv is None:
            logging.debug("RealAnalyzer.analyze -> empty (no indicators or empty batch)")
            return Decisions(items=[])

        df = batch.ohlcv
        try:
            # Example: use liquidity sweep detection to derive signals
            sweeps = self._indicators.liquidity_sweep_detection(df)
            decisions = []
            for s in sweeps.get('liquidity_sweeps', [])[:5]:
                # Simplified mapping: bullish_sweep => BUY, bearish_sweep => SELL
                side = 'BUY' if s['type'] == 'bullish_sweep' else 'SELL'
                decision = {
                    'symbol': batch.symbol,
                    'side': side,
                    'confidence': s.get('confidence', 0.5),
                    'source': 'liquidity_sweep'
                }
                # Optional price level for LIMIT hint
                price_level = s.get('price_level')
                if price_level:
                    decision['price'] = float(price_level)
                    decision['order_type_hint'] = 'LIMIT'
                decisions.append(decision)
            return Decisions(items=decisions)
        except Exception as e:
            logging.warning("RealAnalyzer.analyze failed: %s", e)
            return Decisions(items=[])


class RealDecisionEngine(DecisionEngine):
    def __init__(self, config: dict):
        self.config = config

    async def process(self, decisions: Decisions) -> Orders:
        items = []
        default_qty = float(self.config.get('default_order_qty', 0.001))
        for d in decisions.items:
            side = (d.get('side') or 'BUY').upper()
            order_type = 'LIMIT' if d.get('price') else 'MARKET'
            order = {
                'symbol': d.get('symbol', 'BTCUSDT'),
                'side': side,
                'type': order_type,
                'quantity': d.get('quantity', default_qty),
            }
            if order_type == 'LIMIT':
                order['price'] = float(d['price'])
            items.append(order)
        logging.debug("RealDecisionEngine: built %d orders", len(items))
        return Orders(items=items)


class RealExecutorClient(ExecutorClient):
    def __init__(self, config: dict):
        self.config = config
        # TODO: integrate with Rust executor (FFI/bridge)

    async def execute(self, orders: Orders) -> ExecReport:
        # TODO: call Rust executor adapter
        logging.debug("RealExecutorClient.execute -> stub report")
        return ExecReport(accepted=[], rejected=[])


class RealRiskManager(RiskManager):
    def __init__(self, config: dict):
        self.config = config
        # Could compose risk_manager.SMCRiskManager underneath

    async def assess(self, report: ExecReport) -> RiskState:
        # TODO: map to SMCRiskManager checks
        logging.debug("RealRiskManager.assess -> ok (stub)")
        return RiskState(ok=True, details="stub")


__all__ = [
    "RealDataFeed",
    "RealAnalyzer",
    "RealDecisionEngine",
    "RealExecutorClient",
    "RealRiskManager",
]
