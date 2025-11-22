# SMC Trading Agent Production Operations Manual

This comprehensive operations manual provides guidelines for running, maintaining, and troubleshooting the SMC Trading Agent in production environments.

## Table of Contents

1. [System Overview](#system-overview)
2. [Daily Operations](#daily-operations)
3. [Monitoring and Alerting](#monitoring-and-alerting)
4. [Performance Management](#performance-management)
5. [Security Operations](#security-operations)
6. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
7. [Maintenance Procedures](#maintenance-procedures)
8. [Incident Management](#incident-management)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Capacity Planning](#capacity-planning)
11. [Compliance and Auditing](#compliance-and-auditing)

## System Overview

### Architecture Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Load Balancer │
│   (React)       │────│   (Nginx)       │────│   (HAProxy)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │   Trading    │ │   Risk      │ │ Monitoring │
        │   Engine     │ │   Manager   │ │   Stack    │
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │ PostgreSQL   │ │    Redis    │ │  Kafka     │
        │ (TimescaleDB)│ │  (Cache)    │ │ (Events)   │
        └──────────────┘ └─────────────┘ └────────────┘
```

### Key Services

**Core Services:**
- **Trading Engine**: Processes trades and manages positions
- **Risk Manager**: Monitors risk parameters and enforces limits
- **Data Pipeline**: Ingests and processes market data
- **API Server**: Provides REST and WebSocket APIs
- **WebSocket Manager**: Handles real-time data streaming

**Supporting Services:**
- **PostgreSQL**: Primary database with TimescaleDB extension
- **Redis**: Caching and session storage
- **Kafka**: Event streaming and message queuing
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and alerting

### Service Dependencies

```
Trading Engine → Risk Manager → Database
      ↓             ↓            ↓
  Market Data ←→ WebSocket → API Gateway
      ↓                           ↓
   Events (Kafka)              Frontend
```

## Daily Operations

### Morning Checklist (Daily)

**1. System Health Check**
```bash
#!/bin/bash
# morning_health_check.sh

echo "=== SMC Trading Agent Daily Health Check ==="
echo "Time: $(date)"
echo ""

# Check all services are running
docker-compose ps

# Check resource usage
echo "=== Resource Usage ==="
docker stats --no-stream

# Check database connectivity
echo "=== Database Health ==="
docker exec smc-postgres pg_isready -U smc_user -d smc_trading

# Check Redis connectivity
echo "=== Redis Health ==="
docker exec smc-redis redis-cli ping

# Check application health
echo "=== Application Health ==="
curl -f http://localhost:8000/health || echo "❌ Application health check failed"

# Check recent trades
echo "=== Recent Trading Activity ==="
curl -s http://localhost:8000/api/trades/recent | jq '.[-5:]'

echo ""
echo "=== Health Check Complete ==="
```

**2. Market Data Validation**
```bash
# Verify market data is current
python -c "
import requests
import time

response = requests.get('http://localhost:8000/api/market-data/BTCUSDT')
if response.status_code == 200:
    data = response.json()
    timestamp = data.get('timestamp')
    age = time.time() - timestamp/1000
    if age < 60:  # Data less than 1 minute old
        print('✓ Market data is current')
    else:
        print(f'⚠️  Market data is {age:.0f} seconds old')
else:
    print('❌ Failed to fetch market data')
"
```

**3. Risk Position Review**
```bash
# Check current positions and risk metrics
curl -s http://localhost:8000/api/risk/summary | jq '{
    total_exposure: .total_exposure,
    daily_pnl: .daily_pnl,
    max_drawdown: .max_drawdown,
    open_positions: .open_positions | length,
    risk_score: .risk_score
}'
```

**4. Performance Metrics Review**
```bash
# Review yesterday's performance
curl -s "http://localhost:8000/api/performance/daily?date=$(date -d 'yesterday' +%Y-%m-%d)" | jq '{
    total_trades: .total_trades,
    win_rate: .win_rate,
    total_pnl: .total_pnl,
    sharpe_ratio: .sharpe_ratio
}'
```

### During Trading Hours

**1. Continuous Monitoring**
```bash
# Monitor application logs for errors
tail -f /var/log/smc-agent/application.log | grep -E "(ERROR|CRITICAL|Exception)"

# Monitor trading activity
watch -n 5 'curl -s http://localhost:8000/api/trades/recent | jq ".[-3:]"'
```

**2. Performance Monitoring**
```bash
# Check system performance every hour
while true; do
    echo "$(date): Checking performance..."

    # CPU and Memory
    top -bn1 | head -5

    # Application response time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    echo "Response time: ${response_time}s"

    sleep 3600  # Check every hour
done
```

**3. Risk Monitoring**
```bash
# Real-time risk monitoring script
#!/bin/bash
# risk_monitor.sh

MAX_DAILY_LOSS=1000
MAX_POSITION_SIZE=5000

while true; do
    # Get current risk metrics
    risk_data=$(curl -s http://localhost:8000/api/risk/current)

    daily_loss=$(echo $risk_data | jq -r '.daily_loss')
    total_exposure=$(echo $risk_data | jq -r '.total_exposure')

    # Check thresholds
    if (( $(echo "$daily_loss > $MAX_DAILY_LOSS" | bc -l) )); then
        echo "🚨 Daily loss exceeded! Current: $daily_loss"
        # Send alert
        curl -X POST https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK \
          -H 'Content-type: application/json' \
          --data "{\"text\":\"Daily loss exceeded: \$$daily_loss\"}"
    fi

    if (( $(echo "$total_exposure > $MAX_POSITION_SIZE" | bc -l) )); then
        echo "⚠️  Position size exceeded: $total_exposure"
    fi

    sleep 60  # Check every minute
done
```

### End of Day Procedures

**1. Trading Shutdown**
```bash
# Safely shutdown trading
curl -X POST http://localhost:8000/api/trading/shutdown \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "end_of_day"}'

# Wait for all positions to be closed
while true; do
    open_positions=$(curl -s http://localhost:8000/api/positions | jq '. | length')
    if [ "$open_positions" -eq 0 ]; then
        echo "All positions closed"
        break
    fi
    echo "Waiting for $open_positions positions to close..."
    sleep 30
done
```

**2. Data Backup**
```bash
# Daily backup script
#!/bin/bash
# daily_backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/smc-agent"

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup database
docker exec smc-postgres pg_dump -U smc_user smc_trading > $BACKUP_DIR/$DATE/database.sql

# Backup configuration
cp /app/config.yaml $BACKUP_DIR/$DATE/
cp /app/.env $BACKUP_DIR/$DATE/

# Backup logs
tar -czf $BACKUP_DIR/$DATE/logs.tar.gz /var/log/smc-agent/

# Compress everything
cd $BACKUP_DIR
tar -czf smc-agent-backup-$DATE.tar.gz $DATE/
rm -rf $DATE/

echo "Backup completed: $BACKUP_DIR/smc-agent-backup-$DATE.tar.gz"
```

**3. Daily Report Generation**
```bash
# Generate daily trading report
python -c "
import requests
import json
from datetime import date

today = date.today().isoformat()

# Get daily performance
perf = requests.get(f'http://localhost:8000/api/performance/daily?date={today}').json()
risk = requests.get('http://localhost:8000/api/risk/summary').json()

report = {
    'date': today,
    'performance': perf,
    'risk_metrics': risk,
    'summary': {
        'total_trades': perf.get('total_trades', 0),
        'win_rate': perf.get('win_rate', 0),
        'total_pnl': perf.get('total_pnl', 0),
        'max_drawdown': risk.get('max_drawdown', 0)
    }
}

with open(f'/reports/daily_report_{today}.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f'Daily report generated: daily_report_{today}.json')
"
```

## Monitoring and Alerting

### Key Performance Indicators (KPIs)

**Trading Performance:**
- Daily P&L
- Win rate percentage
- Sharpe ratio
- Maximum drawdown
- Average trade duration
- Slippage percentage

**System Health:**
- API response time (target: <200ms)
- System uptime (target: >99.9%)
- Memory usage (target: <80%)
- CPU usage (target: <70%)
- Database query time (target: <100ms)

**Risk Management:**
- Current exposure
- Daily loss limit usage
- Position size compliance
- Stop loss hit rate
- Margin usage percentage

### Prometheus Metrics Configuration

**Key Metrics to Monitor:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'smc-agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

**Alert Rules:**
```yaml
# alert_rules.yml
groups:
  - name: smc_trading_alerts
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 0.5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High API response time detected"
          description: "95th percentile response time is {{ $value }}s"

      - alert: DailyLossLimitExceeded
        expr: daily_loss > 1000
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Daily loss limit exceeded"
          description: "Current daily loss: {{ $value }}"

      - alert: SystemDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "System is down"
          description: "{{ $labels.instance }} has been down for more than 1 minute"
```

### Grafana Dashboard Setup

**Essential Dashboards:**

**1. System Overview Dashboard**
- CPU, Memory, Network, Disk usage
- Container status
- Service health checks

**2. Trading Performance Dashboard**
- Real-time P&L
- Trade execution metrics
- Win/loss ratios
- Risk metrics

**3. Risk Management Dashboard**
- Current positions
- Exposure limits
- Stop loss status
- Margin usage

### Alert Notification Channels

**Slack Integration:**
```yaml
# alertmanager.yml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    slack_configs:
      - channel: '#smc-alerts'
        title: 'SMC Trading Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

**Email Alerts:**
```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'ops-team@company.com'
        subject: 'SMC Trading Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
```

## Performance Management

### Performance Optimization Checklist

**Database Optimization:**
```sql
-- Index optimization
CREATE INDEX CONCURRENTLY idx_trades_timestamp_symbol ON trades(timestamp, symbol);
CREATE INDEX CONCURRENTLY idx_positions_status ON positions(status);

-- Partition large tables (PostgreSQL 10+)
CREATE TABLE trades_2024_01 PARTITION OF trades
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Vacuum and analyze regularly
VACUUM ANALYZE trades;
```

**Application Optimization:**
```python
# Connection pooling
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 30,
    'pool_timeout': 30,
    'pool_recycle': 3600
}

# Cache configuration
REDIS_CONFIG = {
    'max_connections': 100,
    'retry_on_timeout': True,
    'health_check_interval': 30
}
```

### Performance Monitoring Scripts

**Real-time Performance Monitor:**
```bash
#!/bin/bash
# perf_monitor.sh

while true; do
    clear
    echo "=== SMC Trading Agent Performance Monitor ==="
    echo "Time: $(date)"
    echo ""

    # System metrics
    echo "=== System Resources ==="
    echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
    echo "Memory: $(free | grep Mem | awk '{printf("%.1f%%"), $3/$2 * 100.0}')"
    echo "Disk: $(df -h / | awk 'NR==2 {print $5}')"
    echo ""

    # Application metrics
    echo "=== Application Metrics ==="
    response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    echo "Response Time: ${response_time}s"

    # Database metrics
    echo "=== Database Metrics ==="
    db_connections=$(docker exec smc-postgres psql -U smc_user -t -c "SELECT count(*) FROM pg_stat_activity;")
    echo "Active DB Connections: $db_connections"

    sleep 10
done
```

### Load Testing and Benchmarking

**API Load Test:**
```python
# load_test.py
import asyncio
import aiohttp
import time
import statistics

async def benchmark_api(session, url, requests_per_second=10, duration=60):
    """Benchmark API endpoints"""

    semaphore = asyncio.Semaphore(requests_per_second)
    response_times = []
    errors = 0
    start_time = time.time()

    async def make_request():
        nonlocal errors
        async with semaphore:
            try:
                req_start = time.time()
                async with session.get(url) as response:
                    await response.text()
                    req_time = time.time() - req_start
                    response_times.append(req_time)
                    return response.status == 200
            except Exception:
                errors += 1
                return False

    # Generate requests for duration
    tasks = []
    while time.time() - start_time < duration:
        tasks.append(make_request())
        await asyncio.sleep(1/requests_per_second)

    results = await asyncio.gather(*tasks)

    # Calculate statistics
    success_rate = sum(results) / len(results) * 100
    avg_response_time = statistics.mean(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile

    return {
        'total_requests': len(results),
        'success_rate': success_rate,
        'avg_response_time': avg_response_time,
        'p95_response_time': p95_response_time,
        'errors': errors
    }

async def main():
    async with aiohttp.ClientSession() as session:
        print("Benchmarking API endpoints...")

        endpoints = [
            '/health',
            '/api/trades/recent',
            '/api/positions',
            '/api/risk/current'
        ]

        for endpoint in endpoints:
            url = f"http://localhost:8000{endpoint}"
            results = await benchmark_api(session, url)

            print(f"\n=== {endpoint} ===")
            print(f"Total Requests: {results['total_requests']}")
            print(f"Success Rate: {results['success_rate']:.2f}%")
            print(f"Avg Response Time: {results['avg_response_time']:.3f}s")
            print(f"95th Percentile: {results['p95_response_time']:.3f}s")
            print(f"Errors: {results['errors']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Security Operations

### Security Monitoring

**Security Log Monitoring:**
```bash
# Monitor security-related logs
tail -f /var/log/auth.log | grep -E "(ssh|sudo|fail|invalid)"

# Monitor application security events
grep -E "(authentication|authorization|security|attack)" /var/log/smc-agent/application.log
```

**Access Control Auditing:**
```bash
# Audit API access
curl -s http://localhost:8000/api/admin/access-log | jq '[
    .[] | select(.timestamp > (now - 86400))
]'

# Review active sessions
curl -s http://localhost:8000/api/admin/sessions | jq '.[] | select(.active == true)'
```

### Security Hardening Procedures

**Daily Security Checklist:**
```bash
#!/bin/bash
# daily_security_check.sh

echo "=== Daily Security Check ==="
echo "$(date)"

# 1. Check for failed login attempts
echo "=== Failed Login Attempts ==="
grep "Failed password" /var/log/auth.log | wc -l

# 2. Check for suspicious API activity
echo "=== Suspicious API Activity ==="
curl -s http://localhost:8000/api/admin/security-events | jq '.[] | select(.severity == "high")'

# 3. Verify SSL certificates
echo "=== SSL Certificate Status ==="
openssl x509 -in /etc/nginx/ssl/cert.pem -noout -dates

# 4. Check for known vulnerabilities
echo "=== Vulnerability Check ==="
# This would integrate with your vulnerability scanner
echo "Running vulnerability scan..."

# 5. Review API key usage
echo "=== API Key Usage ==="
curl -s http://localhost:8000/api/admin/api-keys | jq '.'

echo "=== Security Check Complete ==="
```

**Security Incident Response:**
```bash
#!/bin/bash
# security_incident_response.sh

INCIDENT_TYPE=$1
SEVERITY=$2

case $INCIDENT_TYPE in
    "unauthorized_access")
        echo "🚨 Unauthorized access detected!"

        # Disable affected accounts
        curl -X POST http://localhost:8000/api/admin/disable-account \
          -H "Authorization: Bearer $TOKEN" \
          -d '{"account_id": "compromised_account"}'

        # Rotate API keys
        curl -X POST http://localhost:8000/api/admin/rotate-api-keys \
          -H "Authorization: Bearer $TOKEN"

        # Send alert
        send_security_alert "Unauthorized access incident detected"
        ;;

    "suspicious_trading")
        echo "⚠️ Suspicious trading activity detected!"

        # Pause trading
        curl -X POST http://localhost:8000/api/trading/pause \
          -H "Authorization: Bearer $TOKEN"

        # Review recent trades
        curl -s http://localhost:8000/api/trades/suspicious > /tmp/suspicious_trades.json

        # Send alert to compliance
        send_compliance_alert "Suspicious trading activity detected"
        ;;
esac
```

## Backup and Disaster Recovery

### Backup Strategy

**Backup Schedule:**
- **Database**: Every 4 hours (continuous backups for critical data)
- **Configuration**: Daily
- **Logs**: Weekly
- **Application**: Before major updates

**Backup Retention:**
- **Daily backups**: 30 days
- **Weekly backups**: 12 weeks
- **Monthly backups**: 12 months
- **Yearly backups**: 7 years

**Automated Backup Script:**
```bash
#!/bin/bash
# automated_backup.sh

BACKUP_TYPE=$1  # hourly, daily, weekly, monthly
RETENTION_DAYS=$2

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/smc-agent"
BACKUP_FILE="smc-backup-${BACKUP_TYPE}-${TIMESTAMP}.tar.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Starting ${BACKUP_TYPE} backup..."

# Database backup
docker exec smc-postgres pg_dump -U smc_user -Fc smc_trading > /tmp/db_backup.dump

# Configuration backup
cp /app/config.yaml /tmp/
cp /app/.env /tmp/

# Application backup
docker save smc-trading-agent:latest > /tmp/app_backup.tar

# Create compressed backup
cd /tmp
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    db_backup.dump \
    config.yaml \
    .env \
    app_backup.tar

# Cleanup temporary files
rm -f /tmp/db_backup.dump /tmp/config.yaml /tmp/.env /tmp/app_backup.tar

# Upload to cloud storage (AWS S3 example)
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://smc-backups/${BACKUP_TYPE}/"

# Clean up old backups
find $BACKUP_DIR -name "smc-backup-${BACKUP_TYPE}-*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Verify backup
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "✓ Backup completed successfully: ${BACKUP_FILE}"
else
    echo "❌ Backup failed!"
    exit 1
fi
```

### Disaster Recovery Procedures

**Complete System Recovery:**
```bash
#!/bin/bash
# disaster_recovery.sh

BACKUP_FILE=$1  # Path to backup file

echo "Starting disaster recovery from: $BACKUP_FILE"

# 1. Stop all services
docker-compose down

# 2. Extract backup
mkdir -p /tmp/recovery
tar -xzf $BACKUP_FILE -C /tmp/recovery

# 3. Restore database
docker-compose up -d postgres
sleep 30  # Wait for database to start

docker exec -i smc-postgres pg_restore -U smc_user -d smc_trading < /tmp/recovery/db_backup.dump

# 4. Restore configuration
cp /tmp/recovery/config.yaml /app/
cp /tmp/recovery/.env /app/

# 5. Restore application
docker load < /tmp/recovery/app_backup.tar

# 6. Start all services
docker-compose up -d

# 7. Verify recovery
sleep 60
curl -f http://localhost:8000/health

if [ $? -eq 0 ]; then
    echo "✓ Disaster recovery completed successfully"
else
    echo "❌ Disaster recovery failed"
    exit 1
fi

# 8. Cleanup
rm -rf /tmp/recovery
```

**Database Point-in-Time Recovery:**
```bash
#!/bin/bash
# pitr_recovery.sh

RECOVERY_TIME=$1  # Target recovery time (ISO format)

echo "Starting point-in-time recovery to: $RECOVERY_TIME"

# 1. Create recovery configuration
cat > /tmp/recovery.conf << EOF
restore_command = 'cp /backup/wal/%f %p'
recovery_target_time = '$RECOVERY_TIME'
EOF

# 2. Stop PostgreSQL
docker-compose stop postgres

# 3. Prepare recovery
docker run --rm -v smc_postgres_data:/var/lib/postgresql/data \
  -v /backup:/backup \
  postgres:13 \
  bash -c "
    cp /backup/base_backup/* /var/lib/postgresql/data/
    cp /tmp/recovery.conf /var/lib/postgresql/data/
  "

# 4. Start PostgreSQL in recovery mode
docker-compose up -d postgres

# 5. Verify recovery
sleep 30
docker exec smc-postgres psql -U smc_user -d smc_trading -c "
  SELECT count(*) FROM trades WHERE timestamp <= '$RECOVERY_TIME';
"

echo "Point-in-time recovery completed"
```

## Maintenance Procedures

### Regular Maintenance Schedule

**Daily Tasks:**
- [ ] System health checks
- [ ] Review error logs
- [ ] Monitor trading performance
- [ ] Backup verification
- [ ] Security log review

**Weekly Tasks:**
- [ ] Performance analysis
- [ ] Database maintenance (VACUUM, ANALYZE)
- [ ] Log rotation and archiving
- [ ] Security updates review
- [ ] Capacity planning review

**Monthly Tasks:**
- [ ] Full system backup test
- [ ] Disaster recovery drill
- [ ] Security audit
- [ ] Performance tuning
- [ ] Documentation update

**Quarterly Tasks:**
- [ ] Major system updates
- [ ] Architecture review
- [ ] Capacity upgrade planning
- [ ] Compliance audit
- [ ] Vendor security review

### System Updates

**Application Update Procedure:**
```bash
#!/bin/bash
# update_application.sh

NEW_VERSION=$1

echo "Updating application to version: $NEW_VERSION"

# 1. Pre-update checks
echo "Running pre-update checks..."

# Verify system health
curl -f http://localhost:8000/health || {
    echo "❌ System health check failed"
    exit 1
}

# Check for open positions
open_positions=$(curl -s http://localhost:8000/api/positions | jq '. | length')
if [ "$open_positions" -gt 0 ]; then
    echo "⚠️  Open positions detected. Consider closing positions before update."
    read -p "Continue with update? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 2. Create backup
echo "Creating pre-update backup..."
./automated_backup.sh pre-update 7

# 3. Stop trading
echo "Stopping trading activities..."
curl -X POST http://localhost:8000/api/trading/shutdown \
  -H "Authorization: Bearer $TOKEN"

# 4. Update application
echo "Updating application..."
git fetch origin
git checkout $NEW_VERSION

# 5. Build and deploy
docker-compose -f docker-compose.optimized.yml build
docker-compose -f docker-compose.optimized.yml up -d

# 6. Post-update checks
echo "Running post-update checks..."
sleep 60

# Verify health
for i in {1..10}; do
    if curl -f http://localhost:8000/health; then
        echo "✅ Application is healthy"
        break
    fi
    echo "Waiting for application to start... ($i/10)"
    sleep 30
done

# Run database migrations
python -m alembic upgrade head

# Verify configuration
python -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print('Configuration validated successfully')
"

# 7. Resume operations
echo "Resuming operations..."
curl -X POST http://localhost:8000/api/trading/start \
  -H "Authorization: Bearer $TOKEN"

echo "✅ Application update completed successfully"
```

### Database Maintenance

**Database Maintenance Script:**
```bash
#!/bin/bash
# database_maintenance.sh

echo "Starting database maintenance..."

# 1. Database statistics
echo "Gathering database statistics..."
docker exec smc-postgres psql -U smc_user -d smc_trading -c "ANALYZE;"

# 2. Vacuum old data
echo "Vacuuming old data..."
docker exec smc-postgres psql -U smc_user -d smc_trading -c "
    VACUUM (VERBOSE, ANALYZE) trades;
    VACUUM (VERBOSE, ANALYZE) positions;
    VACUUM (VERBOSE, ANALYZE) market_data;
"

# 3. Rebuild indexes if needed
echo "Checking index bloat..."
docker exec smc-postgres psql -U smc_user -d smc_trading -c "
    SELECT schemaname, tablename, indexname,
           pg_size_pretty(pg_relation_size(indexrelid)) as index_size
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
    ORDER BY pg_relation_size(indexrelid) DESC;
"

# 4. Archive old data (if configured)
echo "Archiving old data..."
docker exec smc-postgres psql -U smc_user -d smc_trading -c "
    -- Archive trades older than 1 year
    INSERT INTO trades_archive
    SELECT * FROM trades
    WHERE timestamp < NOW() - INTERVAL '1 year';

    -- Delete archived trades
    DELETE FROM trades
    WHERE timestamp < NOW() - INTERVAL '1 year';
"

# 5. Check database size
echo "Database size report:"
docker exec smc-postgres psql -U smc_user -d smc_trading -c "
    SELECT pg_size_pretty(pg_database_size('smc_trading')) as database_size;
"

echo "Database maintenance completed"
```

## Incident Management

### Incident Classification

**Severity Levels:**

**Critical (P1):**
- System completely down
- Major financial loss (>10% daily loss)
- Security breach
- Regulatory compliance issue

**High (P2):**
- Significant performance degradation
- Partial system failure
- High risk of financial loss
- Important features not working

**Medium (P3):**
- Minor performance issues
- Non-critical features failing
- User experience impacted

**Low (P4):**
- Documentation issues
- Minor bugs
- Enhancement requests

### Incident Response Process

**1. Detection**
```bash
# Automated detection script
#!/bin/bash
# incident_detection.sh

# Check for critical conditions
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ System healthy"
else
    echo "🚨 CRITICAL: System health check failed"
    ./create_incident.sh "system_down" "critical" "System health check failed"
fi

# Check for high daily loss
daily_loss=$(curl -s http://localhost:8000/api/risk/current | jq -r '.daily_loss')
if (( $(echo "$daily_loss > 1000" | bc -l) )); then
    echo "🚨 HIGH: Daily loss exceeded: $daily_loss"
    ./create_incident.sh "daily_loss_exceeded" "high" "Daily loss: $daily_loss"
fi
```

**2. Incident Creation:**
```bash
#!/bin/bash
# create_incident.sh

INCIDENT_TYPE=$1
SEVERITY=$2
DESCRIPTION=$3

INCIDENT_ID=$(date +%Y%m%d-%H%M%S)

echo "Creating incident $INCIDENT_ID..."

# Create incident record
cat > /tmp/incident_$INCIDENT_ID.json << EOF
{
    "incident_id": "$INCIDENT_ID",
    "type": "$INCIDENT_TYPE",
    "severity": "$SEVERITY",
    "description": "$DESCRIPTION",
    "status": "open",
    "created_at": "$(date -Iseconds)",
    "assigned_to": "ops-team",
    "affected_services": ["trading-engine", "risk-manager"]
}
EOF

# Store incident
mv /tmp/incident_$INCIDENT_ID.json /incidents/

# Send notification
send_alert "$SEVERITY" "Incident $INCIDENT_ID: $DESCRIPTION"

# Add to incident tracking system
curl -X POST https://your-incident-system.com/api/incidents \
  -H "Authorization: Bearer $INCIDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @/incidents/incident_$INCIDENT_ID.json

echo "Incident $INCIDENT_ID created and notified"
```

**3. Response and Resolution**
```bash
#!/bin/bash
# incident_response.sh

INCIDENT_ID=$1
ACTION=$2

case $ACTION in
    "pause_trading")
        echo "Pausing trading for incident $INCIDENT_ID..."
        curl -X POST http://localhost:8000/api/trading/pause \
          -H "Authorization: Bearer $TOKEN"
        ;;

    "switch_to_safe_mode")
        echo "Switching to safe mode for incident $INCIDENT_ID..."
        curl -X POST http://localhost:8000/api/admin/safe-mode \
          -H "Authorization: Bearer $TOKEN"
        ;;

    "scale_down")
        echo "Scaling down services for incident $INCIDENT_ID..."
        kubectl scale deployment smc-agent --replicas=1 -n smc-trading
        ;;

    "escalate")
        echo "Escalating incident $INCIDENT_ID..."
        # Call escalation procedures
        ./escalate_incident.sh $INCIDENT_ID
        ;;
esac

# Update incident status
jq ".status = 'in_progress'" /incidents/incident_$INCIDENT_ID.json > /tmp/incident_temp
mv /tmp/incident_temp /incidents/incident_$INCIDENT_ID.json
```

### Post-Incident Review

**Post-Mortem Template:**
```markdown
# Incident Post-Mortem

## Incident Summary
- **Incident ID**: {incident_id}
- **Date/Time**: {incident_time}
- **Duration**: {duration}
- **Severity**: {severity}
- **Impact**: {impact_description}

## Timeline
- {time}: {event_description}
- {time}: {event_description}
- ...

## Root Cause Analysis
**Primary Cause**: {root_cause}
**Contributing Factors**:
- {factor_1}
- {factor_2}

## Resolution Actions
1. {action_taken_1}
2. {action_taken_2}
3. ...

## Prevention Measures
1. {prevention_measure_1}
2. {prevention_measure_2}
3. ...

## Lessons Learned
- {lesson_1}
- {lesson_2}

## Follow-up Items
- [ ] {follow_up_item_1}
- [ ] {follow_up_item_2}
```

## Troubleshooting Guide

### Common Issues and Solutions

**1. High Memory Usage**

**Symptoms:**
- Container getting OOMKilled
- System swapping heavily
- Memory usage >90%

**Diagnostics:**
```bash
# Check memory usage by process
docker exec smc-agent ps aux --sort=-%mem | head -10

# Check for memory leaks
python -m memory_profiler main.py

# Check application memory pools
curl -s http://localhost:8000/api/debug/memory | jq .
```

**Solutions:**
```bash
# Restart affected services
docker restart smc-agent

# Increase memory limits
docker update --memory=8g smc-agent

# Enable memory profiling
export MEMORY_PROFILING=1
```

**2. Database Connection Issues**

**Symptoms:**
- Connection timeout errors
- Too many connections error
- Slow query performance

**Diagnostics:**
```bash
# Check connection count
docker exec smc-postgres psql -U smc_user -t -c "SELECT count(*) FROM pg_stat_activity;"

# Check slow queries
docker exec smc-postgres psql -U smc_user -c "
    SELECT query, mean_time, calls
    FROM pg_stat_statements
    ORDER BY mean_time DESC
    LIMIT 10;
"

# Check connection pool status
curl -s http://localhost:8000/api/debug/database | jq .
```

**Solutions:**
```bash
# Increase connection pool size
# Edit config.yaml
database:
  pool_size: 30
  max_overflow: 50

# Restart application
docker restart smc-agent

# Kill long-running queries
docker exec smc-postgres psql -U smc_user -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE state = 'active'
    AND query_start < now() - interval '5 minutes';
"
```

**3. Exchange API Rate Limits**

**Symptoms:**
- 429 Too Many Requests errors
- Missing market data
- Failed trade executions

**Diagnostics:**
```bash
# Check API usage
curl -s http://localhost:8000/api/exchanges/rate-limits | jq .

# Check recent API errors
grep "429\|rate limit" /var/log/smc-agent/application.log
```

**Solutions:**
```bash
# Implement rate limiting
# Update config.yaml
exchanges:
  binance:
    rate_limit: 600  # Reduce from default
    request_timeout: 30

# Add request queuing
export ENABLE_REQUEST_QUEUE=1

# Use multiple API keys (if available)
export BINANCE_API_KEY_2="your_second_key"
```

**4. High Latency**

**Symptoms:**
- Slow API response times
- Delayed trade executions
- Market data delays

**Diagnostics:**
```bash
# Check network latency
ping api.binance.com
traceroute api.binance.com

# Check application performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Profile application
python -m cProfile -o profile.stats main.py
```

**Solutions:**
```bash
# Optimize database queries
EXPLAIN ANALYZE SELECT * FROM trades WHERE symbol = 'BTCUSDT';

# Enable caching
export REDIS_CACHE_ENABLED=1

# Optimize network settings
# Edit /etc/sysctl.conf
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
```

### Emergency Procedures

**1. Emergency Trading Stop**
```bash
#!/bin/bash
# emergency_stop.sh

echo "🚨 EMERGENCY TRADING STOP INITIATED"

# 1. Stop all trading immediately
curl -X POST http://localhost:8000/api/trading/emergency-stop \
  -H "Authorization: Bearer $EMERGENCY_TOKEN"

# 2. Cancel all open orders
curl -X POST http://localhost:8000/api/orders/cancel-all \
  -H "Authorization: Bearer $EMERGENCY_TOKEN"

# 3. Close all positions (if configured for emergency closure)
curl -X POST http://localhost:8000/api/positions/emergency-close \
  -H "Authorization: Bearer $EMERGENCY_TOKEN"

# 4. Notify all teams
send_emergency_alert "Emergency trading stop executed"

echo "✅ Emergency stop completed"
```

**2. System Rollback**
```bash
#!/bin/bash
# rollback_system.sh

BACKUP_VERSION=$1

echo "Rolling back system to backup: $BACKUP_VERSION"

# 1. Stop current system
docker-compose down

# 2. Restore from backup
./disaster_recovery.sh /backup/smc-agent/$BACKUP_VERSION

# 3. Verify rollback
sleep 60
if curl -f http://localhost:8000/health; then
    echo "✅ System rollback successful"
else
    echo "❌ System rollback failed"
    exit 1
fi
```

## Capacity Planning

### Resource Monitoring

**Current Usage Analysis:**
```bash
#!/bin/bash
# capacity_analysis.sh

echo "=== Capacity Analysis Report ==="
echo "Date: $(date)"
echo ""

# CPU Usage Analysis
echo "=== CPU Usage ==="
echo "Current: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
echo "Average (24h): $(sar -u | grep Average | awk '{print $3}')"
echo ""

# Memory Usage Analysis
echo "=== Memory Usage ==="
echo "Current: $(free | grep Mem | awk '{printf("%.1f%%"), $3/$2 * 100.0}')"
echo "Peak (24h): $(sar -r | grep Average | awk '{print $3}')"
echo ""

# Storage Usage Analysis
echo "=== Storage Usage ==="
df -h | grep -E "(Filesystem|/dev/)"
echo ""

# Database Growth
echo "=== Database Growth ==="
docker exec smc-postgres psql -U smc_user -d smc_trading -c "
    SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
echo ""

# Trading Volume Trends
echo "=== Trading Volume Trends ==="
curl -s "http://localhost:8000/api/analytics/volume-trend?days=30" | jq '.'
```

### Scaling Recommendations

**Vertical Scaling (Increasing Resources):**
```bash
# Current resource limits
docker inspect smc-agent | jq '.[0].HostConfig.Resources'

# Recommended scaling based on usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | tr -d '%')
MEM_USAGE=$(free | grep Mem | awk '{printf("%.0f"), $3/$2 * 100.0}')

if [ "$CPU_USAGE" -gt 80 ]; then
    echo "⚠️  High CPU usage detected. Consider increasing CPU allocation."
fi

if [ "$MEM_USAGE" -gt 85 ]; then
    echo "⚠️  High memory usage detected. Consider increasing memory allocation."
fi
```

**Horizontal Scaling (Adding Instances):**
```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: smc-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: smc-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

## Compliance and Auditing

### Regulatory Compliance

**Trade Reporting:**
```bash
#!/bin/bash
# generate_compliance_report.sh

REPORT_DATE=$(date +%Y-%m-%d)
REPORT_DIR="/compliance-reports"

mkdir -p $REPORT_DIR

echo "Generating compliance report for: $REPORT_DATE"

# 1. Trade execution report
curl -s "http://localhost:8000/api/reports/trades?date=$REPORT_DATE" \
  -H "Authorization: Bearer $COMPLIANCE_TOKEN" \
  > $REPORT_DIR/trades_$REPORT_DATE.json

# 2. Risk metrics report
curl -s "http://localhost:8000/api/reports/risk-metrics?date=$REPORT_DATE" \
  -H "Authorization: Bearer $COMPLIANCE_TOKEN" \
  > $REPORT_DIR/risk_metrics_$REPORT_DATE.json

# 3. System activity log
curl -s "http://localhost:8000/api/reports/system-activity?date=$REPORT_DATE" \
  -H "Authorization: Bearer $COMPLIANCE_TOKEN" \
  > $REPORT_DIR/system_activity_$REPORT_DATE.json

# 4. Audit trail
curl -s "http://localhost:8000/api/reports/audit-trail?date=$REPORT_DATE" \
  -H "Authorization: Bearer $COMPLIANCE_TOKEN" \
  > $REPORT_DIR/audit_trail_$REPORT_DATE.json

# 5. Generate summary report
python -c "
import json
from datetime import datetime

date = '$REPORT_DATE'
trades = json.load(open(f'$REPORT_DIR/trades_{date}.json'))
risk = json.load(open(f'$REPORT_DIR/risk_metrics_{date}.json'))

summary = {
    'report_date': date,
    'total_trades': len(trades),
    'total_volume': sum(t['quantity'] for t in trades),
    'total_pnl': sum(t.get('pnl', 0) for t in trades),
    'max_drawdown': risk.get('max_drawdown', 0),
    'var_95': risk.get('var_95', 0),
    'compliance_checks': {
        'position_limits_ok': risk.get('position_limits_compliant', True),
        'risk_limits_ok': risk.get('risk_limits_compliant', True),
        'documentation_complete': True
    }
}

with open(f'$REPORT_DIR/compliance_summary_{date}.json', 'w') as f:
    json.dump(summary, f, indent=2)
"

echo "✅ Compliance report generated: $REPORT_DIR/compliance_summary_$REPORT_DATE.json"
```

### Audit Trail

**Audit Log Configuration:**
```yaml
# config.yaml
audit:
  enabled: true
  log_level: INFO
  retention_days: 2555  # 7 years

  events_to_log:
    - trade_executed
    - position_opened
    - position_closed
    - risk_limit_breached
    - configuration_changed
    - user_authentication
    - api_access
    - system_error

  storage:
    type: database
    table: audit_logs
    backup_frequency: daily
```

**Audit Query Examples:**
```bash
# Query audit events for specific date
curl -s "http://localhost:8000/api/audit/events?date=2024-01-01" \
  -H "Authorization: Bearer $AUDIT_TOKEN" | jq '.'

# Query specific user activity
curl -s "http://localhost:8000/api/audit/user?user_id=admin&days=7" \
  -H "Authorization: Bearer $AUDIT_TOKEN" | jq '.'

# Query trade-related audit events
curl -s "http://localhost:8000/api/audit/trade-events?days=30" \
  -H "Authorization: Bearer $AUDIT_TOKEN" | jq '.'
```

### Security Auditing

**Monthly Security Audit Script:**
```bash
#!/bin/bash
# monthly_security_audit.sh

AUDIT_DATE=$(date +%Y-%m-01)
AUDIT_DIR="/security-audits"

mkdir -p $AUDIT_DIR

echo "Running monthly security audit..."

# 1. Access control review
echo "=== Access Control Review ===" > $AUDIT_DIR/access_control_$AUDIT_DATE.txt
curl -s http://localhost:8000/api/admin/users >> $AUDIT_DIR/access_control_$AUDIT_DATE.txt
curl -s http://localhost:8000/api/admin/api-keys >> $AUDIT_DIR/access_control_$AUDIT_DATE.txt

# 2. Configuration security review
echo "=== Configuration Security Review ===" > $AUDIT_DIR/config_security_$AUDIT_DATE.txt
grep -i "password\|secret\|key" /app/config.yaml >> $AUDIT_DIR/config_security_$AUDIT_DATE.txt

# 3. Log analysis for security events
echo "=== Security Events Analysis ===" > $AUDIT_DIR/security_events_$AUDIT_DATE.txt
grep -E "(authentication|authorization|security|attack|breach)" /var/log/smc-agent/*.log >> $AUDIT_DIR/security_events_$AUDIT_DATE.txt

# 4. Vulnerability scan
echo "=== Vulnerability Scan ===" > $AUDIT_DIR/vulnerabilities_$AUDIT_DATE.txt
# This would integrate with your vulnerability scanning tool

# 5. Generate security report
cat > $AUDIT_DIR/security_report_$AUDIT_DATE.md << EOF
# Monthly Security Report - $AUDIT_DATE

## Executive Summary
[Summary of security posture]

## Findings
### High Severity
[High severity findings]

### Medium Severity
[Medium severity findings]

### Low Severity
[Low severity findings]

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]

## Action Items
- [ ] [Action item 1]
- [ ] [Action item 2]
EOF

echo "✅ Security audit completed: $AUDIT_DIR/security_report_$AUDIT_DATE.md"
```

---

This operations manual provides comprehensive guidance for maintaining and operating the SMC Trading Agent in production. Regular reviews and updates of this manual should be performed to ensure it remains current with system changes and operational requirements.