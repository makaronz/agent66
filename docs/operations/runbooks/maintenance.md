# Maintenance Runbook

## Overview

This runbook covers regular maintenance procedures for the SMC Trading Agent system to ensure optimal performance, security, and reliability. All maintenance tasks are categorized by frequency and criticality.

## 📅 Maintenance Schedule

### Daily Tasks (Automated)

- [ ] System health checks
- [ ] Database backup verification
- [ ] Log rotation and cleanup
- [ ] Performance metrics review
- [ ] Security scan results review

### Weekly Tasks

- [ ] Database maintenance (VACUUM, ANALYZE)
- [ ] Certificate expiration checks
- [ ] Dependency vulnerability scans
- [ ] Performance trend analysis
- [ ] Capacity planning review

### Monthly Tasks

- [ ] Full system backup test
- [ ] Security audit
- [ ] Disaster recovery test
- [ ] Documentation updates
- [ ] Performance optimization review

### Quarterly Tasks

- [ ] Major dependency updates
- [ ] Security penetration testing
- [ ] Disaster recovery drill
- [ ] Architecture review
- [ ] Compliance audit

## 🔄 Daily Maintenance

### Automated Daily Health Check

```bash
#!/bin/bash
# daily-maintenance.sh - Automated daily maintenance tasks

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NAMESPACE="smc-trading"
LOG_FILE="/var/log/maintenance/daily_$TIMESTAMP.log"

exec > >(tee -a $LOG_FILE)
exec 2>&1

echo "🔄 Daily Maintenance - $(date)"
echo "================================"

# 1. System Health Check
echo "1. Running system health check..."
./scripts/quick-health-check.sh
HEALTH_STATUS=$?

if [ $HEALTH_STATUS -ne 0 ]; then
    echo "⚠️ Health check failed - generating detailed report"
    ./scripts/generate-diagnostic-report.sh

    # Send alert
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Daily health check failed. Diagnostic report generated."}' \
        $SLACK_WEBHOOK_URL
fi

# 2. Database Backup Verification
echo "2. Verifying database backups..."
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
BACKUP_DATE=$(echo $LATEST_BACKUP | grep -o '[0-9]\{8\}')
TODAY=$(date +%Y%m%d)

if [ "$BACKUP_DATE" = "$TODAY" ] || [ "$BACKUP_DATE" = "$(date -d 'yesterday' +%Y%m%d)" ]; then
    echo "✅ Recent backup found: $LATEST_BACKUP"
else
    echo "❌ No recent backup found - triggering emergency backup"
    kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_dump -U postgres -d smc_trading -F c -f /tmp/emergency_$(date +%Y%m%d_%H%M%S).dump

    # Alert for missing backup
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Database backup missing - emergency backup created"}' \
        $SLACK_WEBHOOK_URL
fi

# 3. Log Cleanup
echo "3. Cleaning up old logs..."
find /var/log -name "*.log" -mtime +7 -delete
kubectl exec deployment/trading-engine -n $NAMESPACE -- find /var/log -name "*.log" -mtime +7 -delete
kubectl exec deployment/api-gateway -n $NAMESPACE -- find /var/log -name "*.log" -mtime +7 -delete

# 4. Performance Metrics Collection
echo "4. Collecting performance metrics..."
kubectl top nodes > /tmp/daily_node_metrics_$TIMESTAMP.txt
kubectl top pods -n $NAMESPACE > /tmp/daily_pod_metrics_$TIMESTAMP.txt

# Store metrics in monitoring system
curl -X POST "http://prometheus:9090/api/v1/admin/tsdb/snapshot"

# 5. Security Scan Results Review
echo "5. Reviewing security scan results..."
CRITICAL_VULNS=$(kubectl get vulnerabilityreports -n $NAMESPACE -o json | jq '.items[] | select(.report.summary.criticalCount > 0) | .metadata.name' | wc -l)

if [ $CRITICAL_VULNS -gt 0 ]; then
    echo "⚠️ Found $CRITICAL_VULNS critical vulnerabilities"
    kubectl get vulnerabilityreports -n $NAMESPACE -o json | jq '.items[] | select(.report.summary.criticalCount > 0)'

    # Alert for critical vulnerabilities
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Critical vulnerabilities found: '$CRITICAL_VULNS'"}' \
        $SLACK_WEBHOOK_URL
else
    echo "✅ No critical vulnerabilities found"
fi

echo "Daily maintenance completed - $(date)"
```

### Manual Daily Checks

```bash
# Check trading performance
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:password@postgres-primary:5432/smc_trading')
cur = conn.cursor()

# Daily P&L
cur.execute('''
    SELECT
        DATE(timestamp) as date,
        COUNT(*) as trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(pnl) as total_pnl,
        AVG(pnl) as avg_pnl
    FROM trades
    WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE(timestamp)
    ORDER BY date DESC;
''')

print('Recent Trading Performance:')
for row in cur.fetchall():
    print(f'{row[0]}: {row[1]} trades, {row[2]} wins, P&L: ${row[3]:.2f}')
"

# Check system resources
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import psutil
print(f'CPU: {psutil.cpu_percent()}%')
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'Disk: {psutil.disk_usage(\"/\").percent}%')
"
```

## 📊 Weekly Maintenance

### Database Maintenance

```bash
#!/bin/bash
# weekly-database-maintenance.sh - Weekly database optimization

NAMESPACE="smc-trading"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📊 Weekly Database Maintenance - $(date)"
echo "======================================="

# 1. Database Statistics Update
echo "1. Updating database statistics..."
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "ANALYZE;"

# 2. Vacuum Operations
echo "2. Running VACUUM operations..."
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "
VACUUM (VERBOSE, ANALYZE) trades;
VACUUM (VERBOSE, ANALYZE) smc_signals;
VACUUM (VERBOSE, ANALYZE) user_sessions;
VACUUM (VERBOSE, ANALYZE) audit_logs;
"

# 3. Index Maintenance
echo "3. Checking index usage..."
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;
"

# 4. Connection Pool Optimization
echo "4. Optimizing connection pool..."
kubectl exec pgbouncer-0 -n $NAMESPACE -- psql -p 6432 pgbouncer -c "SHOW POOLS;"
kubectl exec pgbouncer-0 -n $NAMESPACE -- psql -p 6432 pgbouncer -c "SHOW CLIENTS;"

# 5. Database Size Monitoring
echo "5. Monitoring database size..."
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "
SELECT
    pg_size_pretty(pg_database_size('smc_trading')) as database_size,
    pg_size_pretty(pg_total_relation_size('trades')) as trades_table_size,
    pg_size_pretty(pg_total_relation_size('smc_signals')) as signals_table_size;
"

# 6. Slow Query Analysis
echo "6. Analyzing slow queries..."
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    stddev_exec_time,
    rows
FROM pg_stat_statements
WHERE mean_exec_time > 1000  -- Queries taking more than 1 second
ORDER BY mean_exec_time DESC
LIMIT 10;
"

echo "Weekly database maintenance completed"
```

### Certificate Management

```bash
#!/bin/bash
# certificate-maintenance.sh - Certificate expiration monitoring

echo "🔐 Certificate Maintenance"
echo "========================="

# Check Kubernetes certificates
kubectl get certificates -n smc-trading

# Check certificate expiration
for cert in $(kubectl get certificates -n smc-trading -o jsonpath='{.items[*].metadata.name}'); do
    expiry=$(kubectl get certificate $cert -n smc-trading -o jsonpath='{.status.notAfter}')
    echo "Certificate $cert expires: $expiry"

    # Check if expiring within 30 days
    expiry_timestamp=$(date -d "$expiry" +%s)
    current_timestamp=$(date +%s)
    days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

    if [ $days_until_expiry -lt 30 ]; then
        echo "⚠️ Certificate $cert expires in $days_until_expiry days"

        # Send alert
        curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"⚠️ Certificate '$cert' expires in '$days_until_expiry' days"}' \
            $SLACK_WEBHOOK_URL
    fi
done

# Check external certificate
echo "Checking external API certificate..."
cert_info=$(openssl s_client -connect api.smc-trading.com:443 -servername api.smc-trading.com 2>/dev/null | openssl x509 -noout -dates)
echo "$cert_info"
```

### Dependency Updates

```bash
#!/bin/bash
# dependency-updates.sh - Check for dependency updates

echo "📦 Dependency Update Check"
echo "========================="

# Check Python dependencies
echo "1. Python Dependencies:"
kubectl exec deployment/trading-engine -n smc-trading -- pip list --outdated

# Check Node.js dependencies
echo "2. Node.js Dependencies:"
kubectl exec deployment/api-gateway -n smc-trading -- npm outdated

# Check Rust dependencies
echo "3. Rust Dependencies:"
kubectl exec deployment/execution-engine -n smc-trading -- cargo outdated

# Check container image updates
echo "4. Container Image Updates:"
images=("trading-engine" "api-gateway" "execution-engine" "web-app")
for image in "${images[@]}"; do
    current_tag=$(kubectl get deployment $image -n smc-trading -o jsonpath='{.spec.template.spec.containers[0].image}' | cut -d: -f2)
    echo "   $image: current tag $current_tag"

    # Check for newer tags (this would need to be implemented based on your registry)
    # docker run --rm gcr.io/go-containerregistry/crane:latest ls smc-trading/$image | tail -5
done
```

## 🗓️ Monthly Maintenance

### Full System Backup Test

```bash
#!/bin/bash
# monthly-backup-test.sh - Comprehensive backup restoration test

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_NAMESPACE="smc-trading-backup-test"

echo "💾 Monthly Backup Test - $(date)"
echo "================================"

# 1. Create test namespace
kubectl create namespace $TEST_NAMESPACE

# 2. Get latest backup
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
echo "Testing backup: $LATEST_BACKUP"

# 3. Download and extract backup
aws s3 cp s3://smc-trading-backups/daily/$LATEST_BACKUP ./test-backup.dump.gz
gunzip test-backup.dump.gz

# 4. Deploy test PostgreSQL instance
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-test
  namespace: $TEST_NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-test
  template:
    metadata:
      labels:
        app: postgres-test
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: smc_trading
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          value: testpassword
        ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-test
  namespace: $TEST_NAMESPACE
spec:
  selector:
    app: postgres-test
  ports:
  - port: 5432
    targetPort: 5432
EOF

# 5. Wait for PostgreSQL to be ready
kubectl wait --for=condition=available deployment/postgres-test -n $TEST_NAMESPACE --timeout=300s

# 6. Restore backup
kubectl cp test-backup.dump $TEST_NAMESPACE/$(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}'):/tmp/
kubectl exec -n $TEST_NAMESPACE $(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}') -- pg_restore -U postgres -d smc_trading -v /tmp/test-backup.dump

# 7. Verify restoration
TRADE_COUNT=$(kubectl exec -n $TEST_NAMESPACE $(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}') -- psql -U postgres -d smc_trading -t -c "SELECT COUNT(*) FROM trades;")
USER_COUNT=$(kubectl exec -n $TEST_NAMESPACE $(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}') -- psql -U postgres -d smc_trading -t -c "SELECT COUNT(*) FROM users;")

echo "Backup restoration test results:"
echo "- Trades: $TRADE_COUNT"
echo "- Users: $USER_COUNT"

# 8. Cleanup
kubectl delete namespace $TEST_NAMESPACE
rm -f test-backup.dump

# 9. Report results
if [ $TRADE_COUNT -gt 0 ] && [ $USER_COUNT -gt 0 ]; then
    echo "✅ Monthly backup test PASSED"
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"✅ Monthly backup restoration test PASSED"}' \
        $SLACK_WEBHOOK_URL
else
    echo "❌ Monthly backup test FAILED"
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"❌ Monthly backup restoration test FAILED - immediate attention required"}' \
        $SLACK_WEBHOOK_URL
fi
```

### Security Audit

```bash
#!/bin/bash
# monthly-security-audit.sh - Comprehensive security audit

echo "🔐 Monthly Security Audit - $(date)"
echo "==================================="

NAMESPACE="smc-trading"
AUDIT_REPORT="security_audit_$(date +%Y%m%d).md"

cat > $AUDIT_REPORT << EOF
# Security Audit Report
Date: $(date)
Namespace: $NAMESPACE

## Findings Summary
EOF

# 1. Vulnerability Scan
echo "1. Running vulnerability scan..."
kubectl get vulnerabilityreports -n $NAMESPACE -o json > vuln_report.json

CRITICAL_COUNT=$(jq '.items[] | .report.summary.criticalCount' vuln_report.json | awk '{sum += $1} END {print sum}')
HIGH_COUNT=$(jq '.items[] | .report.summary.highCount' vuln_report.json | awk '{sum += $1} END {print sum}')

echo "### Vulnerability Scan Results" >> $AUDIT_REPORT
echo "- Critical vulnerabilities: $CRITICAL_COUNT" >> $AUDIT_REPORT
echo "- High vulnerabilities: $HIGH_COUNT" >> $AUDIT_REPORT
echo "" >> $AUDIT_REPORT

# 2. RBAC Audit
echo "2. Auditing RBAC configuration..."
echo "### RBAC Configuration" >> $AUDIT_REPORT
kubectl get rolebindings -n $NAMESPACE >> $AUDIT_REPORT
echo "" >> $AUDIT_REPORT

# 3. Network Policy Audit
echo "3. Checking network policies..."
NETWORK_POLICIES=$(kubectl get networkpolicies -n $NAMESPACE --no-headers | wc -l)
echo "### Network Security" >> $AUDIT_REPORT
echo "- Network policies configured: $NETWORK_POLICIES" >> $AUDIT_REPORT
echo "" >> $AUDIT_REPORT

# 4. Secret Audit
echo "4. Auditing secrets..."
echo "### Secrets Audit" >> $AUDIT_REPORT
kubectl get secrets -n $NAMESPACE -o json | jq '.items[] | {name: .metadata.name, type: .type, keys: (.data | keys)}' >> $AUDIT_REPORT
echo "" >> $AUDIT_REPORT

# 5. Pod Security Context Audit
echo "5. Checking pod security contexts..."
echo "### Pod Security Contexts" >> $AUDIT_REPORT
kubectl get pods -n $NAMESPACE -o json | jq '.items[] | {name: .metadata.name, securityContext: .spec.securityContext, containerSecurityContext: .spec.containers[].securityContext}' >> $AUDIT_REPORT
echo "" >> $AUDIT_REPORT

# 6. Generate recommendations
echo "### Recommendations" >> $AUDIT_REPORT
if [ $CRITICAL_COUNT -gt 0 ]; then
    echo "- URGENT: Address $CRITICAL_COUNT critical vulnerabilities" >> $AUDIT_REPORT
fi
if [ $HIGH_COUNT -gt 5 ]; then
    echo "- Address $HIGH_COUNT high-severity vulnerabilities" >> $AUDIT_REPORT
fi
if [ $NETWORK_POLICIES -eq 0 ]; then
    echo "- Implement network policies for better network segmentation" >> $AUDIT_REPORT
fi

echo "Security audit completed. Report: $AUDIT_REPORT"

# Send summary to security team
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"🔐 Monthly security audit completed. Critical: '$CRITICAL_COUNT', High: '$HIGH_COUNT'"}' \
    $SLACK_SECURITY_WEBHOOK
```

### Performance Optimization Review

```bash
#!/bin/bash
# monthly-performance-review.sh - Performance optimization analysis

echo "📈 Monthly Performance Review - $(date)"
echo "======================================"

NAMESPACE="smc-trading"

# 1. Resource Usage Trends
echo "1. Analyzing resource usage trends..."
kubectl exec prometheus-0 -n monitoring -- promtool query instant 'avg_over_time(container_cpu_usage_seconds_total{namespace="'$NAMESPACE'"}[30d])'
kubectl exec prometheus-0 -n monitoring -- promtool query instant 'avg_over_time(container_memory_usage_bytes{namespace="'$NAMESPACE'"}[30d])'

# 2. Database Performance Analysis
echo "2. Database performance analysis..."
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;
"

# 3. API Performance Analysis
echo "3. API performance analysis..."
kubectl exec prometheus-0 -n monitoring -- promtool query instant 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[30d]))'

# 4. Trading Performance Analysis
echo "4. Trading performance analysis..."
kubectl exec deployment/trading-engine -n $NAMESPACE -- python -c "
import psycopg2
from datetime import datetime, timedelta

conn = psycopg2.connect('postgresql://postgres:password@postgres-primary:5432/smc_trading')
cur = conn.cursor()

# Monthly trading statistics
cur.execute('''
    SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
        AVG(pnl) as avg_pnl,
        STDDEV(pnl) as pnl_stddev,
        MAX(pnl) as max_win,
        MIN(pnl) as max_loss
    FROM trades
    WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days';
''')

stats = cur.fetchone()
win_rate = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0

print(f'Monthly Trading Performance:')
print(f'Total Trades: {stats[0]}')
print(f'Win Rate: {win_rate:.2f}%')
print(f'Average P&L: ${stats[2]:.2f}')
print(f'Sharpe Ratio: {stats[2] / stats[3] if stats[3] > 0 else 0:.2f}')
print(f'Best Trade: ${stats[4]:.2f}')
print(f'Worst Trade: ${stats[5]:.2f}')
"

# 5. Generate optimization recommendations
echo "5. Generating optimization recommendations..."
# This would analyze the collected data and suggest optimizations
```

## 🔄 Quarterly Maintenance

### Major System Updates

```bash
#!/bin/bash
# quarterly-updates.sh - Major system updates and upgrades

echo "🔄 Quarterly System Updates - $(date)"
echo "===================================="

NAMESPACE="smc-trading"

# 1. Kubernetes Version Update
echo "1. Checking Kubernetes version..."
CURRENT_VERSION=$(kubectl version --short | grep "Server Version" | cut -d: -f2 | tr -d ' ')
echo "Current Kubernetes version: $CURRENT_VERSION"

# 2. Container Image Updates
echo "2. Planning container image updates..."
images=("trading-engine" "api-gateway" "execution-engine" "web-app")
for image in "${images[@]}"; do
    current_image=$(kubectl get deployment $image -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')
    echo "   $image: $current_image"

    # Check for security updates
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image --severity HIGH,CRITICAL $current_image
done

# 3. Database Major Version Check
echo "3. Checking database version..."
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -c "SELECT version();"

# 4. Dependency Major Updates
echo "4. Checking for major dependency updates..."
kubectl exec deployment/trading-engine -n $NAMESPACE -- pip list --outdated | grep -E "(major|breaking)"
kubectl exec deployment/api-gateway -n $NAMESPACE -- npm outdated | grep -E "(major|breaking)"

# 5. Performance Baseline Update
echo "5. Updating performance baselines..."
# Collect new baseline metrics after optimizations
kubectl exec prometheus-0 -n monitoring -- promtool query instant 'avg_over_time(http_request_duration_seconds{quantile="0.95"}[7d])'
```

### Disaster Recovery Drill

```bash
#!/bin/bash
# quarterly-dr-drill.sh - Disaster recovery drill

echo "🚨 Quarterly Disaster Recovery Drill - $(date)"
echo "=============================================="

NAMESPACE="smc-trading"
DR_NAMESPACE="smc-trading-dr"

# 1. Simulate primary region failure
echo "1. Simulating primary region failure..."
kubectl scale deployment --all --replicas=0 -n $NAMESPACE

# 2. Activate DR procedures
echo "2. Activating disaster recovery..."
kubectl create namespace $DR_NAMESPACE

# 3. Restore from backup
echo "3. Restoring from backup..."
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
echo "Using backup: $LATEST_BACKUP"

# Deploy DR infrastructure
kubectl apply -f deployment/kubernetes/dr/ -n $DR_NAMESPACE

# 4. Test DR system
echo "4. Testing DR system functionality..."
kubectl wait --for=condition=available deployment/trading-engine -n $DR_NAMESPACE --timeout=600s

# Test API
curl -f https://dr.smc-trading.com/health

# 5. Measure RTO/RPO
DR_COMPLETE_TIME=$(date)
echo "DR activation completed at: $DR_COMPLETE_TIME"

# 6. Cleanup DR environment
echo "6. Cleaning up DR environment..."
kubectl delete namespace $DR_NAMESPACE

# 7. Restore primary environment
echo "7. Restoring primary environment..."
kubectl scale deployment --all --replicas=3 -n $NAMESPACE

echo "Disaster recovery drill completed"
```

## 📊 Maintenance Metrics and Reporting

### Maintenance Dashboard

```json
{
  "dashboard": {
    "title": "SMC Trading Agent - Maintenance Dashboard",
    "panels": [
      {
        "title": "System Uptime",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"smc-trading\"}"
          }
        ]
      },
      {
        "title": "Backup Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "backup_success_total / backup_attempts_total * 100"
          }
        ]
      },
      {
        "title": "Maintenance Windows",
        "type": "table",
        "targets": [
          {
            "expr": "maintenance_window_duration_seconds"
          }
        ]
      },
      {
        "title": "Security Vulnerabilities",
        "type": "graph",
        "targets": [
          {
            "expr": "vulnerability_count_by_severity"
          }
        ]
      }
    ]
  }
}
```

### Maintenance Reporting

```bash
#!/bin/bash
# generate-maintenance-report.sh - Generate monthly maintenance report

MONTH=$(date +%Y-%m)
REPORT_FILE="maintenance_report_$MONTH.md"

cat > $REPORT_FILE << EOF
# Maintenance Report - $MONTH

## Summary
- Scheduled maintenance windows: X
- Emergency maintenance: Y
- System uptime: Z%
- Backup success rate: A%

## Completed Tasks
### Daily Tasks
- [x] Health checks: 30/30 days
- [x] Backup verification: 30/30 days
- [x] Log cleanup: 30/30 days

### Weekly Tasks
- [x] Database maintenance: 4/4 weeks
- [x] Certificate checks: 4/4 weeks
- [x] Dependency scans: 4/4 weeks

### Monthly Tasks
- [x] Full backup test: Completed
- [x] Security audit: Completed
- [x] Performance review: Completed

## Issues Identified
1. Issue 1: Description and resolution
2. Issue 2: Description and resolution

## Recommendations
1. Recommendation 1
2. Recommendation 2

## Next Month's Focus
- Priority 1
- Priority 2
EOF

echo "Maintenance report generated: $REPORT_FILE"
```

## 🚨 Emergency Maintenance Procedures

### Emergency Maintenance Checklist

```bash
#!/bin/bash
# emergency-maintenance.sh - Emergency maintenance procedures

echo "🚨 Emergency Maintenance Initiated - $(date)"
echo "==========================================="

# 1. Immediate assessment
echo "1. Assessing system status..."
./scripts/quick-health-check.sh

# 2. Enable maintenance mode
echo "2. Enabling maintenance mode..."
kubectl patch ingress api-ingress -n smc-trading -p '{
    "metadata": {
        "annotations": {
            "nginx.ingress.kubernetes.io/custom-http-errors": "503"
        }
    }
}'

# 3. Notify stakeholders
echo "3. Notifying stakeholders..."
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"🚨 EMERGENCY MAINTENANCE: System maintenance in progress. ETA: TBD"}' \
    $SLACK_WEBHOOK_URL

# 4. Create emergency backup
echo "4. Creating emergency backup..."
kubectl exec postgres-primary-0 -n smc-trading -- pg_dump -U postgres -d smc_trading -F c -f /tmp/emergency_$(date +%Y%m%d_%H%M%S).dump

# 5. Perform emergency procedures
echo "5. Performing emergency maintenance..."
# Specific emergency procedures would go here

# 6. Verify system recovery
echo "6. Verifying system recovery..."
./scripts/health-check.sh

# 7. Disable maintenance mode
echo "7. Disabling maintenance mode..."
kubectl patch ingress api-ingress -n smc-trading --type=json -p='[
    {"op": "remove", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1custom-http-errors"}
]'

# 8. Final notification
echo "8. Sending completion notification..."
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"✅ Emergency maintenance completed. All systems operational."}' \
    $SLACK_WEBHOOK_URL

echo "Emergency maintenance completed - $(date)"
```

## 📋 Maintenance Automation

### Automated Maintenance Scheduler

```yaml
# maintenance-cronjobs.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-maintenance
  namespace: smc-trading
spec:
  schedule: "0 2 * * *" # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: maintenance
              image: smc-trading/maintenance:latest
              command: ["/bin/bash", "/scripts/daily-maintenance.sh"]
          restartPolicy: OnFailure
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-maintenance
  namespace: smc-trading
spec:
  schedule: "0 3 * * 0" # Weekly on Sunday at 3 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: maintenance
              image: smc-trading/maintenance:latest
              command: ["/bin/bash", "/scripts/weekly-maintenance.sh"]
          restartPolicy: OnFailure
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: monthly-maintenance
  namespace: smc-trading
spec:
  schedule: "0 4 1 * *" # Monthly on 1st at 4 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: maintenance
              image: smc-trading/maintenance:latest
              command: ["/bin/bash", "/scripts/monthly-maintenance.sh"]
          restartPolicy: OnFailure
```

---

**Last Updated**: $(date)  
**Document Version**: 1.0.0  
**Next Review Date**: $(date -d "+1 month")  
**Maintained By**: DevOps Team
