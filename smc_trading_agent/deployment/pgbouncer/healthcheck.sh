#!/bin/bash

# PgBouncer health check script
# Checks if PgBouncer is responding and can connect to databases

set -e

# Check if PgBouncer is listening on port 6432
if ! nc -z localhost 6432; then
    echo "ERROR: PgBouncer is not listening on port 6432"
    exit 1
fi

# Try to connect to PgBouncer admin interface
if ! echo "SHOW POOLS;" | psql -h localhost -p 6432 -U postgres -d pgbouncer -t > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to PgBouncer admin interface"
    exit 1
fi

# Check pool status
POOL_STATUS=$(echo "SHOW POOLS;" | psql -h localhost -p 6432 -U postgres -d pgbouncer -t 2>/dev/null | grep -c "smc_trading_agent" || echo "0")

if [ "$POOL_STATUS" -eq 0 ]; then
    echo "ERROR: No active pools found"
    exit 1
fi

echo "PgBouncer health check passed"
exit 0