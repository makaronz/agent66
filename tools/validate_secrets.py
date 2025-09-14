"""
Simple CLI to validate presence of required Vault-managed secrets
in local/dev or inside a pod with Vault Agent injection.

Usage:
  python tools/validate_secrets.py --paths /vault/secrets/database:/vault/secrets/exchanges:/vault/secrets/jwt
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List


def parse_env_file(path: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                values[k] = v
    return values


def validate(paths: List[str]) -> int:
    required_keys = {
        "/vault/secrets/database": ["DATABASE_URL", "DATABASE_PASSWORD"],
        "/vault/secrets/exchanges": [
            "BINANCE_API_KEY",
            "BINANCE_API_SECRET",
            # add BYBIT/OANDA if needed when split per file
        ],
        "/vault/secrets/jwt": ["JWT_SECRET", "ENCRYPTION_KEY"],
    }

    ok = True
    for path in paths:
        if not os.path.exists(path):
            print(f"MISSING FILE: {path}")
            ok = False
            continue
        data = parse_env_file(path)
        for key in required_keys.get(path, []):
            if not data.get(key):
                print(f"MISSING KEY {key} in {path}")
                ok = False
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--paths",
        default="/vault/secrets/database:/vault/secrets/exchanges:/vault/secrets/jwt",
        help="Colon-separated list of files to validate",
    )
    args = parser.parse_args()
    paths = args.paths.split(":")
    return validate(paths)


if __name__ == "__main__":
    sys.exit(main())


