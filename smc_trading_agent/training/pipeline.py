# smc_trading_agent/training/pipeline.py

"""
This module contains the functions for building and evaluating the trading model training pipeline.
It includes custom time-series cross-validation, walk-forward backtesting,
and performance evaluation metrics.
"""

import numpy as np
import pandas as pd
import quantstats as qs
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler


def create_strict_time_series_split(data, n_splits=5, gap=0):
    """
    Creates a time-series cross-validator that enforces a gap between train and test sets.

    This function is a wrapper around scikit-learn's TimeSeriesSplit but is designed
    to make the gap parameter explicit and central to its use, preventing data leakage
    from features engineered with lookaheads (e.g., rolling means).

    Args:
        data (pd.DataFrame or np.ndarray): The dataset to be split.
        n_splits (int): The number of splits to generate.
        gap (int): The number of samples to exclude between the end of the training set
                   and the beginning of the test set.

    Yields:
        tuple: A tuple containing the training and testing indices for each split.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    for train_index, test_index in tscv.split(data):
        yield train_index, test_index


def walk_forward_backtest(model, X, y, n_splits=5, gap=0):
    """
    Performs a walk-forward backtest of a given model.

    This function simulates how a model would perform in a real-world scenario by
    iteratively training on past data and testing on future data. It includes
    data preprocessing within each fold to prevent data leakage.

    Args:
        model: A scikit-learn compatible model instance.
        X (pd.DataFrame): The feature dataset.
        y (pd.Series): The target variable.
        n_splits (int): The number of splits for the time-series cross-validation.
        gap (int): The gap between training and testing sets in each fold.

    Returns:
        dict: A dictionary containing performance metrics from the backtest.
    """
    all_preds = []
    all_true_indices = []

    cv_splitter = create_strict_time_series_split(X, n_splits=n_splits, gap=gap)

    for fold, (train_index, test_index) in enumerate(cv_splitter):
        print(f"--- Fold {fold+1}/{n_splits} ---")
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        print(f"Training on {len(X_train)} samples...")
        model.fit(X_train_scaled, y_train)
        
        print(f"Testing on {len(X_test)} samples...")
        preds = model.predict(X_test_scaled)
        
        all_preds.append(preds)
        all_true_indices.extend(test_index)

    # Align predictions with original index
    final_preds = pd.Series(np.concatenate(all_preds), index=X.iloc[all_true_indices].index)
    final_true = y.loc[final_preds.index]

    # Assume predictions are signals (+1 for buy, -1 for sell, 0 for hold)
    # This is a simplified assumption. A real implementation would be more complex.
    # We calculate returns based on the signal and the true next-period price change.
    returns = final_true.pct_change().shift(-1) * final_preds
    returns = returns.fillna(0)
    
    return calculate_performance_metrics(returns)


def calculate_performance_metrics(returns):
    """
    Calculates key performance metrics for a trading strategy using quantstats.

    Args:
        returns (pd.Series): A pandas Series of portfolio returns for each period.

    Returns:
        dict: A dictionary of performance metrics.
    """
    print("\nCalculating performance metrics...")
    
    # Ensure returns is a pandas Series
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns)

    qs.extend_pandas()

    metrics = {
        "Sharpe Ratio": returns.sharpe(),
        "Sortino Ratio": returns.sortino(),
        "Max Drawdown [%]": returns.max_drawdown() * 100,
        "Calmar Ratio": returns.calmar(),
        "CAGR [%]": returns.cagr() * 100,
        "Win Rate [%]": returns.win_rate() * 100,
        "Cumulative Returns": returns.cumsum().iloc[-1]
    }
    
    # Generate and print a concise report
    qs.reports.metrics(returns, mode='basic')

    return metrics
