# System Diagnostics Guide

## Overview

This guide provides comprehensive diagnostic procedures and commands for troubleshooting the SMC Trading Agent system. Use these tools to identify, analyze, and resolve system issues.

## 🔍 Quick Health Check

### Automated Health Check Script

```bash
#!/bin/bash
# quick-health-check.sh - Rapid system health assessment

echo "🏥 SMC Trading Agent - Quick Health Check"
echo "========================================"

NAMESPACE="smc-trading"
ISSUES_FOUND=0

# 1. Kubernetes Cluster Health
echo "1. Checking Kubernetes cluster..."
if kubectl cluster-info &>/dev/null; then
    echo "   ✅ Kubernetes cluster is accessible"
else
    echo "   ❌ Kubernetes cluster is not accessible"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 2. Node Status
echo "2. Checking node status..."
NOT_READY_NODES=$(kubectl get nodes | grep -v Ready | grep -v NAME | wc -l)
if [ $NOT_READY_NODES -eq 0 ]; then
    echo "   ✅ All nodes are ready"
else
    echo "   ❌ $NOT_READY_NODES nodes are not ready"
    kubectl get nodes | grep -v Ready
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 3. Pod Status
echo "3. Checking pod status..."
UNHEALTHY_PODS=$(kubectl get pods -n $NAMESPACE | grep -v Running | grep -v Completed | grep -v NAME | wc -l)
if [ $UNHEALTHY_PODS -eq 0 ]; then
    echo "   ✅ All pods are running"
else
    echo "   ❌ $UNHEALTHY_PODS pods are not running"
    kubectl get pods -n $NAMESPACE | grep -v Running | grep -v Completed
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 4. Service Connectivity
echo "4. Checking service connectivity..."
if curl -f -s --max-time 5 https://api.smc-trading.com/health &>/dev/null; then
    echo "   ✅ API is responding"
else
    echo "   ❌ API is not responding"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 5. Database Connectivity
echo "5. Checking database..."
if kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_isready -q &>/dev/null; then
    echo "   ✅ Database is accessible"
else
    echo "   ❌ Database is not accessible"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# 6. Redis Connectivity
echo "6. Checking Redis..."
if kubectl exec redis-0 -n $NAMESPACE -- redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "   ✅ Redis is responding"
else
    echo "   ❌ Redis is not responding"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Summary
echo ""
if [ $ISSUES_FOUND -eq 0 ]; then
    echo "🎉 System is healthy - no issues found!"
    exit 0
else
    echo "⚠️  Found $ISSUES_FOUND issues that need attention"
    echo "Run detailed diagnostics for more information"
    exit 1
fi
```

## 🔧 Detailed Diagnostic Commands

### Kubernetes Diagnostics

#### Cluster Information

```bash
# Basic cluster info
kubectl cluster-info
kubectl version --short

# Node details
kubectl get nodes -o wide
kubectl describe nodes

# Resource usage
kubectl top nodes
kubectl top pods -A --sort-by=cpu
kubectl top pods -A --sort-by=memory

# Cluster events
kubectl get events --sort-by='.lastTimestamp' -A | tail -20
```

#### Pod Diagnostics

```bash
# Pod status in SMC namespace
kubectl get pods -n smc-trading -o wide

# Detailed pod information
kubectl describe pod <pod-name> -n smc-trading

# Pod logs
kubectl logs <pod-name> -n smc-trading --tail=100
kubectl logs <pod-name> -n smc-trading --previous  # Previous container logs

# Pod resource usage
kubectl top pod <pod-name> -n smc-trading --containers

# Pod shell access
kubectl exec -it <pod-name> -n smc-trading -- /bin/bash
```

#### Service and Network Diagnostics

```bash
# Service status
kubectl get services -n smc-trading
kubectl describe service <service-name> -n smc-trading

# Endpoint information
kubectl get endpoints -n smc-trading
kubectl describe endpoints <service-name> -n smc-trading

# Ingress status
kubectl get ingress -n smc-trading
kubectl describe ingress <ingress-name> -n smc-trading

# Network policies
kubectl get networkpolicies -n smc-trading
```

### Application-Level Diagnostics

#### Trading Engine Diagnostics

```bash
# Check trading engine health
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import requests
import sys
try:
    response = requests.get('http://localhost:8000/health', timeout=5)
    print(f'Status: {response.status_code}')
    print(f'Response: {response.json()}')
    sys.exit(0 if response.status_code == 200 else 1)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"

# Check SMC indicators
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
from smc_detector.indicators import SMCIndicators
try:
    smc = SMCIndicators()
    print('SMC indicators loaded successfully')
    print(f'Available methods: {[m for m in dir(smc) if not m.startswith(\"_\")]}')
except Exception as e:
    print(f'Error loading SMC indicators: {e}')
"

# Check exchange connectivity
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import ccxt
exchanges = ['binance', 'bybit']
for exchange_name in exchanges:
    try:
        exchange = getattr(ccxt, exchange_name)({'sandbox': True})
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f'{exchange_name}: Connected - BTC/USDT = {ticker[\"last\"]}')
    except Exception as e:
        print(f'{exchange_name}: Error - {e}')
"
```

#### API Gateway Diagnostics

```bash
# Check API gateway health
kubectl exec deployment/api-gateway -n smc-trading -- curl -f http://localhost:3000/health

# Check middleware functionality
kubectl exec deployment/api-gateway -n smc-trading -- node -e "
const express = require('express');
console.log('Express version:', express.version || 'Unknown');
console.log('Node.js version:', process.version);
console.log('Memory usage:', process.memoryUsage());
"

# Test JWT functionality
kubectl exec deployment/api-gateway -n smc-trading -- node -e "
const jwt = require('jsonwebtoken');
const token = jwt.sign({test: true}, 'test-secret');
const decoded = jwt.verify(token, 'test-secret');
console.log('JWT test:', decoded.test ? 'PASS' : 'FAIL');
"
```

#### Database Diagnostics

```bash
# Basic database connectivity
kubectl exec postgres-primary-0 -n smc-trading -- pg_isready -U postgres

# Database version and status
kubectl exec postgres-primary-0 -n smc-trading -- psql -U postgres -c "SELECT version();"
kubectl exec postgres-primary-0 -n smc-trading -- psql -U postgres -c "SELECT pg_is_in_recovery();"

# Connection statistics
kubectl exec postgres-primary-0 -n smc-trading -- psql -U postgres -c "
SELECT
    count(*) as total_connections,
    count(*) FILTER (WHERE state = 'active') as active_connections,
    count(*) FILTER (WHERE state = 'idle') as idle_connections
FROM pg_stat_activity;
"

# Database size and table statistics
kubectl exec postgres-primary-0 -n smc-trading -- psql -U postgres -d smc_trading -c "
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
"

# Slow queries
kubectl exec postgres-primary-0 -n smc-trading -- psql -U postgres -d smc_trading -c "
SELECT
    query,
    mean_exec_time,
    calls,
    total_exec_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Lock information
kubectl exec postgres-primary-0 -n smc-trading -- psql -U postgres -d smc_trading -c "
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;
"
```

#### Redis Diagnostics

```bash
# Basic Redis connectivity
kubectl exec redis-0 -n smc-trading -- redis-cli ping

# Redis information
kubectl exec redis-0 -n smc-trading -- redis-cli info server
kubectl exec redis-0 -n smc-trading -- redis-cli info memory
kubectl exec redis-0 -n smc-trading -- redis-cli info clients
kubectl exec redis-0 -n smc-trading -- redis-cli info stats

# Key statistics
kubectl exec redis-0 -n smc-trading -- redis-cli --scan --pattern "*" | head -20
kubectl exec redis-0 -n smc-trading -- redis-cli dbsize

# Memory usage by key pattern
kubectl exec redis-0 -n smc-trading -- redis-cli --bigkeys

# Slow log
kubectl exec redis-0 -n smc-trading -- redis-cli slowlog get 10
```

## 📊 Performance Diagnostics

### System Resource Monitoring

```bash
#!/bin/bash
# performance-diagnostics.sh - System performance analysis

echo "📊 Performance Diagnostics"
echo "========================="

NAMESPACE="smc-trading"

# CPU and Memory usage
echo "1. Resource Usage:"
kubectl top nodes
echo ""
kubectl top pods -n $NAMESPACE --sort-by=cpu | head -10
echo ""
kubectl top pods -n $NAMESPACE --sort-by=memory | head -10

# Network connectivity tests
echo "2. Network Performance:"
echo "Testing exchange connectivity..."
for exchange in "api.binance.com" "api.bybit.com" "api-fxtrade.oanda.com"; do
    response_time=$(curl -w "%{time_total}" -o /dev/null -s $exchange/ping 2>/dev/null || echo "timeout")
    echo "   $exchange: ${response_time}s"
done

# Database performance
echo "3. Database Performance:"
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins + n_tup_upd + n_tup_del as total_writes
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY total_writes DESC
LIMIT 5;
"

# Redis performance
echo "4. Redis Performance:"
kubectl exec redis-0 -n $NAMESPACE -- redis-cli info stats | grep -E "(total_commands_processed|instantaneous_ops_per_sec|keyspace_hits|keyspace_misses)"

# API response times
echo "5. API Response Times:"
for endpoint in "/health" "/v1/status" "/v1/account/balance"; do
    response_time=$(curl -w "%{time_total}" -o /dev/null -s "https://api.smc-trading.com$endpoint" 2>/dev/null || echo "error")
    echo "   $endpoint: ${response_time}s"
done
```

### Application Performance Metrics

```bash
# Trading engine performance
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import psutil
import time

# CPU usage
cpu_percent = psutil.cpu_percent(interval=1)
print(f'CPU Usage: {cpu_percent}%')

# Memory usage
memory = psutil.virtual_memory()
print(f'Memory Usage: {memory.percent}% ({memory.used / 1024**3:.2f}GB / {memory.total / 1024**3:.2f}GB)')

# Disk usage
disk = psutil.disk_usage('/')
print(f'Disk Usage: {disk.percent}% ({disk.used / 1024**3:.2f}GB / {disk.total / 1024**3:.2f}GB)')

# Network I/O
net_io = psutil.net_io_counters()
print(f'Network - Sent: {net_io.bytes_sent / 1024**2:.2f}MB, Received: {net_io.bytes_recv / 1024**2:.2f}MB')
"

# Check for memory leaks
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import gc
import sys

# Garbage collection stats
print('Garbage Collection Stats:')
for i, count in enumerate(gc.get_count()):
    print(f'  Generation {i}: {count} objects')

# Memory usage by object type
print('\\nTop object types by count:')
import collections
type_counts = collections.Counter(type(obj).__name__ for obj in gc.get_objects())
for obj_type, count in type_counts.most_common(10):
    print(f'  {obj_type}: {count}')
"
```

## 🔍 Log Analysis

### Centralized Log Collection

```bash
#!/bin/bash
# collect-logs.sh - Collect logs from all components

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="logs_$TIMESTAMP"
NAMESPACE="smc-trading"

mkdir -p $LOG_DIR

echo "Collecting logs from SMC Trading Agent..."

# Collect pod logs
for pod in $(kubectl get pods -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}'); do
    echo "Collecting logs from $pod..."
    kubectl logs $pod -n $NAMESPACE --tail=1000 > "$LOG_DIR/${pod}.log" 2>&1

    # Previous container logs if available
    kubectl logs $pod -n $NAMESPACE --previous --tail=1000 > "$LOG_DIR/${pod}_previous.log" 2>&1 || true
done

# Collect events
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' > "$LOG_DIR/events.log"

# Collect resource descriptions
kubectl describe pods -n $NAMESPACE > "$LOG_DIR/pod_descriptions.log"
kubectl describe services -n $NAMESPACE > "$LOG_DIR/service_descriptions.log"

# System information
kubectl get nodes -o yaml > "$LOG_DIR/nodes.yaml"
kubectl top nodes > "$LOG_DIR/node_resources.log"
kubectl top pods -n $NAMESPACE > "$LOG_DIR/pod_resources.log"

# Create archive
tar -czf "smc_logs_$TIMESTAMP.tar.gz" $LOG_DIR/
echo "Logs collected in: smc_logs_$TIMESTAMP.tar.gz"
```

### Log Analysis Scripts

```bash
#!/bin/bash
# analyze-logs.sh - Analyze logs for common issues

LOG_FILE=${1:-"trading-engine.log"}

echo "🔍 Log Analysis for: $LOG_FILE"
echo "================================"

# Error analysis
echo "1. Error Summary:"
grep -i error "$LOG_FILE" | cut -d' ' -f1-3 | sort | uniq -c | sort -nr | head -10

# Warning analysis
echo "2. Warning Summary:"
grep -i warning "$LOG_FILE" | cut -d' ' -f1-3 | sort | uniq -c | sort -nr | head -10

# Exception analysis
echo "3. Exception Summary:"
grep -i exception "$LOG_FILE" | cut -d' ' -f1-3 | sort | uniq -c | sort -nr | head -10

# Performance issues
echo "4. Performance Issues:"
grep -E "(timeout|slow|latency)" "$LOG_FILE" | wc -l
echo "   Timeout/Slow operations found: $(grep -E '(timeout|slow|latency)' "$LOG_FILE" | wc -l)"

# Connection issues
echo "5. Connection Issues:"
grep -E "(connection|disconnect|refused)" "$LOG_FILE" | wc -l
echo "   Connection-related issues: $(grep -E '(connection|disconnect|refused)' "$LOG_FILE" | wc -l)"

# Recent critical events
echo "6. Recent Critical Events (last 100 lines):"
tail -100 "$LOG_FILE" | grep -E "(CRITICAL|ERROR|FATAL)" | tail -5
```

## 🌐 Network Diagnostics

### Connectivity Testing

```bash
#!/bin/bash
# network-diagnostics.sh - Network connectivity testing

echo "🌐 Network Diagnostics"
echo "====================="

NAMESPACE="smc-trading"

# Internal service connectivity
echo "1. Internal Service Connectivity:"
services=("postgres-primary" "redis" "api-gateway" "trading-engine")
for service in "${services[@]}"; do
    if kubectl exec deployment/api-gateway -n $NAMESPACE -- nc -z $service 5432 2>/dev/null; then
        echo "   ✅ $service is reachable"
    else
        echo "   ❌ $service is not reachable"
    fi
done

# External API connectivity
echo "2. External API Connectivity:"
external_apis=(
    "api.binance.com:443"
    "api.bybit.com:443"
    "api-fxtrade.oanda.com:443"
)

for api in "${external_apis[@]}"; do
    host=$(echo $api | cut -d: -f1)
    port=$(echo $api | cut -d: -f2)

    if kubectl exec deployment/trading-engine -n $NAMESPACE -- nc -z $host $port 2>/dev/null; then
        echo "   ✅ $api is reachable"
    else
        echo "   ❌ $api is not reachable"
    fi
done

# DNS resolution
echo "3. DNS Resolution:"
dns_names=("api.smc-trading.com" "monitoring.smc-trading.com")
for dns in "${dns_names[@]}"; do
    if kubectl exec deployment/api-gateway -n $NAMESPACE -- nslookup $dns >/dev/null 2>&1; then
        echo "   ✅ $dns resolves correctly"
    else
        echo "   ❌ $dns resolution failed"
    fi
done

# Ingress connectivity
echo "4. Ingress Connectivity:"
if curl -f -s --max-time 10 https://api.smc-trading.com/health >/dev/null; then
    echo "   ✅ External API is accessible"
else
    echo "   ❌ External API is not accessible"
fi
```

### Network Performance Testing

```bash
# Bandwidth testing between pods
kubectl exec deployment/trading-engine -n smc-trading -- iperf3 -c postgres-primary -t 10

# Latency testing
kubectl exec deployment/trading-engine -n smc-trading -- ping -c 10 postgres-primary

# DNS lookup performance
kubectl exec deployment/api-gateway -n smc-trading -- dig api.smc-trading.com
```

## 🔐 Security Diagnostics

### Security Audit

```bash
#!/bin/bash
# security-audit.sh - Security configuration audit

echo "🔐 Security Audit"
echo "================="

NAMESPACE="smc-trading"

# Check RBAC configuration
echo "1. RBAC Configuration:"
kubectl get rolebindings -n $NAMESPACE
kubectl get clusterrolebindings | grep smc-trading

# Check network policies
echo "2. Network Policies:"
kubectl get networkpolicies -n $NAMESPACE

# Check pod security contexts
echo "3. Pod Security Contexts:"
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.securityContext}{"\n"}{end}'

# Check secrets
echo "4. Secrets Audit:"
kubectl get secrets -n $NAMESPACE
kubectl describe secrets -n $NAMESPACE | grep -E "(Name:|Type:|Data)"

# Check service accounts
echo "5. Service Accounts:"
kubectl get serviceaccounts -n $NAMESPACE

# Check for privileged containers
echo "6. Privileged Containers:"
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].securityContext.privileged}{"\n"}{end}' | grep true || echo "   ✅ No privileged containers found"
```

### Certificate Diagnostics

```bash
# Check TLS certificates
kubectl get certificates -n smc-trading
kubectl describe certificates -n smc-trading

# Check certificate expiration
openssl s_client -connect api.smc-trading.com:443 -servername api.smc-trading.com 2>/dev/null | openssl x509 -noout -dates

# Check ingress TLS configuration
kubectl get ingress -n smc-trading -o yaml | grep -A 10 tls
```

## 📋 Diagnostic Report Generation

### Automated Diagnostic Report

```bash
#!/bin/bash
# generate-diagnostic-report.sh - Generate comprehensive diagnostic report

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="diagnostic_report_$TIMESTAMP.md"
NAMESPACE="smc-trading"

cat > $REPORT_FILE << EOF
# SMC Trading Agent - Diagnostic Report
Generated: $(date)
Namespace: $NAMESPACE

## System Overview
EOF

# Cluster information
echo "### Kubernetes Cluster" >> $REPORT_FILE
kubectl cluster-info >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Node status
echo "### Node Status" >> $REPORT_FILE
kubectl get nodes -o wide >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Pod status
echo "### Pod Status" >> $REPORT_FILE
kubectl get pods -n $NAMESPACE -o wide >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Service status
echo "### Service Status" >> $REPORT_FILE
kubectl get services -n $NAMESPACE >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Resource usage
echo "### Resource Usage" >> $REPORT_FILE
kubectl top nodes >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE
kubectl top pods -n $NAMESPACE >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Recent events
echo "### Recent Events" >> $REPORT_FILE
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20 >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

# Health checks
echo "### Health Checks" >> $REPORT_FILE
echo "API Health:" >> $REPORT_FILE
curl -f -s https://api.smc-trading.com/health >> $REPORT_FILE 2>&1 || echo "API health check failed" >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "Database Health:" >> $REPORT_FILE
kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_isready >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

echo "Redis Health:" >> $REPORT_FILE
kubectl exec redis-0 -n $NAMESPACE -- redis-cli ping >> $REPORT_FILE 2>&1
echo "" >> $REPORT_FILE

echo "Diagnostic report generated: $REPORT_FILE"
```

## 🚨 Alert Integration

### Prometheus Queries for Diagnostics

```yaml
# Common diagnostic queries
queries:
  - name: "High CPU Usage"
    query: 'rate(container_cpu_usage_seconds_total{namespace="smc-trading"}[5m]) * 100 > 80'

  - name: "High Memory Usage"
    query: 'container_memory_usage_bytes{namespace="smc-trading"} / container_spec_memory_limit_bytes * 100 > 90'

  - name: "Pod Restart Rate"
    query: 'rate(kube_pod_container_status_restarts_total{namespace="smc-trading"}[15m]) > 0'

  - name: "API Error Rate"
    query: 'rate(http_requests_total{status=~"5.."}[5m]) > 0.01'

  - name: "Database Connection Count"
    query: 'pg_stat_activity_count{namespace="smc-trading"}'

  - name: "Redis Memory Usage"
    query: 'redis_memory_used_bytes{namespace="smc-trading"} / redis_memory_max_bytes * 100'
```

### Automated Diagnostic Triggers

```bash
# Create diagnostic automation
cat > diagnostic-automation.yaml << EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: diagnostic-automation
  namespace: smc-trading
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: diagnostics
            image: smc-trading/diagnostics:latest
            command:
            - /bin/bash
            - -c
            - |
              ./quick-health-check.sh
              if [ $? -ne 0 ]; then
                ./generate-diagnostic-report.sh
                # Send alert to operations team
                curl -X POST -H 'Content-type: application/json' \
                  --data '{"text":"🚨 Automated diagnostics detected issues. Report generated."}' \
                  $SLACK_WEBHOOK_URL
              fi
          restartPolicy: OnFailure
EOF

kubectl apply -f diagnostic-automation.yaml
```

---

**Last Updated**: $(date)  
**Document Version**: 1.0.0  
**Maintained By**: DevOps Team
