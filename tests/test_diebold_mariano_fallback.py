import sys
import asyncio
import numpy as np
import pytest

from training.validation.statistical_tests import diebold_mariano as dm


def test_calculate_autocorr_adjusted_variance_fallback_without_statsmodels(monkeypatch):
    # Simulate absence of statsmodels in the environment
    monkeypatch.setitem(sys.modules, 'statsmodels', None)

    # Force the module-level flag to ensure fallback path
    monkeypatch.setattr(dm, 'HAS_STATSMODELS', False, raising=True)

    # Spy on the simple autocorr test to ensure it is used
    call_counter = {"count": 0}

    def fake_simple_autocorr(self, data):
        call_counter["count"] += 1
        # Return False to follow the simple variance branch and avoid Newey–West
        return False

    monkeypatch.setattr(dm.DieboldMarianoTest, '_simple_autocorr_test', fake_simple_autocorr, raising=True)

    # Prepare synthetic loss differential with n >= 10
    rng = np.random.default_rng(42)
    loss_diff = rng.normal(loc=0.0, scale=1.0, size=32)
    mean_diff = float(np.mean(loss_diff))

    tester = dm.DieboldMarianoTest({
        'significance_level': 0.05,
        'autocorr_adjustment': True,
        'max_lags': 10,
        'min_sample_size': 10,
    })

    # Should not raise and should use the fallback
    var_diff, dof = asyncio.run(
        tester._calculate_autocorr_adjusted_variance(loss_diff, mean_diff)
    )

    assert call_counter["count"] == 1
    assert isinstance(var_diff, float)
    assert isinstance(dof, int)


