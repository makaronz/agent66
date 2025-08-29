"""
End-to-end workflow tests (offline) using the integration example.

These tests validate that the high-level trading flow produces
plausible outputs without hitting external services:
- SMC pattern simulation
- Decision making (fallback or ensemble if available)
- Risk assessment and final signals assembly
"""

from typing import Dict, Any

import pytest

from smc_trading_agent.integration_example import run_integration_example


def _validate_signal(sig: Dict[str, Any]) -> None:
    # Required base fields
    assert "action" in sig and sig["action"] in {"BUY", "SELL"}
    assert "symbol" in sig and isinstance(sig["symbol"], str)
    assert "entry_price" in sig and isinstance(sig["entry_price"], (int, float))
    # Risk fields
    assert "stop_loss" in sig and "take_profit" in sig
    assert "position_size" in sig and sig["position_size"] >= 0
    assert "risk_reward_ratio" in sig and sig["risk_reward_ratio"] > 0


@pytest.mark.integration
def test_integration_example_runs_and_returns_summary():
    result = run_integration_example()

    # Basic shape
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "patterns_detected" in result
    assert "signals_generated" in result
    assert "signals" in result and isinstance(result["signals"], list)

    # If any signals were generated, validate structure of a few
    for sig in result["signals"][:5]:
        _validate_signal(sig)


