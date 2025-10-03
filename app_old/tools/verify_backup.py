"""
Verify database backups by connecting and checking latest backup timestamp and size.
Usage:
  python tools/verify_backup.py --dsn "postgresql://user:pass@host:5432/db" --min-age-hours 1
"""

from __future__ import annotations

import argparse
import time
import psycopg2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', required=True)
    parser.add_argument('--min-age-hours', type=int, default=1)
    args = parser.parse_args()

    try:
        with psycopg2.connect(args.dsn) as conn:
            with conn.cursor() as cur:
                # Example verification table populated by backup job (customize if needed)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS backup_audit (
                        id serial PRIMARY KEY,
                        backup_time timestamptz NOT NULL DEFAULT now(),
                        backup_size_bytes bigint DEFAULT 0
                    );
                """)
                conn.commit()

                cur.execute("SELECT backup_time, backup_size_bytes FROM backup_audit ORDER BY backup_time DESC LIMIT 1")
                row = cur.fetchone()
                if not row:
                    print("NO_BACKUP_RECORD")
                    return 2

                backup_time, size_bytes = row
                age_hours = (time.time() - backup_time.timestamp()) / 3600
                if age_hours > args.min_age_hours:
                    print(f"BACKUP_TOO_OLD age_hours={age_hours:.2f} size={size_bytes}")
                    return 3

                if size_bytes is not None and size_bytes <= 0:
                    print("BACKUP_SIZE_ZERO")
                    return 4

                print(f"BACKUP_OK age_hours={age_hours:.2f} size={size_bytes}")
                return 0
    except Exception as e:
        print(f"BACKUP_VERIFY_ERROR {e}")
        return 5


if __name__ == '__main__':
    raise SystemExit(main())


