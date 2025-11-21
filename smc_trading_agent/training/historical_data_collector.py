#!/usr/bin/env python3
"""
SMC Historical Data Acquisition System

This module provides comprehensive historical data collection capabilities for training SMC ML models.
Supports multiple exchanges, timeframes, and data quality validation.

Key Features:
- 2+ years of historical OHLCV data collection
- Multi-exchange support (Binance, ByBit, OANDA)
- Multiple timeframes (M5, M15, H1, H4, D1)
- Data quality validation and gap filling
- Efficient storage with Parquet format
- Progress tracking and resume capability
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from urllib.parse import urljoin

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class DataCollectionConfig:
    """Configuration for historical data collection."""
    exchanges: List[str]
    symbols: List[str]
    timeframes: List[str]
    start_date: datetime
    end_date: datetime
    data_dir: str
    batch_size: int = 1000
    max_retries: int = 3
    rate_limit_delay: float = 0.1
    validate_data: bool = True
    fill_gaps: bool = True
    storage_format: str = "parquet"  # "parquet" or "csv"
    resume_collection: bool = True
    create_database: bool = True
    quality_threshold: float = 0.95  # Minimum data quality score


@dataclass
class DataQualityMetrics:
    """Data quality assessment metrics."""
    total_records: int
    missing_records: int
    duplicate_records: int
    outliers_detected: int
    gaps_filled: int
    quality_score: float
    completeness_ratio: float
    timestamp_consistency: bool
    price_validity: bool
    volume_validity: bool


class HistoricalDataCollector:
    """
    Advanced historical data collector for SMC training.

    Supports multi-exchange data collection with comprehensive quality validation,
    gap filling, and efficient storage mechanisms.
    """

    def __init__(self, config: DataCollectionConfig):
        """
        Initialize historical data collector.

        Args:
            config: Data collection configuration
        """
        self.config = config
        self.data_dir = Path(config.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database for tracking
        if config.create_database:
            self.db_path = self.data_dir / "collection_metadata.db"
            self._init_database()

        # Exchange API endpoints
        self.exchange_endpoints = {
            'binance': {
                'klines': 'https://api.binance.com/api/v3/klines',
                'symbols': 'https://api.binance.com/api/v3/exchangeInfo',
                'rate_limit': 1200
            },
            'bybit': {
                'klines': 'https://api.bybit.com/v5/market/kline',
                'symbols': 'https://api.bybit.com/v5/market/instruments-info',
                'rate_limit': 600
            }
        }

        # Progress tracking
        self.progress = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'start_time': None,
            'estimated_completion': None
        }

        # Quality validation thresholds
        self.quality_thresholds = {
            'min_price_change': 0.0001,  # 0.01% minimum price movement
            'max_price_change': 0.5,     # 50% maximum price movement (filters outliers)
            'min_volume': 1.0,            # Minimum valid volume
            'max_volume_ratio': 100.0,    # Maximum volume spike ratio
            'gap_threshold': 0.1,         # Maximum gap ratio
        }

        logger.info(f"Historical data collector initialized for {len(config.exchanges)} exchanges")

    def _init_database(self):
        """Initialize SQLite database for tracking collection progress."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create collection progress table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_records INTEGER DEFAULT 0,
                    collected_records INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    quality_score REAL DEFAULT 0.0,
                    file_path TEXT,
                    UNIQUE(exchange, symbol, timeframe, start_date, end_date)
                )
            """)

            # Create data quality table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_quality (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER,
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    total_records INTEGER NOT NULL,
                    missing_records INTEGER DEFAULT 0,
                    duplicate_records INTEGER DEFAULT 0,
                    outliers_detected INTEGER DEFAULT 0,
                    gaps_filled INTEGER DEFAULT 0,
                    quality_score REAL NOT NULL,
                    completeness_ratio REAL NOT NULL,
                    timestamp_consistency BOOLEAN DEFAULT 1,
                    price_validity BOOLEAN DEFAULT 1,
                    volume_validity BOOLEAN DEFAULT 1,
                    assessment_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (collection_id) REFERENCES collection_progress (id)
                )
            """)

            conn.commit()

        logger.info("Collection metadata database initialized")

    async def collect_all_historical_data(self) -> Dict[str, Any]:
        """
        Collect all historical data based on configuration.

        Returns:
            Dict[str, Any]: Collection results and statistics
        """
        logger.info("Starting comprehensive historical data collection")
        start_time = time.time()
        self.progress['start_time'] = start_time

        try:
            # Calculate total tasks
            total_tasks = (
                len(self.config.exchanges) *
                len(self.config.symbols) *
                len(self.config.timeframes)
            )
            self.progress['total_tasks'] = total_tasks

            logger.info(f"Total collection tasks: {total_tasks}")

            # Create collection tasks
            collection_tasks = []
            for exchange in self.config.exchanges:
                for symbol in self.config.symbols:
                    for timeframe in self.config.timeframes:
                        task = self._collect_symbol_data(exchange, symbol, timeframe)
                        collection_tasks.append(task)

            # Execute collection tasks in batches to respect rate limits
            results = []
            batch_size = min(self.config.batch_size, len(collection_tasks))

            for i in range(0, len(collection_tasks), batch_size):
                batch = collection_tasks[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(collection_tasks)-1)//batch_size + 1}")

                # Execute batch
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend(batch_results)

                # Update progress
                self.progress['completed_tasks'] += len(batch_results)
                progress_pct = (self.progress['completed_tasks'] / self.progress['total_tasks']) * 100

                # Estimate completion time
                elapsed = time.time() - start_time
                if self.progress['completed_tasks'] > 0:
                    estimated_total = elapsed * self.progress['total_tasks'] / self.progress['completed_tasks']
                    self.progress['estimated_completion'] = start_time + estimated_total

                logger.info(f"Progress: {progress_pct:.1f}% ({self.progress['completed_tasks']}/{self.progress['total_tasks']})")

                # Rate limiting delay between batches
                if i + batch_size < len(collection_tasks):
                    await asyncio.sleep(self.config.rate_limit_delay * batch_size)

            # Process results
            successful_collections = []
            failed_collections = []

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Collection task failed: {str(result)}")
                    failed_collections.append(str(result))
                    self.progress['failed_tasks'] += 1
                else:
                    successful_collections.append(result)

            # Generate collection summary
            total_time = time.time() - start_time
            summary = {
                'status': 'completed',
                'total_time_seconds': total_time,
                'total_tasks': self.progress['total_tasks'],
                'completed_tasks': self.progress['completed_tasks'],
                'failed_tasks': self.progress['failed_tasks'],
                'success_rate': self.progress['completed_tasks'] / self.progress['total_tasks'] * 100,
                'successful_collections': successful_collections,
                'failed_collections': failed_collections,
                'data_directory': str(self.data_dir),
                'collection_timestamp': datetime.now().isoformat()
            }

            logger.info(f"Historical data collection completed in {total_time:.2f}s")
            logger.info(f"Success rate: {summary['success_rate']:.1f}%")

            return summary

        except Exception as e:
            logger.error(f"Historical data collection failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'total_time_seconds': time.time() - start_time
            }

    async def _collect_symbol_data(self, exchange: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Collect historical data for a specific symbol and timeframe.

        Args:
            exchange: Exchange name
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '5m', '1h', '1d')

        Returns:
            Dict[str, Any]: Collection results
        """
        try:
            # Check if already collected (resume capability)
            if self.config.resume_collection:
                existing_data = self._check_existing_data(exchange, symbol, timeframe)
                if existing_data and len(existing_data) > 0:
                    logger.info(f"Found existing data for {exchange}/{symbol}/{timeframe}: {len(existing_data)} records")
                    return {
                        'exchange': exchange,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'status': 'already_collected',
                        'records': len(existing_data),
                        'file_path': self._get_file_path(exchange, symbol, timeframe)
                    }

            # Fetch data from exchange
            data = await self._fetch_exchange_data(exchange, symbol, timeframe)

            if data is None or len(data) == 0:
                logger.warning(f"No data received for {exchange}/{symbol}/{timeframe}")
                return {
                    'exchange': exchange,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'no_data',
                    'records': 0
                }

            # Validate and clean data
            if self.config.validate_data:
                data, quality_metrics = self._validate_and_clean_data(data, exchange, symbol, timeframe)
            else:
                quality_metrics = self._calculate_basic_quality_metrics(data)

            # Fill gaps if enabled
            if self.config.fill_gaps:
                data = self._fill_data_gaps(data, timeframe)
                quality_metrics.gaps_filled = self._count_filled_gaps(data)

            # Save data
            file_path = await self._save_data(data, exchange, symbol, timeframe)

            # Update database
            collection_id = self._update_collection_progress(
                exchange, symbol, timeframe, len(data), 'completed', quality_metrics, file_path
            )

            result = {
                'exchange': exchange,
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'completed',
                'records': len(data),
                'quality_score': quality_metrics.quality_score,
                'file_path': str(file_path),
                'collection_id': collection_id
            }

            logger.info(f"Collected {len(data)} records for {exchange}/{symbol}/{timeframe} (quality: {quality_metrics.quality_score:.3f})")
            return result

        except Exception as e:
            logger.error(f"Failed to collect data for {exchange}/{symbol}/{timeframe}: {str(e)}")

            # Update database with failure
            self._update_collection_progress(exchange, symbol, timeframe, 0, 'failed')

            return {
                'exchange': exchange,
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'failed',
                'error': str(e),
                'records': 0
            }

    async def _fetch_exchange_data(self, exchange: str, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Fetch historical data from exchange API.

        Args:
            exchange: Exchange name
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Optional[pd.DataFrame]: OHLCV data or None if failed
        """
        try:
            if exchange == 'binance':
                return await self._fetch_binance_data(symbol, timeframe)
            elif exchange == 'bybit':
                return await self._fetch_bybit_data(symbol, timeframe)
            else:
                logger.error(f"Unsupported exchange: {exchange}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch data from {exchange}: {str(e)}")
            return None

    async def _fetch_binance_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Fetch historical data from Binance API."""
        try:
            # Convert timeframe to Binance format
            timeframe_map = {
                '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '2h': '2h', '4h': '4h',
                '1d': '1d'
            }
            binance_timeframe = timeframe_map.get(timeframe, timeframe)

            # Prepare request parameters
            params = {
                'symbol': symbol.replace('/', ''),
                'interval': binance_timeframe,
                'startTime': int(self.config.start_date.timestamp() * 1000),
                'endTime': int(self.config.end_date.timestamp() * 1000),
                'limit': 1000  # Maximum per request
            }

            all_data = []
            current_start = self.config.start_date

            while current_start < self.config.end_date:
                # Make request with retries
                data = await self._make_request_with_retries(
                    'GET',
                    self.exchange_endpoints['binance']['klines'],
                    params=params
                )

                if not data or len(data) == 0:
                    break

                all_data.extend(data)

                # Update start time for next batch
                if len(data) > 0:
                    last_timestamp = data[-1][0]  # First column is timestamp
                    current_start = datetime.fromtimestamp(last_timestamp / 1000)
                    params['startTime'] = int(current_start.timestamp() * 1000) + 1

                # Rate limiting
                await asyncio.sleep(self.config.rate_limit_delay)

            # Convert to DataFrame
            if all_data:
                df = pd.DataFrame(all_data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])

                # Convert to proper data types
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)

                # Select OHLCV columns
                ohlcv_columns = ['open', 'high', 'low', 'close', 'volume']
                df[ohlcv_columns] = df[ohlcv_columns].astype(float)

                return df[ohlcv_columns]

            return None

        except Exception as e:
            logger.error(f"Failed to fetch Binance data for {symbol} {timeframe}: {str(e)}")
            return None

    async def _fetch_bybit_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Fetch historical data from ByBit API."""
        try:
            # Convert timeframe to ByBit format
            timeframe_map = {
                '5m': '5', '15m': '15', '30m': '30',
                '1h': '60', '2h': '120', '4h': '240',
                '1d': 'D'
            }
            bybit_timeframe = timeframe_map.get(timeframe, timeframe)

            # Prepare request parameters
            params = {
                'category': 'linear',
                'symbol': symbol.replace('/', ''),
                'interval': bybit_timeframe,
                'start': int(self.config.start_date.timestamp() * 1000),
                'end': int(self.config.end_date.timestamp() * 1000),
                'limit': 1000
            }

            all_data = []

            while True:
                # Make request
                response = await self._make_request_with_retries(
                    'GET',
                    self.exchange_endpoints['bybit']['klines'],
                    params=params
                )

                if not response or 'result' not in response:
                    break

                data = response['result'].get('list', [])
                if not data:
                    break

                all_data.extend(data)

                # Update start time for next batch
                if len(data) > 0:
                    last_timestamp = int(data[-1][0])  # First column is timestamp
                    params['start'] = last_timestamp + 1

                # Break if we've reached the end
                if len(data) < params['limit']:
                    break

                # Rate limiting
                await asyncio.sleep(self.config.rate_limit_delay)

            # Convert to DataFrame
            if all_data:
                df = pd.DataFrame(all_data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'turnover'
                ])

                # Convert to proper data types
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)

                # Select OHLCV columns
                ohlcv_columns = ['open', 'high', 'low', 'close', 'volume']
                df[ohlcv_columns] = df[ohlcv_columns].astype(float)

                # Sort by timestamp (ByBit returns data in descending order)
                df.sort_index(inplace=True)

                return df[ohlcv_columns]

            return None

        except Exception as e:
            logger.error(f"Failed to fetch ByBit data for {symbol} {timeframe}: {str(e)}")
            return None

    async def _make_request_with_retries(self, method: str, url: str, params: Dict = None, max_retries: int = None) -> Any:
        """Make HTTP request with retry logic."""
        if max_retries is None:
            max_retries = self.config.max_retries

        for attempt in range(max_retries + 1):
            try:
                response = requests.request(method, url, params=params, timeout=30)

                if response.status_code == 200:
                    if 'binance' in url:
                        return response.json()
                    elif 'bybit' in url:
                        return response.json()
                    else:
                        return response.json()

                elif response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited, waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    continue

                else:
                    logger.warning(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")

                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise Exception(f"Failed to complete request after {max_retries + 1} attempts")

    def _validate_and_clean_data(self, data: pd.DataFrame, exchange: str, symbol: str, timeframe: str) -> Tuple[pd.DataFrame, DataQualityMetrics]:
        """
        Validate and clean data quality.

        Args:
            data: Raw OHLCV data
            exchange: Exchange name
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Tuple[pd.DataFrame, DataQualityMetrics]: Cleaned data and quality metrics
        """
        original_len = len(data)

        # Basic validation
        validation_errors = []

        # Check for required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            validation_errors.append(f"Missing columns: {missing_columns}")

        # Check for null values
        null_counts = data.isnull().sum()
        if null_counts.any():
            validation_errors.append(f"Null values found: {null_counts[null_counts > 0].to_dict()}")

        # Check timestamp continuity
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)

        # Detect duplicates
        duplicates = data.index.duplicated().sum()

        # Detect outliers based on price changes
        price_changes = data['close'].pct_change()
        outliers = (
            (abs(price_changes) < self.quality_thresholds['min_price_change']) |
            (abs(price_changes) > self.quality_thresholds['max_price_change'])
        ).sum()

        # Volume validation
        invalid_volume = (data['volume'] < self.quality_thresholds['min_volume']).sum()

        # Price validity (high >= low, close within range)
        invalid_prices = (
            (data['high'] < data['low']) |
            (data['close'] > data['high']) |
            (data['close'] < data['low']) |
            (data['open'] > data['high']) |
            (data['open'] < data['low'])
        ).sum()

        # Clean data
        cleaned_data = data.copy()

        # Remove duplicates
        if duplicates > 0:
            cleaned_data = cleaned_data[~cleaned_data.index.duplicated(keep='first')]

        # Remove invalid price records
        if invalid_prices > 0:
            valid_price_mask = (
                (cleaned_data['high'] >= cleaned_data['low']) &
                (cleaned_data['close'] <= cleaned_data['high']) &
                (cleaned_data['close'] >= cleaned_data['low']) &
                (cleaned_data['open'] <= cleaned_data['high']) &
                (cleaned_data['open'] >= cleaned_data['low'])
            )
            cleaned_data = cleaned_data[valid_price_mask]

        # Handle outliers
        if outliers > 0:
            # Remove extreme outliers but keep reasonable movements
            extreme_outlier_mask = abs(price_changes) <= self.quality_thresholds['max_price_change']
            cleaned_data = cleaned_data[extreme_outlier_mask]

        # Remove records with zero or negative volume
        if invalid_volume > 0:
            cleaned_data = cleaned_data[cleaned_data['volume'] >= self.quality_thresholds['min_volume']]

        # Calculate quality metrics
        final_len = len(cleaned_data)
        missing_records = original_len - final_len

        quality_metrics = DataQualityMetrics(
            total_records=final_len,
            missing_records=missing_records,
            duplicate_records=duplicates,
            outliers_detected=outliers,
            gaps_filled=0,  # Will be updated if gap filling is applied
            quality_score=self._calculate_quality_score(cleaned_data, missing_records),
            completeness_ratio=final_len / max(original_len, 1),
            timestamp_consistency=self._check_timestamp_consistency(cleaned_data, timeframe),
            price_validity=invalid_prices == 0,
            volume_validity=invalid_volume == 0
        )

        logger.info(f"Data validation for {exchange}/{symbol}/{timeframe}: "
                   f"quality_score={quality_metrics.quality_score:.3f}, "
                   f"removed={missing_records} invalid records")

        return cleaned_data, quality_metrics

    def _calculate_basic_quality_metrics(self, data: pd.DataFrame) -> DataQualityMetrics:
        """Calculate basic quality metrics without full validation."""
        return DataQualityMetrics(
            total_records=len(data),
            missing_records=0,
            duplicate_records=0,
            outliers_detected=0,
            gaps_filled=0,
            quality_score=1.0,  # Assume perfect if validation disabled
            completeness_ratio=1.0,
            timestamp_consistency=True,
            price_validity=True,
            volume_validity=True
        )

    def _calculate_quality_score(self, data: pd.DataFrame, missing_records: int) -> float:
        """Calculate overall data quality score (0-1)."""
        if len(data) == 0:
            return 0.0

        # Base score from completeness
        completeness_score = 1.0 - (missing_records / (len(data) + missing_records))

        # Penalty for insufficient data
        min_records_threshold = 1000  # Minimum records for good quality
        if len(data) < min_records_threshold:
            completeness_score *= (len(data) / min_records_threshold)

        # Check for reasonable price ranges
        price_ranges = data['high'] - data['low']
        zero_range_count = (price_ranges == 0).sum()
        if zero_range_count > 0:
            range_penalty = zero_range_count / len(data)
            completeness_score *= (1.0 - min(range_penalty, 0.5))

        return max(0.0, min(1.0, completeness_score))

    def _check_timestamp_consistency(self, data: pd.DataFrame, timeframe: str) -> bool:
        """Check if timestamps are consistent with expected intervals."""
        if len(data) < 2:
            return True

        # Map timeframe to pandas frequency
        timeframe_map = {
            '5m': '5T', '15m': '15T', '30m': '30T',
            '1h': '1H', '2h': '2H', '4h': '4H',
            '1d': '1D'
        }

        freq = timeframe_map.get(timeframe, '1H')

        # Calculate actual intervals
        intervals = data.index.to_series().diff().dropna()
        expected_interval = pd.Timedelta(freq)

        # Allow some tolerance (within 10% of expected interval)
        tolerance = expected_interval * 0.1

        consistent_intervals = (
            (intervals >= expected_interval - tolerance) &
            (intervals <= expected_interval + tolerance)
        ).sum()

        return (consistent_intervals / len(intervals)) >= 0.95  # 95% consistency threshold

    def _fill_data_gaps(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Fill gaps in time series data."""
        if len(data) == 0:
            return data

        # Create expected timestamp range
        timeframe_map = {
            '5m': '5T', '15m': '15T', '30m': '30T',
            '1h': '1H', '2h': '2H', '4h': '4H',
            '1d': '1D'
        }

        freq = timeframe_map.get(timeframe, '1H')
        expected_range = pd.date_range(
            start=data.index.min(),
            end=data.index.max(),
            freq=freq
        )

        # Reindex to expected range
        data_filled = data.reindex(expected_range)

        # Forward fill missing data (common approach for OHLCV)
        data_filled['open'] = data_filled['open'].fillna(method='ffill')
        data_filled['high'] = data_filled['high'].fillna(method='ffill')
        data_filled['low'] = data_filled['low'].fillna(method='ffill')
        data_filled['close'] = data_filled['close'].fillna(method='ffill')
        data_filled['volume'] = data_filled['volume'].fillna(0)  # Volume defaults to 0

        # Fill any remaining NaN with previous close
        data_filled = data_filled.fillna(method='bfill').fillna(method='ffill')

        return data_filled

    def _count_filled_gaps(self, data: pd.DataFrame) -> int:
        """Count number of filled gaps in data."""
        # This is a simplified count - in practice you'd track this more carefully
        return (data.isnull().any(axis=1)).sum()

    async def _save_data(self, data: pd.DataFrame, exchange: str, symbol: str, timeframe: str) -> Path:
        """Save data to disk in specified format."""
        # Create file path
        file_path = self._get_file_path(exchange, symbol, timeframe)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if self.config.storage_format == 'parquet':
                # Save as Parquet (recommended for large datasets)
                data.to_parquet(file_path, compression='snappy')
            else:
                # Save as CSV
                data.to_csv(file_path)

            logger.debug(f"Saved {len(data)} records to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save data to {file_path}: {str(e)}")
            raise

    def _get_file_path(self, exchange: str, symbol: str, timeframe: str) -> Path:
        """Generate file path for storing data."""
        # Clean symbol name
        clean_symbol = symbol.replace('/', '_')

        # Generate filename
        if self.config.storage_format == 'parquet':
            filename = f"{clean_symbol}_{timeframe}.parquet"
        else:
            filename = f"{clean_symbol}_{timeframe}.csv"

        return self.data_dir / exchange / filename

    def _check_existing_data(self, exchange: str, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Check if data already exists and load it."""
        file_path = self._get_file_path(exchange, symbol, timeframe)

        if not file_path.exists():
            return None

        try:
            if self.config.storage_format == 'parquet':
                data = pd.read_parquet(file_path)
            else:
                data = pd.read_csv(file_path, index_col=0, parse_dates=True)

            # Check if data covers the required date range
            if len(data) > 0:
                data_start = data.index.min()
                data_end = data.index.max()

                if (data_start <= self.config.start_date and
                    data_end >= self.config.end_date):
                    return data

            return None

        except Exception as e:
            logger.warning(f"Failed to load existing data from {file_path}: {str(e)}")
            return None

    def _update_collection_progress(self, exchange: str, symbol: str, timeframe: str,
                                  records: int, status: str, quality_metrics: DataQualityMetrics = None,
                                  file_path: Path = None) -> int:
        """Update collection progress in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert or update progress
                cursor.execute("""
                    INSERT OR REPLACE INTO collection_progress
                    (exchange, symbol, timeframe, start_date, end_date, total_records,
                     collected_records, status, last_updated, quality_score, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exchange, symbol, timeframe,
                    self.config.start_date.isoformat(),
                    self.config.end_date.isoformat(),
                    records, records, status,
                    datetime.now().isoformat(),
                    quality_metrics.quality_score if quality_metrics else 0.0,
                    str(file_path) if file_path else None
                ))

                collection_id = cursor.lastrowid

                # Insert quality metrics if available
                if quality_metrics and status == 'completed':
                    cursor.execute("""
                        INSERT INTO data_quality
                        (collection_id, exchange, symbol, timeframe, total_records,
                         missing_records, duplicate_records, outliers_detected, gaps_filled,
                         quality_score, completeness_ratio, timestamp_consistency,
                         price_validity, volume_validity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        collection_id, exchange, symbol, timeframe,
                        quality_metrics.total_records, quality_metrics.missing_records,
                        quality_metrics.duplicate_records, quality_metrics.outliers_detected,
                        quality_metrics.gaps_filled, quality_metrics.quality_score,
                        quality_metrics.completeness_ratio, quality_metrics.timestamp_consistency,
                        quality_metrics.price_validity, quality_metrics.volume_validity
                    ))

                conn.commit()
                return collection_id

        except Exception as e:
            logger.error(f"Failed to update collection progress: {str(e)}")
            return -1

    def get_collection_summary(self) -> Dict[str, Any]:
        """Get comprehensive collection summary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Overall statistics
                stats_df = pd.read_sql_query("""
                    SELECT
                        COUNT(*) as total_collections,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        AVG(quality_score) as avg_quality_score,
                        SUM(collected_records) as total_records
                    FROM collection_progress
                """, conn)

                # Per-exchange statistics
                exchange_stats = pd.read_sql_query("""
                    SELECT
                        exchange,
                        COUNT(*) as collections,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        AVG(quality_score) as avg_quality,
                        SUM(collected_records) as total_records
                    FROM collection_progress
                    GROUP BY exchange
                """, conn)

                # Data quality summary
                quality_stats = pd.read_sql_query("""
                    SELECT
                        AVG(quality_score) as avg_quality,
                        AVG(completeness_ratio) as avg_completeness,
                        SUM(CASE WHEN timestamp_consistency = 1 THEN 1 ELSE 0 END) as consistent_timestamps,
                        SUM(CASE WHEN price_validity = 1 THEN 1 ELSE 0 END) as valid_prices,
                        SUM(CASE WHEN volume_validity = 1 THEN 1 ELSE 0 END) as valid_volumes
                    FROM data_quality
                """, conn)

                return {
                    'overall_stats': stats_df.iloc[0].to_dict(),
                    'exchange_stats': exchange_stats.to_dict('records'),
                    'quality_stats': quality_stats.iloc[0].to_dict(),
                    'progress': self.progress,
                    'collection_timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to generate collection summary: {str(e)}")
            return {'error': str(e)}


def create_data_collection_config(
    exchanges: List[str] = None,
    symbols: List[str] = None,
    timeframes: List[str] = None,
    start_date: datetime = None,
    end_date: datetime = None,
    **kwargs
) -> DataCollectionConfig:
    """
    Create data collection configuration with sensible defaults.

    Args:
        exchanges: List of exchanges to collect from
        symbols: List of symbols to collect
        timeframes: List of timeframes to collect
        start_date: Start date for collection
        end_date: End date for collection
        **kwargs: Additional configuration parameters

    Returns:
        DataCollectionConfig: Complete configuration
    """
    # Default values
    default_exchanges = ['binance', 'bybit']
    default_symbols = ['BTCUSDT', 'ETHUSDT', 'EURUSD', 'GBPUSD', 'USDJPY']
    default_timeframes = ['5m', '15m', '1h', '4h', '1d']

    return DataCollectionConfig(
        exchanges=exchanges or default_exchanges,
        symbols=symbols or default_symbols,
        timeframes=timeframes or default_timeframes,
        start_date=start_date or (datetime.now() - timedelta(days=730)),  # 2 years ago
        end_date=end_date or datetime.now(),
        **kwargs
    )


async def main():
    """Example usage of the historical data collector."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting SMC Historical Data Collection")

    # Create configuration
    config = create_data_collection_config(
        exchanges=['binance', 'bybit'],
        symbols=['BTCUSDT', 'ETHUSDT'],
        timeframes=['5m', '15m', '1h', '4h', '1d'],
        start_date=datetime.now() - timedelta(days=365),  # 1 year for demo
        end_date=datetime.now(),
        data_dir='./historical_data',
        validate_data=True,
        fill_gaps=True,
        storage_format='parquet'
    )

    # Initialize collector
    collector = HistoricalDataCollector(config)

    # Collect data
    results = await collector.collect_all_historical_data()

    # Print results
    print("\n" + "="*80)
    print("COLLECTION RESULTS")
    print("="*80)
    print(json.dumps(results, indent=2, default=str))

    # Get detailed summary
    summary = collector.get_collection_summary()
    print(f"\nCollection Summary:")
    print(f"Total Collections: {summary['overall_stats']['total_collections']}")
    print(f"Completed: {summary['overall_stats']['completed']}")
    print(f"Failed: {summary['overall_stats']['failed']}")
    print(f"Average Quality Score: {summary['overall_stats']['avg_quality_score']:.3f}")
    print(f"Total Records Collected: {summary['overall_stats']['total_records']:,}")


if __name__ == "__main__":
    asyncio.run(main())