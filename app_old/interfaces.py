"""
Interfaces and data contracts for the trading loop orchestration.

Python owns orchestration; Rust stays a pure executor behind an adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any, List, Optional, Mapping


# ----- Data Contracts -----

@dataclass
class MarketBatch:
    """Normalized batch of market data used by the pipeline."""
    exchange: str
    symbol: str
    ohlcv: Any  # e.g., pandas.DataFrame or numpy arrays
    ts: Optional[float] = None


@dataclass
class Decisions:
    """Model decisions/signals output by analysis stage."""
    items: List[Mapping[str, Any]]


@dataclass
class Orders:
    """Concrete order intents ready for execution."""
    items: List[Mapping[str, Any]]


@dataclass
class ExecReport:
    """Execution outcome for submitted orders."""
    accepted: List[Mapping[str, Any]]
    rejected: List[Mapping[str, Any]]


@dataclass
class RiskState:
    """Risk evaluation/limits status based on latest execution."""
    ok: bool
    details: Optional[str] = None


# ----- Service Protocols (narrow, explicit) -----

class DataFeed(Protocol):
    async def get_latest_data(self) -> Optional[MarketBatch]:
        ...


class Analyzer(Protocol):
    async def analyze(self, batch: MarketBatch) -> Decisions:
        ...


class DecisionEngine(Protocol):
    async def process(self, decisions: Decisions) -> Orders:
        ...


class ExecutorClient(Protocol):
    async def execute(self, orders: Orders) -> ExecReport:
        ...


class RiskManager(Protocol):
    async def assess(self, report: ExecReport) -> RiskState:
        ...


__all__ = [
    # Data contracts
    "MarketBatch",
    "Decisions",
    "Orders",
    "ExecReport",
    "RiskState",
    # Protocols
    "DataFeed",
    "Analyzer",
    "DecisionEngine",
    "ExecutorClient",
    "RiskManager",
]

