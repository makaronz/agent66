"""
Mock providers implementing interfaces for offline mode.
"""
import logging
from typing import Optional, Mapping, Any, List

from interfaces import (
    MarketBatch, Decisions, Orders, ExecReport, RiskState,
    DataFeed, Analyzer, DecisionEngine, ExecutorClient, RiskManager,
)


class MockDataFeed(DataFeed):
    async def get_latest_data(self) -> Optional[MarketBatch]:
        logging.info("MockDataFeed.get_latest_data -> None batch")
        return None


class MockAnalyzer(Analyzer):
    async def analyze(self, batch: MarketBatch) -> Decisions:
        logging.info("MockAnalyzer.analyze -> empty decisions")
        return Decisions(items=[])


class MockDecisionEngine(DecisionEngine):
    async def process(self, decisions: Decisions) -> Orders:
        logging.info("MockDecisionEngine.process -> empty orders")
        return Orders(items=[])


class MockExecutorClient(ExecutorClient):
    async def execute(self, orders: Orders) -> ExecReport:
        logging.info("MockExecutorClient.execute -> empty report")
        return ExecReport(accepted=[], rejected=[])


class MockRiskManager(RiskManager):
    async def assess(self, report: ExecReport) -> RiskState:
        logging.info("MockRiskManager.assess -> ok")
        return RiskState(ok=True, details="offline mock")


__all__ = [
    "MockDataFeed",
    "MockAnalyzer",
    "MockDecisionEngine",
    "MockExecutorClient",
    "MockRiskManager",
]

