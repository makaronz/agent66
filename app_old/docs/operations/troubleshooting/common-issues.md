# Common System Issues - Troubleshooting Guide

## Overview

This guide covers the most frequently encountered issues in the SMC Trading Agent system and their solutions.

## 🔴 Critical Issues

### 1. Trading Engine Not Responding

**Symptoms:**

- API endpoints returning 503 errors
- No new trades being executed
- WebSocket connections failing

**Diagnosis:**

```bash
# Check pod status
kubectl get pods -n smc-trading -l app=trading-engine

# Check logs for errors
kubectl logs -f deployment/trading-engine -n smc-trading --tail=100

# Check resource usage
kubectl top pods -n smc-trading
```

**Solutions:**

1. **Memory Issues:**

   ```bash
   # Scale up memory limits
   kubectl patch deployment trading-engine -n smc-trading -p '{"spec":{"template":{"spec":{"containers":[{"name":"trading-engine","resources":{"limits":{"memory":"4Gi"}}}]}}}}'

   # Restart deployment
   kubectl rollout restart deployment/trading-engine -n smc-trading
   ```

2. **Database Connection Issues:**

   ```bash
   # Check database connectivity
   kubectl exec -it deployment/trading-engine -n smc-trading -- python -c "
   import psycopg2
   conn = psycopg2.connect('postgresql://user:pass@db:5432/smc_trading')
   print('Database connection: OK')
   "

   # Restart PgBouncer if needed
   kubectl rollout restart deployment/pgbouncer -n smc-trading
   ```

3. **Exchange API Issues:**
   ```bash
   # Check exchange connectivity
   kubectl exec -it deployment/trading-engine -n smc-trading -- python -c "
   import ccxt
   exchange = ccxt.binance({'sandbox': True})
   print(exchange.fetch_ticker('BTC/USDT'))
   "
   ```

### 2. Database Performance Degradation

**Symptoms:**

- Slow query responses (>1s)
- High CPU usage on database pods
- Connection pool exhaustion

**Diagnosis:**

```sql
-- Connect to database
kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading

-- Check active connections
SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';

-- Identify slow queries
SELECT query, mean_exec_time, calls, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes
SELECT schemaname,tablename,attname,n_distinct,correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;
```

**Solutions:**

1. **Connection Pool Tuning:**

   ```bash
   # Update PgBouncer configuration
   kubectl edit configmap pgbouncer-config -n smc-trading
   # Increase pool_size and max_client_conn

   # Restart PgBouncer
   kubectl rollout restart deployment/pgbouncer -n smc-trading
   ```

2. **Query Optimization:**

   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_trades_timestamp ON trades(timestamp);
   CREATE INDEX CONCURRENTLY idx_trades_user_id_timestamp ON trades(user_id, timestamp);

   -- Update table statistics
   ANALYZE trades;
   ANALYZE smc_signals;
   ```

3. **Scale Database Resources:**
   ```bash
   # Increase database resources
   kubectl patch statefulset postgres-primary -n smc-trading -p '{"spec":{"template":{"spec":{"containers":[{"name":"postgres","resources":{"limits":{"cpu":"4","memory":"8Gi"}}}]}}}}'
   ```

### 3. Redis Connection Issues

**Symptoms:**

- Session timeouts
- Cache misses
- Authentication failures

**Diagnosis:**

```bash
# Check Redis pod status
kubectl get pods -n smc-trading -l app=redis

# Check Redis connectivity
kubectl exec -it redis-0 -n smc-trading -- redis-cli ping

# Check Redis memory usage
kubectl exec -it redis-0 -n smc-trading -- redis-cli info memory

# Check connection count
kubectl exec -it redis-0 -n smc-trading -- redis-cli info clients
```

**Solutions:**

1. **Memory Issues:**

   ```bash
   # Check memory usage
   kubectl exec -it redis-0 -n smc-trading -- redis-cli info memory

   # Clear cache if needed (emergency only)
   kubectl exec -it redis-0 -n smc-trading -- redis-cli FLUSHDB

   # Scale Redis memory
   kubectl patch statefulset redis -n smc-trading -p '{"spec":{"template":{"spec":{"containers":[{"name":"redis","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
   ```

2. **Connection Limit Issues:**
   ```bash
   # Increase max connections in Redis config
   kubectl exec -it redis-0 -n smc-trading -- redis-cli CONFIG SET maxclients 10000
   ```

## 🟡 Warning Level Issues

### 4. High API Latency

**Symptoms:**

- API response times >500ms
- User complaints about slow interface
- Timeout errors in logs

**Diagnosis:**

```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s "https://api.smc-trading.com/health"

# Check load balancer metrics
kubectl describe service api-gateway -n smc-trading

# Check pod resource usage
kubectl top pods -n smc-trading -l app=api-gateway
```

**Solutions:**

1. **Scale API Gateway:**

   ```bash
   # Increase replicas
   kubectl scale deployment api-gateway --replicas=5 -n smc-trading

   # Enable horizontal pod autoscaling
   kubectl autoscale deployment api-gateway --cpu-percent=70 --min=3 --max=10 -n smc-trading
   ```

2. **Optimize Database Queries:**
   ```bash
   # Enable query logging temporarily
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -c "SELECT pg_reload_conf();"
   ```

### 5. WebSocket Connection Drops

**Symptoms:**

- Frequent reconnections in frontend
- Real-time data delays
- WebSocket error messages

**Diagnosis:**

```bash
# Check WebSocket service
kubectl get endpoints websocket-service -n smc-trading

# Check nginx ingress logs
kubectl logs -f deployment/nginx-ingress-controller -n ingress-nginx | grep websocket

# Test WebSocket connection
wscat -c wss://api.smc-trading.com/ws
```

**Solutions:**

1. **Nginx Configuration:**

   ```yaml
   # Update ingress with proper WebSocket headers
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     annotations:
       nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
       nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
       nginx.ingress.kubernetes.io/websocket-services: "websocket-service"
   ```

2. **Application-Level Fixes:**

   ```bash
   # Restart WebSocket service
   kubectl rollout restart deployment/websocket-service -n smc-trading

   # Check for memory leaks
   kubectl exec -it deployment/websocket-service -n smc-trading -- ps aux
   ```

## 🟢 Information Level Issues

### 6. Log Volume Issues

**Symptoms:**

- Disk space warnings
- Log rotation failures
- Missing log entries

**Solutions:**

```bash
# Check log volume usage
kubectl exec -it deployment/trading-engine -n smc-trading -- df -h /var/log

# Rotate logs manually
kubectl exec -it deployment/trading-engine -n smc-trading -- logrotate -f /etc/logrotate.conf

# Adjust log levels
kubectl set env deployment/trading-engine LOG_LEVEL=WARNING -n smc-trading
```

### 7. Certificate Expiration Warnings

**Symptoms:**

- SSL certificate warnings
- Browser security alerts
- API authentication issues

**Solutions:**

```bash
# Check certificate expiration
kubectl get certificates -n smc-trading

# Force certificate renewal
kubectl delete certificate api-tls -n smc-trading
kubectl apply -f k8s/certificates.yaml

# Verify certificate
openssl s_client -connect api.smc-trading.com:443 -servername api.smc-trading.com
```

## Diagnostic Commands Reference

### System Health Check

```bash
#!/bin/bash
# health-check.sh - Quick system health verification

echo "=== SMC Trading Agent Health Check ==="

# Check all pods
echo "1. Pod Status:"
kubectl get pods -n smc-trading

# Check services
echo "2. Service Status:"
kubectl get services -n smc-trading

# Check ingress
echo "3. Ingress Status:"
kubectl get ingress -n smc-trading

# Check persistent volumes
echo "4. Storage Status:"
kubectl get pv,pvc -n smc-trading

# Check resource usage
echo "5. Resource Usage:"
kubectl top nodes
kubectl top pods -n smc-trading

# Test API endpoints
echo "6. API Health:"
curl -f https://api.smc-trading.com/health || echo "API health check failed"

# Test database connectivity
echo "7. Database Connectivity:"
kubectl exec -it postgres-primary -n smc-trading -- pg_isready

# Test Redis connectivity
echo "8. Redis Connectivity:"
kubectl exec -it redis-0 -n smc-trading -- redis-cli ping

echo "=== Health Check Complete ==="
```

### Performance Monitoring

```bash
#!/bin/bash
# performance-check.sh - System performance analysis

echo "=== Performance Analysis ==="

# CPU and Memory usage
kubectl top nodes
kubectl top pods -n smc-trading --sort-by=cpu
kubectl top pods -n smc-trading --sort-by=memory

# Network connectivity tests
echo "Testing exchange connectivity..."
curl -w "Time: %{time_total}s\n" -o /dev/null -s https://api.binance.com/api/v3/ping
curl -w "Time: %{time_total}s\n" -o /dev/null -s https://api.bybit.com/v2/public/time

# Database performance
kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC LIMIT 10;"

echo "=== Performance Analysis Complete ==="
```

## Escalation Procedures

### When to Escalate

- **Immediate Escalation**: System completely down, security breach, data loss
- **1 Hour Escalation**: Performance degradation affecting >50% users
- **4 Hour Escalation**: Non-critical issues that cannot be resolved

### Escalation Contacts

1. **Level 1**: On-call engineer (Slack: @oncall)
2. **Level 2**: Senior DevOps engineer (Phone: +1-XXX-XXX-XXXX)
3. **Level 3**: Engineering manager (Email: manager@smc-trading.com)
4. **Level 4**: CTO (Emergency only: +1-XXX-XXX-XXXX)

### Escalation Information to Provide

- Issue description and impact
- Steps already taken
- Current system status
- Estimated user impact
- Relevant logs and metrics

---

**Last Updated**: $(date)  
**Document Version**: 1.0.0  
**Maintained By**: DevOps Team
