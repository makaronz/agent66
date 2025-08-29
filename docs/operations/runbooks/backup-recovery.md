# Backup and Disaster Recovery Procedures

## Overview

This document outlines comprehensive backup and disaster recovery procedures for the SMC Trading Agent system. Our recovery objectives are:

- **RTO (Recovery Time Objective)**: 15 minutes
- **RPO (Recovery Point Objective)**: 5 minutes
- **Availability Target**: 99.9% uptime

## Backup Strategy

### 1. Database Backups

#### Automated Daily Backups

```bash
#!/bin/bash
# daily-backup.sh - Automated daily backup script

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgresql"
S3_BUCKET="smc-trading-backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform PostgreSQL backup
kubectl exec postgres-primary -n smc-trading -- pg_dump -U postgres -d smc_trading -F c -b -v -f /tmp/backup_$BACKUP_DATE.dump

# Copy backup from pod to local storage
kubectl cp smc-trading/postgres-primary:/tmp/backup_$BACKUP_DATE.dump $BACKUP_DIR/backup_$BACKUP_DATE.dump

# Compress backup
gzip $BACKUP_DIR/backup_$BACKUP_DATE.dump

# Upload to S3
aws s3 cp $BACKUP_DIR/backup_$BACKUP_DATE.dump.gz s3://$S3_BUCKET/daily/

# Verify backup integrity
gunzip -t $BACKUP_DIR/backup_$BACKUP_DATE.dump.gz
if [ $? -eq 0 ]; then
    echo "Backup verification successful: backup_$BACKUP_DATE.dump.gz"
else
    echo "ERROR: Backup verification failed!"
    # Send alert to operations team
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Database backup verification failed for '$BACKUP_DATE'"}' \
        $SLACK_WEBHOOK_URL
fi

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "backup_*.dump.gz" -mtime +30 -delete
aws s3 ls s3://$S3_BUCKET/daily/ | awk '$1 < "'$(date -d '30 days ago' '+%Y-%m-%d')'" {print $4}' | xargs -I {} aws s3 rm s3://$S3_BUCKET/daily/{}

echo "Daily backup completed: backup_$BACKUP_DATE.dump.gz"
```

#### Point-in-Time Recovery Setup

```bash
# Enable WAL archiving for point-in-time recovery
kubectl exec -it postgres-primary -n smc-trading -- psql -U postgres -c "
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET archive_mode = on;
ALTER SYSTEM SET archive_command = 'aws s3 cp %p s3://smc-trading-backups/wal/%f';
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET wal_keep_segments = 64;
"

# Restart PostgreSQL to apply changes
kubectl rollout restart statefulset/postgres-primary -n smc-trading
```

#### Manual Backup Procedure

```bash
# Emergency manual backup
EMERGENCY_BACKUP_DATE=$(date +%Y%m%d_%H%M%S_emergency)

# Create full database backup
kubectl exec postgres-primary -n smc-trading -- pg_dumpall -U postgres -f /tmp/full_backup_$EMERGENCY_BACKUP_DATE.sql

# Copy to safe location
kubectl cp smc-trading/postgres-primary:/tmp/full_backup_$EMERGENCY_BACKUP_DATE.sql ./emergency_backups/

# Upload to S3 immediately
aws s3 cp ./emergency_backups/full_backup_$EMERGENCY_BACKUP_DATE.sql s3://smc-trading-backups/emergency/

echo "Emergency backup completed: full_backup_$EMERGENCY_BACKUP_DATE.sql"
```

### 2. Application Data Backups

#### Configuration Backups

```bash
#!/bin/bash
# backup-configs.sh - Backup all Kubernetes configurations

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
CONFIG_BACKUP_DIR="/backups/kubernetes"

mkdir -p $CONFIG_BACKUP_DIR

# Backup all Kubernetes resources
kubectl get all,configmaps,secrets,ingress,pv,pvc -n smc-trading -o yaml > $CONFIG_BACKUP_DIR/k8s-resources-$BACKUP_DATE.yaml

# Backup Helm releases
helm list -n smc-trading -o yaml > $CONFIG_BACKUP_DIR/helm-releases-$BACKUP_DATE.yaml

# Backup custom configurations
cp -r /etc/smc-trading/ $CONFIG_BACKUP_DIR/configs-$BACKUP_DATE/

# Create archive
tar -czf $CONFIG_BACKUP_DIR/config-backup-$BACKUP_DATE.tar.gz $CONFIG_BACKUP_DIR/*-$BACKUP_DATE*

# Upload to S3
aws s3 cp $CONFIG_BACKUP_DIR/config-backup-$BACKUP_DATE.tar.gz s3://smc-trading-backups/configs/

echo "Configuration backup completed: config-backup-$BACKUP_DATE.tar.gz"
```

#### Redis Data Backup

```bash
#!/bin/bash
# backup-redis.sh - Backup Redis data

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
REDIS_BACKUP_DIR="/backups/redis"

mkdir -p $REDIS_BACKUP_DIR

# Create Redis backup
kubectl exec redis-0 -n smc-trading -- redis-cli BGSAVE

# Wait for backup to complete
while [ $(kubectl exec redis-0 -n smc-trading -- redis-cli LASTSAVE) -eq $(kubectl exec redis-0 -n smc-trading -- redis-cli LASTSAVE) ]; do
    sleep 1
done

# Copy backup file
kubectl cp smc-trading/redis-0:/data/dump.rdb $REDIS_BACKUP_DIR/redis-backup-$BACKUP_DATE.rdb

# Upload to S3
aws s3 cp $REDIS_BACKUP_DIR/redis-backup-$BACKUP_DATE.rdb s3://smc-trading-backups/redis/

echo "Redis backup completed: redis-backup-$BACKUP_DATE.rdb"
```

## Disaster Recovery Procedures

### 1. Complete System Failure Recovery

#### Step 1: Assess the Situation

```bash
# Check cluster status
kubectl cluster-info
kubectl get nodes
kubectl get namespaces

# Check if any pods are running
kubectl get pods --all-namespaces

# Verify backup availability
aws s3 ls s3://smc-trading-backups/daily/ | tail -5
aws s3 ls s3://smc-trading-backups/configs/ | tail -5
```

#### Step 2: Restore Infrastructure

```bash
# If Kubernetes cluster is down, recreate it
# (This assumes you have infrastructure as code)

# Apply namespace
kubectl apply -f k8s/namespace.yaml

# Restore configurations
LATEST_CONFIG=$(aws s3 ls s3://smc-trading-backups/configs/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp s3://smc-trading-backups/configs/$LATEST_CONFIG ./
tar -xzf $LATEST_CONFIG

# Apply Kubernetes resources
kubectl apply -f k8s-resources-*.yaml
```

#### Step 3: Restore Database

```bash
# Get latest backup
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp s3://smc-trading-backups/daily/$LATEST_BACKUP ./

# Decompress backup
gunzip $LATEST_BACKUP

# Wait for PostgreSQL pod to be ready
kubectl wait --for=condition=ready pod -l app=postgres-primary -n smc-trading --timeout=300s

# Restore database
kubectl cp ${LATEST_BACKUP%.gz} smc-trading/postgres-primary:/tmp/restore.dump
kubectl exec postgres-primary -n smc-trading -- pg_restore -U postgres -d smc_trading -v /tmp/restore.dump

# Verify database restoration
kubectl exec postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "SELECT COUNT(*) FROM trades;"
```

#### Step 4: Restore Redis Data

```bash
# Get latest Redis backup
LATEST_REDIS=$(aws s3 ls s3://smc-trading-backups/redis/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp s3://smc-trading-backups/redis/$LATEST_REDIS ./

# Stop Redis temporarily
kubectl scale statefulset redis --replicas=0 -n smc-trading

# Copy backup to Redis pod
kubectl cp $LATEST_REDIS smc-trading/redis-0:/data/dump.rdb

# Start Redis
kubectl scale statefulset redis --replicas=1 -n smc-trading

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n smc-trading --timeout=300s
```

#### Step 5: Verify System Recovery

```bash
# Check all pods are running
kubectl get pods -n smc-trading

# Test API endpoints
curl -f https://api.smc-trading.com/health

# Test database connectivity
kubectl exec postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "SELECT version();"

# Test Redis connectivity
kubectl exec redis-0 -n smc-trading -- redis-cli ping

# Verify trading engine functionality
curl -f https://api.smc-trading.com/v1/status

echo "System recovery verification completed"
```

### 2. Database-Only Recovery

#### Scenario: Database corruption or data loss

```bash
# Stop all applications that write to database
kubectl scale deployment trading-engine --replicas=0 -n smc-trading
kubectl scale deployment api-gateway --replicas=0 -n smc-trading

# Create emergency backup of current state (if possible)
kubectl exec postgres-primary -n smc-trading -- pg_dump -U postgres -d smc_trading -F c -f /tmp/emergency_$(date +%Y%m%d_%H%M%S).dump

# Drop and recreate database
kubectl exec postgres-primary -n smc-trading -- psql -U postgres -c "DROP DATABASE IF EXISTS smc_trading;"
kubectl exec postgres-primary -n smc-trading -- psql -U postgres -c "CREATE DATABASE smc_trading;"

# Restore from latest backup
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp s3://smc-trading-backups/daily/$LATEST_BACKUP ./
gunzip $LATEST_BACKUP

kubectl cp ${LATEST_BACKUP%.gz} smc-trading/postgres-primary:/tmp/restore.dump
kubectl exec postgres-primary -n smc-trading -- pg_restore -U postgres -d smc_trading -v /tmp/restore.dump

# Restart applications
kubectl scale deployment trading-engine --replicas=3 -n smc-trading
kubectl scale deployment api-gateway --replicas=3 -n smc-trading

# Verify data integrity
kubectl exec postgres-primary -n smc-trading -- psql -U postgres -d smc_trading -c "
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
"
```

### 3. Point-in-Time Recovery

#### Scenario: Need to recover to specific timestamp

```bash
# Determine target recovery time
TARGET_TIME="2024-01-15 14:30:00"

# Stop all database connections
kubectl scale deployment trading-engine --replicas=0 -n smc-trading
kubectl scale deployment api-gateway --replicas=0 -n smc-trading

# Find appropriate base backup
aws s3 ls s3://smc-trading-backups/daily/ | awk '$1 <= "2024-01-15" {print $4}' | tail -1

# Download base backup and WAL files
BASE_BACKUP="backup_20240115_120000.dump.gz"
aws s3 cp s3://smc-trading-backups/daily/$BASE_BACKUP ./
aws s3 sync s3://smc-trading-backups/wal/ ./wal_files/

# Restore base backup
gunzip $BASE_BACKUP
kubectl cp ${BASE_BACKUP%.gz} smc-trading/postgres-primary:/tmp/restore.dump
kubectl exec postgres-primary -n smc-trading -- pg_restore -U postgres -d smc_trading -v /tmp/restore.dump

# Configure recovery
kubectl exec postgres-primary -n smc-trading -- bash -c "
cat > /var/lib/postgresql/data/recovery.conf << EOF
restore_command = 'cp /wal_files/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'promote'
EOF
"

# Copy WAL files to PostgreSQL pod
kubectl cp ./wal_files/ smc-trading/postgres-primary:/wal_files/

# Restart PostgreSQL to start recovery
kubectl rollout restart statefulset/postgres-primary -n smc-trading

# Monitor recovery progress
kubectl logs -f postgres-primary-0 -n smc-trading | grep recovery

# Restart applications after recovery completes
kubectl scale deployment trading-engine --replicas=3 -n smc-trading
kubectl scale deployment api-gateway --replicas=3 -n smc-trading
```

## Cross-Region Disaster Recovery

### 1. Setup Secondary Region

```bash
# Deploy to secondary region (e.g., us-west-2)
export AWS_REGION=us-west-2
export KUBECONFIG=~/.kube/config-west

# Create namespace in secondary region
kubectl apply -f k8s/namespace.yaml

# Deploy minimal infrastructure (database only initially)
kubectl apply -f k8s/postgres-replica.yaml
kubectl apply -f k8s/redis-replica.yaml

# Setup cross-region replication
kubectl exec postgres-primary -n smc-trading -- psql -U postgres -c "
SELECT pg_create_physical_replication_slot('replica_west');
"

# Configure replica in west region
kubectl exec postgres-replica -n smc-trading -- bash -c "
cat > /var/lib/postgresql/data/recovery.conf << EOF
standby_mode = 'on'
primary_conninfo = 'host=postgres-primary.smc-trading.svc.cluster.local port=5432 user=replicator'
primary_slot_name = 'replica_west'
EOF
"
```

### 2. Failover to Secondary Region

```bash
# In case of primary region failure
export AWS_REGION=us-west-2
export KUBECONFIG=~/.kube/config-west

# Promote replica to primary
kubectl exec postgres-replica -n smc-trading -- pg_ctl promote -D /var/lib/postgresql/data

# Deploy full application stack
kubectl apply -f k8s/

# Update DNS to point to new region
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch '{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "api.smc-trading.com",
            "Type": "CNAME",
            "TTL": 60,
            "ResourceRecords": [{"Value": "api-west.smc-trading.com"}]
        }
    }]
}'

# Verify failover
curl -f https://api.smc-trading.com/health
```

## Backup Verification and Testing

### 1. Monthly Backup Restoration Test

```bash
#!/bin/bash
# monthly-backup-test.sh - Test backup restoration process

TEST_DATE=$(date +%Y%m%d_%H%M%S)
TEST_NAMESPACE="smc-trading-test"

echo "Starting monthly backup restoration test: $TEST_DATE"

# Create test namespace
kubectl create namespace $TEST_NAMESPACE

# Get latest backup
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp s3://smc-trading-backups/daily/$LATEST_BACKUP ./test-backup.dump.gz

# Deploy test PostgreSQL instance
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
EOF

# Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=postgres-test -n $TEST_NAMESPACE --timeout=300s

# Restore backup to test instance
gunzip test-backup.dump.gz
kubectl cp test-backup.dump $TEST_NAMESPACE/$(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}'):/tmp/
kubectl exec -n $TEST_NAMESPACE $(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}') -- pg_restore -U postgres -d smc_trading -v /tmp/test-backup.dump

# Verify data integrity
TRADE_COUNT=$(kubectl exec -n $TEST_NAMESPACE $(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}') -- psql -U postgres -d smc_trading -t -c "SELECT COUNT(*) FROM trades;")
USER_COUNT=$(kubectl exec -n $TEST_NAMESPACE $(kubectl get pod -l app=postgres-test -n $TEST_NAMESPACE -o jsonpath='{.items[0].metadata.name}') -- psql -U postgres -d smc_trading -t -c "SELECT COUNT(*) FROM users;")

echo "Backup restoration test results:"
echo "- Trades count: $TRADE_COUNT"
echo "- Users count: $USER_COUNT"

# Cleanup test environment
kubectl delete namespace $TEST_NAMESPACE

# Report results
if [ $TRADE_COUNT -gt 0 ] && [ $USER_COUNT -gt 0 ]; then
    echo "✅ Backup restoration test PASSED"
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"✅ Monthly backup restoration test PASSED - '$TEST_DATE'"}' \
        $SLACK_WEBHOOK_URL
else
    echo "❌ Backup restoration test FAILED"
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"❌ Monthly backup restoration test FAILED - '$TEST_DATE'"}' \
        $SLACK_WEBHOOK_URL
fi

# Cleanup
rm -f test-backup.dump test-backup.dump.gz

echo "Monthly backup restoration test completed: $TEST_DATE"
```

## Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO)

### Service Level Objectives

| Component    | RTO        | RPO        | Backup Frequency    |
| ------------ | ---------- | ---------- | ------------------- |
| Database     | 15 minutes | 5 minutes  | Every 6 hours + WAL |
| Application  | 10 minutes | 0 minutes  | Configuration only  |
| Redis Cache  | 5 minutes  | 15 minutes | Daily               |
| File Storage | 30 minutes | 1 hour     | Daily               |

### Recovery Procedures by Scenario

| Scenario                | Estimated RTO | Recovery Steps                 |
| ----------------------- | ------------- | ------------------------------ |
| Single pod failure      | 2 minutes     | Kubernetes auto-restart        |
| Database corruption     | 15 minutes    | Restore from latest backup     |
| Complete region failure | 30 minutes    | Failover to secondary region   |
| Data center failure     | 45 minutes    | Cross-region disaster recovery |
| Ransomware attack       | 60 minutes    | Restore from offline backups   |

## Monitoring and Alerting for Backups

### Backup Success Monitoring

```bash
# Create backup monitoring script
cat > /usr/local/bin/backup-monitor.sh << 'EOF'
#!/bin/bash

# Check if daily backup completed successfully
YESTERDAY=$(date -d "yesterday" +%Y%m%d)
BACKUP_EXISTS=$(aws s3 ls s3://smc-trading-backups/daily/ | grep $YESTERDAY | wc -l)

if [ $BACKUP_EXISTS -eq 0 ]; then
    echo "❌ Daily backup missing for $YESTERDAY"
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Daily backup MISSING for '$YESTERDAY'"}' \
        $SLACK_WEBHOOK_URL
    exit 1
else
    echo "✅ Daily backup found for $YESTERDAY"
fi

# Check backup file integrity
LATEST_BACKUP=$(aws s3 ls s3://smc-trading-backups/daily/ | grep $YESTERDAY | awk '{print $4}')
aws s3 cp s3://smc-trading-backups/daily/$LATEST_BACKUP /tmp/
gunzip -t /tmp/$LATEST_BACKUP

if [ $? -eq 0 ]; then
    echo "✅ Backup integrity check passed"
    rm /tmp/$LATEST_BACKUP
else
    echo "❌ Backup integrity check failed"
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Backup integrity check FAILED for '$LATEST_BACKUP'"}' \
        $SLACK_WEBHOOK_URL
    exit 1
fi
EOF

chmod +x /usr/local/bin/backup-monitor.sh

# Add to crontab for daily execution
echo "0 8 * * * /usr/local/bin/backup-monitor.sh" | crontab -
```

## Emergency Contacts and Escalation

### Disaster Recovery Team

- **DR Coordinator**: dr-coordinator@smc-trading.com
- **Database Administrator**: dba@smc-trading.com
- **Infrastructure Lead**: infra-lead@smc-trading.com
- **Security Officer**: security@smc-trading.com

### Emergency Procedures

1. **Immediate Response** (0-15 minutes): Assess impact and initiate recovery
2. **Communication** (15-30 minutes): Notify stakeholders and customers
3. **Recovery Execution** (30-60 minutes): Execute recovery procedures
4. **Verification** (60-90 minutes): Verify system functionality
5. **Post-Incident** (24-48 hours): Conduct post-mortem and update procedures

---

**Last Updated**: $(date)  
**Document Version**: 1.0.0  
**Next Review Date**: $(date -d "+3 months")  
**Maintained By**: DevOps Team
