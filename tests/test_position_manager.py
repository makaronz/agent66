"""
Component-focused tests for PositionManager.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch

from ..risk_manager.position_manager import PositionManager, Position, ClosureResult


class TestPositionManager:
    """Test position manager functionality."""

    @pytest.mark.asyncio
    async def test_position_discovery(self, mock_config, mock_exchange_connectors):
        manager = PositionManager(mock_config['position_manager'], mock_exchange_connectors)

        positions = await manager.discover_all_positions()

        assert len(positions) > 0
        for position_id, position in positions.items():
            assert isinstance(position, Position)
            assert position.exchange in ['binance', 'bybit']
            assert position.size > 0

    @pytest.mark.asyncio
    async def test_position_closure(self, mock_config, mock_exchange_connectors):
        manager = PositionManager(mock_config['position_manager'], mock_exchange_connectors)

        # Mock successful closure
        with patch.object(manager, '_execute_position_closure', new_callable=AsyncMock) as mock_closure:
            mock_closure.return_value = ClosureResult(
                exchange='binance',
                symbol='BTCUSDT',
                success=True,
                closed_size=1.0,
                closure_price=51000,
                timestamp=time.time()
            )

            closure_results = await manager.close_all_positions("Test closure")

            assert len(closure_results) > 0
            for result in closure_results:
                assert isinstance(result, ClosureResult)

    @pytest.mark.asyncio
    async def test_closure_validation(self, mock_config, mock_exchange_connectors):
        manager = PositionManager(mock_config['position_manager'], mock_exchange_connectors)

        successful_results = [
            ClosureResult(
                exchange='binance',
                symbol='BTCUSDT',
                success=True,
                closed_size=1.0,
                closure_price=51000,
                timestamp=time.time()
            )
        ]

        is_valid = await manager.validate_position_closure(successful_results)
        assert is_valid is True


