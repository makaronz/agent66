"""
Generate a simple data quality report and update Prometheus metric timestamp.
Usage:
  python tools/generate_data_quality_report.py --input path/to/data.csv --output report.json
"""

from __future__ import annotations

import argparse
import json
import time
import pandas as pd
from typing import Dict, Any

from smc_trading_agent.validators import data_validator
from smc_trading_agent.monitoring.data_quality_metrics import set_report_timestamp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    valid, errors = data_validator.validate_market_data(df)
    level = data_validator.assess_data_quality(df).value
    anomalies = data_validator.detect_data_anomalies(df)

    report: Dict[str, Any] = {
        'valid': valid,
        'errors': errors,
        'quality_level': level,
        'anomalies': anomalies,
        'generated_at': int(time.time())
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    set_report_timestamp(time.time())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


