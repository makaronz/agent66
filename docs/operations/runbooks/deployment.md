# Deployment Runbook

## Overview

This runbook provides comprehensive procedures for deploying the SMC Trading Agent system to production environments. It covers initial deployment, updates, rollbacks, and maintenance deployments.

## Pre-Deployment Checklist

### 🔍 Code Quality Gates

- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests completed successfully
- [ ] Security scan completed without critical vulnerabilities
- [ ] Code review approved by at least 2 senior engineers
- [ ] Performance tests completed (if applicable)
- [ ] Database migration scripts tested in staging

### 🏗️ Infrastructure Readiness

- [ ] Kubernetes cluster health verified
- [ ] Database backup completed within last 6 hours
- [ ] Monitoring and alerting systems operational
- [ ] Load balancer health checks configured
- [ ] SSL certificates valid and not expiring within 30 days
- [ ] DNS configuration verified

### 📋 Deployment Preparation

- [ ] Deployment window scheduled and communicated
- [ ] Rollback plan prepared and tested
- [ ] Stakeholders notified of deployment
- [ ] Emergency contacts available during deployment
- [ ] Status page prepared for updates

## Production Deployment Procedures

### 1. Initial Production Deployment

#### Step 1: Environment Setup

```bash
# Set deployment environment
export ENVIRONMENT=production
export NAMESPACE=smc-trading
export KUBECONFIG=~/.kube/config-prod

# Verify cluster access
kubectl cluster-info
kubectl get nodes
kubectl get namespaces | grep $NAMESPACE
```

#### Step 2: Create Namespace and RBAC

```bash
# Create production namespace
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
  labels:
    name: $NAMESPACE
    environment: production
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: smc-trading-sa
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: $NAMESPACE
  name: smc-trading-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: smc-trading-rolebinding
  namespace: $NAMESPACE
subjects:
- kind: ServiceAccount
  name: smc-trading-sa
  namespace: $NAMESPACE
roleRef:
  kind: Role
  name: smc-trading-role
  apiGroup: rbac.authorization.k8s.io
EOF
```

#### Step 3: Deploy Secrets and ConfigMaps

```bash
# Create secrets from environment variables
kubectl create secret generic smc-secrets -n $NAMESPACE \
  --from-literal=DATABASE_PASSWORD="$DATABASE_PASSWORD" \
  --from-literal=JWT_SECRET="$JWT_SECRET" \
  --from-literal=BINANCE_API_KEY="$BINANCE_API_KEY" \
  --from-literal=BINANCE_API_SECRET="$BINANCE_API_SECRET" \
  --from-literal=BYBIT_API_KEY="$BYBIT_API_KEY" \
  --from-literal=BYBIT_API_SECRET="$BYBIT_API_SECRET" \
  --from-literal=OANDA_API_KEY="$OANDA_API_KEY" \
  --from-literal=REDIS_PASSWORD="$REDIS_PASSWORD"

# Create configuration
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: smc-config
  namespace: $NAMESPACE
data:
  DATABASE_HOST: "postgresql-primary.smc-trading.svc.cluster.local"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "smc_trading"
  REDIS_HOST: "redis-cluster.smc-trading.svc.cluster.local"
  REDIS_PORT: "6379"
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  TRADING_ENABLED: "true"
  MAX_POSITION_SIZE: "10000"
  RISK_LIMIT_PERCENT: "2.0"
EOF
```

#### Step 4: Deploy Database

```bash
# Deploy PostgreSQL with TimescaleDB
kubectl apply -f deployment/kubernetes/postgresql-ha-cluster.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres-primary -n $NAMESPACE --timeout=600s

# Run database migrations
kubectl exec -it postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -f /docker-entrypoint-initdb.d/001_initial_schema.sql
kubectl exec -it postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -f /docker-entrypoint-initdb.d/002_performance_indexes.sql

# Verify database setup
kubectl exec -it postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "SELECT version();"
kubectl exec -it postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

#### Step 5: Deploy Redis Cluster

```bash
# Deploy Redis cluster
kubectl apply -f deployment/kubernetes/redis-cluster.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s

# Verify Redis cluster
kubectl exec -it redis-0 -n $NAMESPACE -- redis-cli ping
kubectl exec -it redis-0 -n $NAMESPACE -- redis-cli cluster info
```

#### Step 6: Deploy Application Services

```bash
# Deploy in dependency order
echo "Deploying Trading Engine..."
kubectl apply -f deployment/kubernetes/trading-engine-deployment.yaml
kubectl wait --for=condition=available deployment/trading-engine -n $NAMESPACE --timeout=300s

echo "Deploying Execution Engine..."
kubectl apply -f deployment/kubernetes/execution-engine-deployment.yaml
kubectl wait --for=condition=available deployment/execution-engine -n $NAMESPACE --timeout=300s

echo "Deploying API Gateway..."
kubectl apply -f deployment/kubernetes/api-gateway-deployment.yaml
kubectl wait --for=condition=available deployment/api-gateway -n $NAMESPACE --timeout=300s

echo "Deploying Data Pipeline..."
kubectl apply -f deployment/kubernetes/data-pipeline-deployment.yaml
kubectl wait --for=condition=available deployment/data-pipeline -n $NAMESPACE --timeout=300s

echo "Deploying Web Application..."
kubectl apply -f deployment/kubernetes/web-app-deployment.yaml
kubectl wait --for=condition=available deployment/web-app -n $NAMESPACE --timeout=300s
```

#### Step 7: Configure Ingress and Load Balancer

```bash
# Deploy ingress controller
kubectl apply -f deployment/kubernetes/ingress-controller.yaml

# Deploy application ingress
kubectl apply -f deployment/kubernetes/ingress.yaml

# Verify ingress
kubectl get ingress -n $NAMESPACE
kubectl describe ingress api-ingress -n $NAMESPACE
```

#### Step 8: Deploy Monitoring Stack

```bash
# Deploy Prometheus
kubectl apply -f deployment/kubernetes/prometheus-deployment.yaml
kubectl wait --for=condition=available deployment/prometheus -n $NAMESPACE --timeout=300s

# Deploy Grafana
kubectl apply -f deployment/kubernetes/grafana-deployment.yaml
kubectl wait --for=condition=available deployment/grafana -n $NAMESPACE --timeout=300s

# Deploy AlertManager
kubectl apply -f deployment/kubernetes/alertmanager-deployment.yaml
kubectl wait --for=condition=available deployment/alertmanager -n $NAMESPACE --timeout=300s
```

#### Step 9: Post-Deployment Verification

```bash
# Run comprehensive health check
./scripts/health-check.sh

# Test API endpoints
curl -f https://api.smc-trading.com/health
curl -f https://api.smc-trading.com/v1/status

# Test WebSocket connections
wscat -c wss://api.smc-trading.com/ws

# Verify monitoring
curl -f https://monitoring.smc-trading.com/api/v1/query?query=up

# Check all pods are running
kubectl get pods -n $NAMESPACE
```

### 2. Application Updates and Rolling Deployments

#### Step 1: Pre-Update Verification

```bash
# Verify current system health
kubectl get pods -n $NAMESPACE | grep -v Running
if [ $? -eq 1 ]; then
    echo "✅ All pods are running"
else
    echo "❌ Some pods are not running. Investigate before proceeding."
    exit 1
fi

# Check recent error rates
kubectl exec -it prometheus-0 -n $NAMESPACE -- promtool query instant 'rate(http_requests_total{status=~"5.."}[5m])'

# Verify backup completion
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
BACKUP_AGE=$(( $(date +%s) - $(date -d "$(echo $LATEST_BACKUP | cut -d'_' -f2 | sed 's/.dump.gz//')" +%s) ))
if [ $BACKUP_AGE -lt 21600 ]; then  # 6 hours
    echo "✅ Recent backup available: $LATEST_BACKUP"
else
    echo "❌ No recent backup found. Creating emergency backup..."
    kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_dump -U postgres -d smc_trading -F c -f /tmp/pre_deployment_$(date +%Y%m%d_%H%M%S).dump
fi
```

#### Step 2: Rolling Update Procedure

```bash
# Set new image version
NEW_VERSION="v1.2.3"
echo "Deploying version: $NEW_VERSION"

# Update trading engine
kubectl set image deployment/trading-engine trading-engine=smc-trading/trading-engine:$NEW_VERSION -n $NAMESPACE
kubectl rollout status deployment/trading-engine -n $NAMESPACE --timeout=300s

# Verify trading engine health
kubectl exec -it deployment/trading-engine -n $NAMESPACE -- python -c "
import requests
response = requests.get('http://localhost:8000/health')
assert response.status_code == 200
print('Trading engine health check passed')
"

# Update execution engine
kubectl set image deployment/execution-engine execution-engine=smc-trading/execution-engine:$NEW_VERSION -n $NAMESPACE
kubectl rollout status deployment/execution-engine -n $NAMESPACE --timeout=300s

# Update API gateway
kubectl set image deployment/api-gateway api-gateway=smc-trading/api-gateway:$NEW_VERSION -n $NAMESPACE
kubectl rollout status deployment/api-gateway -n $NAMESPACE --timeout=300s

# Test API after each update
curl -f https://api.smc-trading.com/health || {
    echo "❌ API health check failed. Initiating rollback..."
    kubectl rollout undo deployment/api-gateway -n $NAMESPACE
    exit 1
}

# Update remaining services
kubectl set image deployment/data-pipeline data-pipeline=smc-trading/data-pipeline:$NEW_VERSION -n $NAMESPACE
kubectl set image deployment/web-app web-app=smc-trading/web-app:$NEW_VERSION -n $NAMESPACE

# Wait for all deployments to complete
kubectl rollout status deployment/data-pipeline -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/web-app -n $NAMESPACE --timeout=300s
```

#### Step 3: Post-Update Verification

```bash
# Comprehensive system test
echo "Running post-deployment verification..."

# Check all pods are running with new version
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}' | grep $NEW_VERSION

# Test critical functionality
echo "Testing trading functionality..."
kubectl exec -it deployment/trading-engine -n $NAMESPACE -- python -c "
from smc_detector.indicators import SMCIndicators
smc = SMCIndicators()
print('SMC indicators loaded successfully')
"

# Test database connectivity
kubectl exec -it postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "SELECT COUNT(*) FROM trades WHERE timestamp > NOW() - INTERVAL '1 hour';"

# Test Redis connectivity
kubectl exec -it redis-0 -n $NAMESPACE -- redis-cli ping

# Monitor error rates for 10 minutes
echo "Monitoring error rates for 10 minutes..."
for i in {1..10}; do
    ERROR_RATE=$(kubectl exec -it prometheus-0 -n $NAMESPACE -- promtool query instant 'rate(http_requests_total{status=~"5.."}[1m])' | grep -o '[0-9.]*' | head -1)
    echo "Minute $i: Error rate = $ERROR_RATE"
    if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
        echo "❌ High error rate detected. Consider rollback."
    fi
    sleep 60
done

echo "✅ Deployment completed successfully"
```

### 3. Database Migration Deployments

#### Step 1: Pre-Migration Backup

```bash
# Create pre-migration backup
MIGRATION_BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
echo "Creating pre-migration backup: $MIGRATION_BACKUP_DATE"

kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_dump -U postgres -d smc_trading -F c -b -v -f /tmp/pre_migration_$MIGRATION_BACKUP_DATE.dump

# Copy backup to safe location
kubectl cp $NAMESPACE/postgres-primary-0:/tmp/pre_migration_$MIGRATION_BACKUP_DATE.dump ./backups/
aws s3 cp ./backups/pre_migration_$MIGRATION_BACKUP_DATE.dump s3://smc-trading-backups/migrations/

# Verify backup integrity
kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_restore --list /tmp/pre_migration_$MIGRATION_BACKUP_DATE.dump | head -10
```

#### Step 2: Execute Migration

```bash
# Stop applications that write to database
kubectl scale deployment trading-engine --replicas=0 -n $NAMESPACE
kubectl scale deployment api-gateway --replicas=0 -n $NAMESPACE
kubectl scale deployment data-pipeline --replicas=0 -n $NAMESPACE

# Wait for connections to close
sleep 30

# Execute migration scripts
for migration_file in supabase/migrations/*.sql; do
    echo "Executing migration: $migration_file"
    kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -f /migrations/$(basename $migration_file)

    # Check for errors
    if [ $? -ne 0 ]; then
        echo "❌ Migration failed: $migration_file"
        echo "Initiating rollback..."
        kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_restore -U postgres -d smc_trading --clean /tmp/pre_migration_$MIGRATION_BACKUP_DATE.dump
        exit 1
    fi
done

# Verify migration success
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;"

# Restart applications
kubectl scale deployment trading-engine --replicas=3 -n $NAMESPACE
kubectl scale deployment api-gateway --replicas=3 -n $NAMESPACE
kubectl scale deployment data-pipeline --replicas=2 -n $NAMESPACE

# Wait for applications to be ready
kubectl wait --for=condition=available deployment/trading-engine -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=available deployment/api-gateway -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=available deployment/data-pipeline -n $NAMESPACE --timeout=300s
```

### 4. Rollback Procedures

#### Immediate Rollback (Application Only)

```bash
# Rollback to previous version
echo "Initiating immediate rollback..."

# Rollback all deployments
kubectl rollout undo deployment/trading-engine -n $NAMESPACE
kubectl rollout undo deployment/execution-engine -n $NAMESPACE
kubectl rollout undo deployment/api-gateway -n $NAMESPACE
kubectl rollout undo deployment/data-pipeline -n $NAMESPACE
kubectl rollout undo deployment/web-app -n $NAMESPACE

# Wait for rollback to complete
kubectl rollout status deployment/trading-engine -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/execution-engine -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/api-gateway -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/data-pipeline -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/web-app -n $NAMESPACE --timeout=300s

# Verify rollback success
curl -f https://api.smc-trading.com/health
echo "✅ Rollback completed successfully"
```

#### Database Rollback (Critical)

```bash
# This should only be used in extreme circumstances
echo "⚠️  CRITICAL: Initiating database rollback"

# Stop all applications
kubectl scale deployment trading-engine --replicas=0 -n $NAMESPACE
kubectl scale deployment api-gateway --replicas=0 -n $NAMESPACE
kubectl scale deployment data-pipeline --replicas=0 -n $NAMESPACE

# Restore from pre-migration backup
kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_restore -U postgres -d smc_trading --clean /tmp/pre_migration_$MIGRATION_BACKUP_DATE.dump

# Verify restoration
kubectl exec postgres-primary-0 -n $NAMESPACE -- psql -U postgres -d smc_trading -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# Restart applications with previous version
kubectl rollout undo deployment/trading-engine -n $NAMESPACE
kubectl rollout undo deployment/api-gateway -n $NAMESPACE
kubectl rollout undo deployment/data-pipeline -n $NAMESPACE

kubectl scale deployment trading-engine --replicas=3 -n $NAMESPACE
kubectl scale deployment api-gateway --replicas=3 -n $NAMESPACE
kubectl scale deployment data-pipeline --replicas=2 -n $NAMESPACE

echo "✅ Database rollback completed"
```

## Deployment Automation Scripts

### 1. Automated Deployment Script

```bash
#!/bin/bash
# deploy.sh - Automated deployment script

set -e

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
NAMESPACE="smc-trading"

echo "🚀 Starting deployment to $ENVIRONMENT with version $VERSION"

# Pre-deployment checks
echo "📋 Running pre-deployment checks..."
./scripts/pre-deployment-check.sh $ENVIRONMENT

# Create backup
echo "💾 Creating pre-deployment backup..."
./scripts/create-backup.sh

# Deploy application
echo "🔄 Deploying application..."
kubectl set image deployment/trading-engine trading-engine=smc-trading/trading-engine:$VERSION -n $NAMESPACE
kubectl set image deployment/execution-engine execution-engine=smc-trading/execution-engine:$VERSION -n $NAMESPACE
kubectl set image deployment/api-gateway api-gateway=smc-trading/api-gateway:$VERSION -n $NAMESPACE
kubectl set image deployment/data-pipeline data-pipeline=smc-trading/data-pipeline:$VERSION -n $NAMESPACE
kubectl set image deployment/web-app web-app=smc-trading/web-app:$VERSION -n $NAMESPACE

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
kubectl rollout status deployment/trading-engine -n $NAMESPACE --timeout=600s
kubectl rollout status deployment/execution-engine -n $NAMESPACE --timeout=600s
kubectl rollout status deployment/api-gateway -n $NAMESPACE --timeout=600s
kubectl rollout status deployment/data-pipeline -n $NAMESPACE --timeout=600s
kubectl rollout status deployment/web-app -n $NAMESPACE --timeout=600s

# Post-deployment verification
echo "✅ Running post-deployment verification..."
./scripts/post-deployment-check.sh

echo "🎉 Deployment completed successfully!"
```

### 2. Health Check Script

```bash
#!/bin/bash
# health-check.sh - Comprehensive health check

NAMESPACE="smc-trading"
FAILED_CHECKS=0

echo "🏥 SMC Trading Agent Health Check"
echo "================================="

# Check pod status
echo "1. Checking pod status..."
UNHEALTHY_PODS=$(kubectl get pods -n $NAMESPACE | grep -v Running | grep -v Completed | wc -l)
if [ $UNHEALTHY_PODS -eq 0 ]; then
    echo "   ✅ All pods are running"
else
    echo "   ❌ $UNHEALTHY_PODS pods are not running"
    kubectl get pods -n $NAMESPACE | grep -v Running | grep -v Completed
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check API health
echo "2. Checking API health..."
if curl -f -s https://api.smc-trading.com/health > /dev/null; then
    echo "   ✅ API is responding"
else
    echo "   ❌ API health check failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check database connectivity
echo "3. Checking database connectivity..."
if kubectl exec postgres-primary-0 -n $NAMESPACE -- pg_isready -q; then
    echo "   ✅ Database is accessible"
else
    echo "   ❌ Database connectivity failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check Redis connectivity
echo "4. Checking Redis connectivity..."
if kubectl exec redis-0 -n $NAMESPACE -- redis-cli ping | grep -q PONG; then
    echo "   ✅ Redis is responding"
else
    echo "   ❌ Redis connectivity failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check trading engine functionality
echo "5. Checking trading engine..."
TRADING_STATUS=$(kubectl exec deployment/trading-engine -n $NAMESPACE -- python -c "
import requests
try:
    response = requests.get('http://localhost:8000/v1/status', timeout=5)
    print(response.status_code)
except:
    print('error')
")

if [ "$TRADING_STATUS" = "200" ]; then
    echo "   ✅ Trading engine is operational"
else
    echo "   ❌ Trading engine check failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Summary
echo ""
echo "Health Check Summary:"
if [ $FAILED_CHECKS -eq 0 ]; then
    echo "🎉 All health checks passed!"
    exit 0
else
    echo "⚠️  $FAILED_CHECKS health checks failed"
    exit 1
fi
```

## Deployment Monitoring and Alerting

### Deployment Success Metrics

```yaml
# deployment-alerts.yaml
groups:
  - name: deployment_alerts
    rules:
      - alert: DeploymentFailed
        expr: kube_deployment_status_replicas_unavailable > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Deployment has unavailable replicas"
          description: "Deployment {{ $labels.deployment }} has {{ $value }} unavailable replicas"

      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod is crash looping"
          description: "Pod {{ $labels.pod }} is restarting frequently"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/second"
```

### Deployment Dashboard

```json
{
  "dashboard": {
    "title": "SMC Trading Agent - Deployment Dashboard",
    "panels": [
      {
        "title": "Pod Status",
        "type": "stat",
        "targets": [
          {
            "expr": "kube_deployment_status_replicas_available{namespace=\"smc-trading\"}"
          }
        ]
      },
      {
        "title": "Deployment Timeline",
        "type": "graph",
        "targets": [
          {
            "expr": "kube_deployment_status_observed_generation{namespace=\"smc-trading\"}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      }
    ]
  }
}
```

## Maintenance Windows

### Scheduled Maintenance Procedure

```bash
#!/bin/bash
# maintenance-window.sh - Scheduled maintenance procedure

MAINTENANCE_START=$(date)
echo "🔧 Starting scheduled maintenance: $MAINTENANCE_START"

# 1. Notify users (30 minutes before)
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"🔧 Scheduled maintenance starting in 30 minutes. Trading will be temporarily unavailable."}' \
    $SLACK_WEBHOOK_URL

# Update status page
curl -X POST "https://api.statuspage.io/v1/pages/$PAGE_ID/incidents" \
    -H "Authorization: OAuth $STATUSPAGE_TOKEN" \
    -d '{
        "incident": {
            "name": "Scheduled Maintenance",
            "status": "scheduled",
            "impact_override": "maintenance",
            "body": "Scheduled maintenance window for system updates."
        }
    }'

# 2. Enable maintenance mode
kubectl patch ingress api-ingress -n smc-trading -p '{
    "metadata": {
        "annotations": {
            "nginx.ingress.kubernetes.io/custom-http-errors": "503",
            "nginx.ingress.kubernetes.io/default-backend": "maintenance-page"
        }
    }
}'

# 3. Gracefully stop trading
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import redis
r = redis.Redis(host='redis', port=6379)
r.set('maintenance_mode', 'true')
print('Maintenance mode enabled')
"

# Wait for active trades to complete
sleep 300

# 4. Perform maintenance tasks
echo "Performing maintenance tasks..."

# Update system packages
kubectl exec -it postgres-primary-0 -n smc-trading -- apt-get update && apt-get upgrade -y

# Optimize database
kubectl exec postgres-primary-0 -n smc-trading -- psql -U postgres -d smc_trading -c "VACUUM ANALYZE;"

# Clear old logs
kubectl exec deployment/trading-engine -n smc-trading -- find /var/log -name "*.log" -mtime +7 -delete

# 5. Restart services
kubectl rollout restart deployment/trading-engine -n smc-trading
kubectl rollout restart deployment/api-gateway -n smc-trading

# Wait for services to be ready
kubectl wait --for=condition=available deployment/trading-engine -n smc-trading --timeout=300s
kubectl wait --for=condition=available deployment/api-gateway -n smc-trading --timeout=300s

# 6. Disable maintenance mode
kubectl exec deployment/trading-engine -n smc-trading -- python -c "
import redis
r = redis.Redis(host='redis', port=6379)
r.delete('maintenance_mode')
print('Maintenance mode disabled')
"

# Remove maintenance page
kubectl patch ingress api-ingress -n smc-trading --type=json -p='[
    {"op": "remove", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1custom-http-errors"},
    {"op": "remove", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1default-backend"}
]'

# 7. Verify system health
./scripts/health-check.sh

# 8. Notify completion
MAINTENANCE_END=$(date)
echo "✅ Scheduled maintenance completed: $MAINTENANCE_END"

curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"✅ Scheduled maintenance completed successfully. All systems operational."}' \
    $SLACK_WEBHOOK_URL
```

---

**Last Updated**: $(date)  
**Document Version**: 1.0.0  
**Next Review Date**: $(date -d "+1 month")  
**Maintained By**: DevOps Team
