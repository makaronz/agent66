# Incident Response Playbook

## Overview

This playbook provides step-by-step procedures for responding to critical incidents in the SMC Trading Agent system. All incidents are classified by severity and have specific response procedures.

## Incident Classification

### Severity Levels

| Level             | Description                                           | Response Time | Examples                                 |
| ----------------- | ----------------------------------------------------- | ------------- | ---------------------------------------- |
| **P0 - Critical** | System completely down, data loss, security breach    | 5 minutes     | Complete system outage, trading halted   |
| **P1 - High**     | Major functionality impaired, significant user impact | 15 minutes    | Database performance issues, API errors  |
| **P2 - Medium**   | Partial functionality affected, moderate user impact  | 1 hour        | WebSocket disconnections, slow responses |
| **P3 - Low**      | Minor issues, minimal user impact                     | 4 hours       | UI glitches, non-critical warnings       |

## P0 - Critical Incident Response

### 🚨 Complete System Outage

**Immediate Actions (0-5 minutes):**

1. **Acknowledge and Assess**

   ```bash
   # Check overall system status
   kubectl get nodes
   kubectl get pods --all-namespaces | grep -v Running

   # Check external dependencies
   curl -I https://api.binance.com/api/v3/ping
   curl -I https://api.bybit.com/v2/public/time
   ```

2. **Emergency Trading Halt**

   ```bash
   # Immediately halt all trading activities
   kubectl exec -it deployment/trading-engine -n smc-trading -- python -c "
   import redis
   r = redis.Redis(host='redis', port=6379)
   r.set('emergency_halt', 'true')
   r.expire('emergency_halt', 3600)  # 1 hour expiry
   print('Emergency trading halt activated')
   "
   ```

3. **Notify Stakeholders**

   ```bash
   # Send immediate alert
   curl -X POST -H 'Content-type: application/json' \
       --data '{"text":"🚨 P0 INCIDENT: Complete system outage detected. Trading halted. Investigation in progress."}' \
       $SLACK_CRITICAL_WEBHOOK

   # Update status page
   curl -X POST "https://api.statuspage.io/v1/pages/$PAGE_ID/incidents" \
       -H "Authorization: OAuth $STATUSPAGE_TOKEN" \
       -d '{
           "incident": {
               "name": "System Outage",
               "status": "investigating",
               "impact_override": "critical",
               "body": "We are investigating a complete system outage. Trading has been halted as a precaution."
           }
       }'
   ```

**Investigation and Recovery (5-15 minutes):**

4. **Identify Root Cause**

   ```bash
   # Check Kubernetes cluster health
   kubectl cluster-info
   kubectl describe nodes

   # Check recent events
   kubectl get events --sort-by='.lastTimestamp' -A | tail -20

   # Check resource usage
   kubectl top nodes
   kubectl top pods -A --sort-by=cpu

   # Check logs for errors
   kubectl logs -f deployment/trading-engine -n smc-trading --tail=100 | grep -i error
   kubectl logs -f deployment/api-gateway -n smc-trading --tail=100 | grep -i error
   ```

5. **Execute Recovery Procedures**

   ```bash
   # If pods are failing, restart deployments
   kubectl rollout restart deployment/trading-engine -n smc-trading
   kubectl rollout restart deployment/api-gateway -n smc-trading
   kubectl rollout restart deployment/execution-engine -n smc-trading

   # If database issues, check database health
   kubectl exec -it postgres-primary -n smc-trading -- pg_isready
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -c "SELECT version();"

   # If Redis issues, restart Redis
   kubectl rollout restart statefulset/redis -n smc-trading
   ```

6. **Verify System Recovery**

   ```bash
   # Wait for all pods to be ready
   kubectl wait --for=condition=ready pod -l app=trading-engine -n smc-trading --timeout=300s
   kubectl wait --for=condition=ready pod -l app=api-gateway -n smc-trading --timeout=300s

   # Test API endpoints
   curl -f https://api.smc-trading.com/health
   curl -f https://api.smc-trading.com/v1/status

   # Test database connectivity
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "SELECT COUNT(*) FROM users;"

   # Test Redis connectivity
   kubectl exec -it redis-0 -n smc-trading -- redis-cli ping
   ```

7. **Resume Trading (Only after full verification)**

   ```bash
   # Remove emergency halt
   kubectl exec -it deployment/trading-engine -n smc-trading -- python -c "
   import redis
   r = redis.Redis(host='redis', port=6379)
   r.delete('emergency_halt')
   print('Emergency trading halt removed')
   "

   # Verify trading engine is processing
   kubectl logs -f deployment/trading-engine -n smc-trading | grep -i "trading resumed"
   ```

### 🔒 Security Breach

**Immediate Actions (0-5 minutes):**

1. **Isolate Affected Systems**

   ```bash
   # Block all external traffic
   kubectl patch ingress api-ingress -n smc-trading -p '{"spec":{"rules":[]}}'

   # Scale down all public-facing services
   kubectl scale deployment api-gateway --replicas=0 -n smc-trading
   kubectl scale deployment web-app --replicas=0 -n smc-trading
   ```

2. **Preserve Evidence**

   ```bash
   # Capture current system state
   kubectl get all -n smc-trading -o yaml > incident-$(date +%Y%m%d_%H%M%S)-k8s-state.yaml

   # Capture logs
   kubectl logs deployment/api-gateway -n smc-trading --since=1h > incident-$(date +%Y%m%d_%H%M%S)-api-logs.txt
   kubectl logs deployment/trading-engine -n smc-trading --since=1h > incident-$(date +%Y%m%d_%H%M%S)-trading-logs.txt

   # Capture network connections
   kubectl exec -it deployment/api-gateway -n smc-trading -- netstat -tulpn > incident-$(date +%Y%m%d_%H%M%S)-netstat.txt
   ```

3. **Notify Security Team**

   ```bash
   # Immediate security alert
   curl -X POST -H 'Content-type: application/json' \
       --data '{"text":"🚨 SECURITY INCIDENT: Potential breach detected. All systems isolated. Security team respond immediately."}' \
       $SLACK_SECURITY_WEBHOOK

   # Email security team
   echo "Security incident detected at $(date). All systems have been isolated. Please respond immediately." | \
       mail -s "URGENT: Security Incident - SMC Trading Agent" security@smc-trading.com
   ```

**Investigation Phase (5-30 minutes):**

4. **Forensic Analysis**

   ```bash
   # Check for unauthorized access
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "
   SELECT username, login_time, ip_address, user_agent
   FROM user_sessions
   WHERE login_time > NOW() - INTERVAL '2 hours'
   ORDER BY login_time DESC;
   "

   # Check for suspicious API calls
   kubectl logs deployment/api-gateway -n smc-trading --since=2h | grep -E "(401|403|429)" | tail -50

   # Check for unusual trading activity
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "
   SELECT user_id, symbol, quantity, price, timestamp
   FROM trades
   WHERE timestamp > NOW() - INTERVAL '2 hours'
   AND (quantity > 10000 OR ABS(price - market_price) / market_price > 0.1)
   ORDER BY timestamp DESC;
   "
   ```

5. **Containment Actions**

   ```bash
   # Rotate all API keys immediately
   kubectl create job api-key-rotation --from=cronjob/api-key-rotation -n smc-trading

   # Force logout all users
   kubectl exec -it redis-0 -n smc-trading -- redis-cli FLUSHDB 1  # Session database

   # Disable compromised accounts (if identified)
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "
   UPDATE users SET is_active = false WHERE id IN ('suspicious-user-id-1', 'suspicious-user-id-2');
   "
   ```

### 💾 Data Loss Incident

**Immediate Actions (0-5 minutes):**

1. **Stop All Write Operations**

   ```bash
   # Scale down all services that write to database
   kubectl scale deployment trading-engine --replicas=0 -n smc-trading
   kubectl scale deployment api-gateway --replicas=0 -n smc-trading
   kubectl scale deployment data-pipeline --replicas=0 -n smc-trading
   ```

2. **Assess Data Loss Scope**

   ```bash
   # Check database status
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "
   SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
   FROM pg_stat_user_tables
   ORDER BY schemaname, tablename;
   "

   # Check for recent backups
   aws s3 ls s3://smc-trading-backups/daily/ | tail -10

   # Verify backup integrity
   LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
   aws s3 cp s3://smc-trading-backups/daily/$LATEST_BACKUP /tmp/
   gunzip -t /tmp/$LATEST_BACKUP
   ```

3. **Initiate Data Recovery**

   ```bash
   # Follow disaster recovery procedures
   # See: docs/operations/runbooks/backup-recovery.md

   # Create emergency backup of current state (if possible)
   kubectl exec postgres-primary -n smc-trading -- pg_dump -U postgres -d smc_trading -F c -f /tmp/emergency_$(date +%Y%m%d_%H%M%S).dump
   ```

## P1 - High Severity Incidents

### 📊 Database Performance Degradation

**Response Procedure:**

1. **Immediate Assessment (0-5 minutes)**

   ```bash
   # Check database connections
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -c "
   SELECT count(*) as active_connections, state
   FROM pg_stat_activity
   GROUP BY state;
   "

   # Identify slow queries
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -c "
   SELECT query, mean_exec_time, calls, total_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   "
   ```

2. **Immediate Mitigation (5-10 minutes)**

   ```bash
   # Kill long-running queries if necessary
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -c "
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'active'
   AND query_start < NOW() - INTERVAL '5 minutes'
   AND query NOT LIKE '%pg_stat_activity%';
   "

   # Restart connection pooler
   kubectl rollout restart deployment/pgbouncer -n smc-trading
   ```

3. **Scale Resources (10-15 minutes)**
   ```bash
   # Increase database resources
   kubectl patch statefulset postgres-primary -n smc-trading -p '{
       "spec": {
           "template": {
               "spec": {
                   "containers": [{
                       "name": "postgres",
                       "resources": {
                           "limits": {"cpu": "4", "memory": "8Gi"},
                           "requests": {"cpu": "2", "memory": "4Gi"}
                       }
                   }]
               }
           }
       }
   }'
   ```

### 🔌 Exchange API Failures

**Response Procedure:**

1. **Activate Failover (0-2 minutes)**

   ```bash
   # Check exchange status
   curl -w "Time: %{time_total}s, Status: %{http_code}\n" https://api.binance.com/api/v3/ping
   curl -w "Time: %{time_total}s, Status: %{http_code}\n" https://api.bybit.com/v2/public/time

   # Activate failover to backup exchange
   kubectl exec -it deployment/trading-engine -n smc-trading -- python -c "
   from data_pipeline.exchange_connectors.failover_manager import FailoverManager
   fm = FailoverManager()
   fm.activate_failover('binance', 'bybit')
   print('Failover activated: binance -> bybit')
   "
   ```

2. **Monitor Failover (2-5 minutes)**

   ```bash
   # Check failover status
   kubectl logs -f deployment/trading-engine -n smc-trading | grep -i failover

   # Verify trading continues on backup exchange
   kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "
   SELECT exchange, COUNT(*) as trade_count
   FROM trades
   WHERE timestamp > NOW() - INTERVAL '5 minutes'
   GROUP BY exchange;
   "
   ```

## P2 - Medium Severity Incidents

### 🌐 WebSocket Connection Issues

**Response Procedure:**

1. **Diagnose Connection Issues**

   ```bash
   # Check WebSocket service status
   kubectl get endpoints websocket-service -n smc-trading
   kubectl describe service websocket-service -n smc-trading

   # Test WebSocket connectivity
   wscat -c wss://api.smc-trading.com/ws
   ```

2. **Restart WebSocket Services**

   ```bash
   # Restart WebSocket pods
   kubectl rollout restart deployment/websocket-service -n smc-trading

   # Check ingress configuration
   kubectl describe ingress api-ingress -n smc-trading | grep -A 10 websocket
   ```

### 📈 High API Latency

**Response Procedure:**

1. **Scale API Services**

   ```bash
   # Increase API gateway replicas
   kubectl scale deployment api-gateway --replicas=5 -n smc-trading

   # Enable horizontal pod autoscaling
   kubectl autoscale deployment api-gateway --cpu-percent=70 --min=3 --max=10 -n smc-trading
   ```

2. **Optimize Performance**

   ```bash
   # Check resource usage
   kubectl top pods -n smc-trading -l app=api-gateway

   # Increase resource limits if needed
   kubectl patch deployment api-gateway -n smc-trading -p '{
       "spec": {
           "template": {
               "spec": {
                   "containers": [{
                       "name": "api-gateway",
                       "resources": {
                           "limits": {"cpu": "2", "memory": "4Gi"},
                           "requests": {"cpu": "1", "memory": "2Gi"}
                       }
                   }]
               }
           }
       }
   }'
   ```

## Communication Templates

### Initial Incident Notification

```
🚨 INCIDENT ALERT - P{SEVERITY}

**Incident ID**: INC-{TIMESTAMP}
**Severity**: P{SEVERITY} - {SEVERITY_NAME}
**Status**: Investigating
**Impact**: {IMPACT_DESCRIPTION}
**Started**: {START_TIME}

**Initial Assessment**:
{BRIEF_DESCRIPTION}

**Actions Taken**:
- {ACTION_1}
- {ACTION_2}

**Next Update**: In {TIME_INTERVAL}

**Incident Commander**: {IC_NAME}
**War Room**: {SLACK_CHANNEL}
```

### Status Update Template

```
📊 INCIDENT UPDATE - P{SEVERITY}

**Incident ID**: INC-{TIMESTAMP}
**Status**: {CURRENT_STATUS}
**Duration**: {ELAPSED_TIME}

**Progress Update**:
{PROGRESS_DESCRIPTION}

**Actions Completed**:
- {COMPLETED_ACTION_1}
- {COMPLETED_ACTION_2}

**Next Steps**:
- {NEXT_ACTION_1}
- {NEXT_ACTION_2}

**ETA to Resolution**: {ESTIMATED_TIME}
**Next Update**: In {TIME_INTERVAL}
```

### Resolution Notification

```
✅ INCIDENT RESOLVED - P{SEVERITY}

**Incident ID**: INC-{TIMESTAMP}
**Status**: Resolved
**Total Duration**: {TOTAL_DURATION}
**Resolution Time**: {RESOLUTION_TIME}

**Root Cause**:
{ROOT_CAUSE_SUMMARY}

**Resolution**:
{RESOLUTION_SUMMARY}

**Follow-up Actions**:
- {FOLLOWUP_ACTION_1}
- {FOLLOWUP_ACTION_2}

**Post-Mortem**: {POST_MORTEM_LINK}
```

## Post-Incident Procedures

### 1. Immediate Post-Resolution (0-2 hours)

- [ ] Verify all systems are fully operational
- [ ] Remove any temporary workarounds
- [ ] Update monitoring and alerting if needed
- [ ] Send resolution notification to stakeholders
- [ ] Begin collecting data for post-mortem

### 2. Post-Mortem Process (24-48 hours)

- [ ] Schedule post-mortem meeting within 24 hours
- [ ] Prepare timeline of events
- [ ] Identify root cause(s)
- [ ] Document lessons learned
- [ ] Create action items for prevention
- [ ] Update runbooks and procedures

### 3. Follow-up Actions (1-2 weeks)

- [ ] Implement preventive measures
- [ ] Update monitoring and alerting
- [ ] Conduct training if needed
- [ ] Review and update incident response procedures
- [ ] Share learnings with broader team

## Escalation Matrix

### On-Call Rotation

| Role                       | Primary          | Secondary        | Escalation           |
| -------------------------- | ---------------- | ---------------- | -------------------- |
| **Incident Commander**     | @oncall-ic       | @backup-ic       | @engineering-manager |
| **DevOps Engineer**        | @oncall-devops   | @backup-devops   | @devops-lead         |
| **Database Administrator** | @oncall-dba      | @backup-dba      | @data-team-lead      |
| **Security Engineer**      | @oncall-security | @backup-security | @security-manager    |

### Escalation Triggers

- **15 minutes**: No progress on P0 incident
- **30 minutes**: No progress on P1 incident
- **1 hour**: Customer escalation or media attention
- **2 hours**: Regulatory implications or data breach

### Emergency Contacts

- **Engineering Manager**: +1-XXX-XXX-XXXX
- **CTO**: +1-XXX-XXX-XXXX (P0 only)
- **CEO**: +1-XXX-XXX-XXXX (Business critical only)
- **Legal**: legal@smc-trading.com (Security/compliance issues)

---

**Last Updated**: $(date)  
**Document Version**: 1.0.0  
**Next Review Date**: $(date -d "+1 month")  
**Maintained By**: DevOps Team
