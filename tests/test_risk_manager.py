import pytest
import yaml
from risk_manager.smc_risk_manager import SMCRiskManager

@pytest.fixture
def create_test_risk_config(tmp_path):
    config_content = """
risk_manager:
  max_position_size: 10000
  max_daily_loss: 1000
  max_drawdown: 0.05
  circuit_breaker_threshold: 0.1
  position_limits:
    BTCUSDT: 1.0
    default: 500.0
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)

def test_risk_manager_initialization(create_test_risk_config):
    """Test that the risk manager initializes correctly from a config file."""
    rm = SMCRiskManager(config_path=create_test_risk_config)
    assert rm.max_position_size == 10000
    assert rm.position_limits['BTCUSDT'] == 1.0

def test_assess_trade_risk_safe(create_test_risk_config):
    """Test a trade that should pass all risk checks."""
    rm = SMCRiskManager(config_path=create_test_risk_config)
    is_safe, message = rm.assess_trade_risk(
        symbol='ETHUSDT',
        size=400,
        current_loss=500,
        current_drawdown=0.03,
        market_change=0.05
    )
    assert is_safe is True

def test_assess_trade_risk_unsafe_size(create_test_risk_config):
    """Test a trade that fails the position size check."""
    rm = SMCRiskManager(config_path=create_test_risk_config)
    is_safe, message = rm.assess_trade_risk(
        symbol='BTCUSDT',
        size=1.5,
        current_loss=100,
        current_drawdown=0.01,
        market_change=0.01
    )
    assert is_safe is False
    assert "exceeds limit" in message