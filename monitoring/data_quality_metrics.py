from prometheus_client import Counter, Gauge


# Counters for data quality errors and anomalies
data_quality_errors_total = Counter(
    'data_quality_errors_total',
    'Total number of data quality validation errors',
    ['component', 'error_type']
)

data_anomalies_total = Counter(
    'data_anomalies_total',
    'Total number of detected data anomalies',
    ['anomaly_type']
)

# Gauge for data freshness (seconds since last update)
data_freshness_seconds = Gauge(
    'data_freshness_seconds',
    'Data freshness in seconds (age of latest datapoint)',
    ['exchange', 'symbol']
)

# Timestamp of the last generated data quality report
data_quality_report_timestamp = Gauge(
    'data_quality_report_timestamp',
    'Unix timestamp when the last data quality report was generated'
)


def inc_quality_error(component: str, error_type: str, amount: int = 1) -> None:
    data_quality_errors_total.labels(component=component, error_type=error_type).inc(amount)


def inc_anomaly(anomaly_type: str, amount: int = 1) -> None:
    data_anomalies_total.labels(anomaly_type=anomaly_type).inc(amount)


def set_freshness(exchange: str, symbol: str, seconds: float) -> None:
    data_freshness_seconds.labels(exchange=exchange, symbol=symbol).set(seconds)


def set_report_timestamp(ts: float) -> None:
    data_quality_report_timestamp.set(ts)


