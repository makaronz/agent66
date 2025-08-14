#!/bin/bash

# Disaster Recovery Testing Script for SMC Trading Agent PostgreSQL HA
# This script tests various failure scenarios and recovery procedures

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="smc-trading"
PRIMARY_SERVICE="postgresql-primary"
REPLICA_SERVICE="postgresql-replica"
CLUSTER_SERVICE="postgresql-ha-cluster"
PATRONI_PORT="8008"
POSTGRES_PORT="5432"

# Test configuration
TEST_DATABASE="smc_trading_agent"
TEST_USER="smc_app_user"
TEST_PASSWORD="${POSTGRES_APP_PASSWORD:-smc_app_pass}"

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to wait for condition
wait_for_condition() {
    local condition="$1"
    local timeout="${2:-300}"
    local interval="${3:-5}"
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if eval "$condition"; then
            return 0
        fi
        sleep $interval
        elapsed=$((elapsed + interval))
        echo -n "."
    done
    
    echo ""
    return 1
}

# Function to get cluster status
get_cluster_status() {
    kubectl get pods -n $NAMESPACE -l app=postgresql-ha -o wide
}

# Function to get Patroni cluster info
get_patroni_cluster() {
    local pod_name="$1"
    kubectl exec -n $NAMESPACE $pod_name -- curl -s http://localhost:$PATRONI_PORT/cluster 2>/dev/null || echo "{}"
}

# Function to get current leader
get_current_leader() {
    local pods=$(kubectl get pods -n $NAMESPACE -l app=postgresql-ha --no-headers -o custom-columns=":metadata.name")
    
    for pod in $pods; do
        local status=$(kubectl exec -n $NAMESPACE $pod -- curl -s http://localhost:$PATRONI_PORT/patroni 2>/dev/null || echo "{}")
        local role=$(echo "$status" | jq -r '.role // "unknown"')
        
        if [ "$role" = "master" ] || [ "$role" = "leader" ]; then
            echo "$pod"
            return 0
        fi
    done
    
    return 1
}

# Function to get replicas
get_replicas() {
    local pods=$(kubectl get pods -n $NAMESPACE -l app=postgresql-ha --no-headers -o custom-columns=":metadata.name")
    local replicas=""
    
    for pod in $pods; do
        local status=$(kubectl exec -n $NAMESPACE $pod -- curl -s http://localhost:$PATRONI_PORT/patroni 2>/dev/null || echo "{}")
        local role=$(echo "$status" | jq -r '.role // "unknown"')
        
        if [ "$role" = "replica" ]; then
            replicas="$replicas $pod"
        fi
    done
    
    echo "$replicas"
}

# Function to execute SQL query
execute_sql() {
    local pod_name="$1"
    local query="$2"
    local database="${3:-$TEST_DATABASE}"
    
    kubectl exec -n $NAMESPACE $pod_name -- psql -h localhost -p $POSTGRES_PORT -U $TEST_USER -d $database -c "$query" 2>/dev/null
}

# Function to test database connectivity
test_connectivity() {
    local service_name="$1"
    local description="$2"
    
    log "${BLUE}Testing connectivity to $description ($service_name)${NC}"
    
    if kubectl run test-connectivity-$RANDOM --rm -i --restart=Never --image=postgres:15-alpine -- \
        psql -h $service_name.$NAMESPACE.svc.cluster.local -p $POSTGRES_PORT -U $TEST_USER -d $TEST_DATABASE -c "SELECT 1;" > /dev/null 2>&1; then
        log "${GREEN}✓ Successfully connected to $description${NC}"
        return 0
    else
        log "${RED}✗ Failed to connect to $description${NC}"
        return 1
    fi
}

# Function to create test data
create_test_data() {
    local pod_name="$1"
    local timestamp=$(date +%s)
    
    log "${BLUE}Creating test data on $pod_name${NC}"
    
    execute_sql $pod_name "
        CREATE TABLE IF NOT EXISTS dr_test_data (
            id SERIAL PRIMARY KEY,
            test_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            data JSONB
        );
        
        INSERT INTO dr_test_data (test_name, data) 
        VALUES ('dr_test_$timestamp', '{\"test\": true, \"timestamp\": $timestamp}');
    "
    
    echo $timestamp
}

# Function to verify test data
verify_test_data() {
    local pod_name="$1"
    local timestamp="$2"
    
    log "${BLUE}Verifying test data on $pod_name${NC}"
    
    local count=$(execute_sql $pod_name "SELECT COUNT(*) FROM dr_test_data WHERE test_name = 'dr_test_$timestamp';" | grep -o '[0-9]*' | head -1)
    
    if [ "$count" = "1" ]; then
        log "${GREEN}✓ Test data verified on $pod_name${NC}"
        return 0
    else
        log "${RED}✗ Test data not found on $pod_name${NC}"
        return 1
    fi
}

# Function to check replication lag
check_replication_lag() {
    local replica_pod="$1"
    
    log "${BLUE}Checking replication lag on $replica_pod${NC}"
    
    local lag=$(execute_sql $replica_pod "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::int;" | grep -o '[0-9]*' | head -1)
    
    if [ -z "$lag" ] || [ "$lag" -gt 60 ]; then
        log "${YELLOW}⚠ High replication lag on $replica_pod: ${lag}s${NC}"
        return 1
    else
        log "${GREEN}✓ Replication lag on $replica_pod: ${lag}s${NC}"
        return 0
    fi
}

# Test 1: Basic cluster health check
test_cluster_health() {
    log "${BLUE}=== Test 1: Cluster Health Check ===${NC}"
    
    log "Getting cluster status..."
    get_cluster_status
    
    local leader=$(get_current_leader)
    if [ -n "$leader" ]; then
        log "${GREEN}✓ Current leader: $leader${NC}"
    else
        log "${RED}✗ No leader found${NC}"
        return 1
    fi
    
    local replicas=$(get_replicas)
    if [ -n "$replicas" ]; then
        log "${GREEN}✓ Replicas found:$replicas${NC}"
    else
        log "${YELLOW}⚠ No replicas found${NC}"
    fi
    
    # Test connectivity to services
    test_connectivity $PRIMARY_SERVICE "Primary Service"
    test_connectivity $REPLICA_SERVICE "Replica Service"
    test_connectivity $CLUSTER_SERVICE "Cluster Service"
    
    log "${GREEN}✓ Test 1 completed${NC}"
}

# Test 2: Data replication test
test_data_replication() {
    log "${BLUE}=== Test 2: Data Replication Test ===${NC}"
    
    local leader=$(get_current_leader)
    if [ -z "$leader" ]; then
        log "${RED}✗ No leader found for replication test${NC}"
        return 1
    fi
    
    # Create test data on leader
    local timestamp=$(create_test_data $leader)
    
    # Wait for replication
    log "Waiting for replication to complete..."
    sleep 10
    
    # Verify data on replicas
    local replicas=$(get_replicas)
    local replication_success=true
    
    for replica in $replicas; do
        if ! verify_test_data $replica $timestamp; then
            replication_success=false
        fi
        check_replication_lag $replica
    done
    
    if $replication_success; then
        log "${GREEN}✓ Test 2 completed - Data replication working${NC}"
    else
        log "${RED}✗ Test 2 failed - Data replication issues${NC}"
        return 1
    fi
}

# Test 3: Leader failover test
test_leader_failover() {
    log "${BLUE}=== Test 3: Leader Failover Test ===${NC}"
    
    local original_leader=$(get_current_leader)
    if [ -z "$original_leader" ]; then
        log "${RED}✗ No leader found for failover test${NC}"
        return 1
    fi
    
    log "Original leader: $original_leader"
    
    # Create test data before failover
    local timestamp=$(create_test_data $original_leader)
    
    # Simulate leader failure by stopping the pod
    log "${YELLOW}Simulating leader failure by deleting pod $original_leader${NC}"
    kubectl delete pod -n $NAMESPACE $original_leader
    
    # Wait for new leader election
    log "Waiting for new leader election..."
    if wait_for_condition "[ -n \"\$(get_current_leader)\" ] && [ \"\$(get_current_leader)\" != \"$original_leader\" ]" 120 5; then
        local new_leader=$(get_current_leader)
        log "${GREEN}✓ New leader elected: $new_leader${NC}"
        
        # Verify data is accessible on new leader
        if verify_test_data $new_leader $timestamp; then
            log "${GREEN}✓ Data accessible on new leader${NC}"
        else
            log "${RED}✗ Data not accessible on new leader${NC}"
            return 1
        fi
        
        # Test write operations on new leader
        local new_timestamp=$(create_test_data $new_leader)
        if verify_test_data $new_leader $new_timestamp; then
            log "${GREEN}✓ Write operations working on new leader${NC}"
        else
            log "${RED}✗ Write operations failed on new leader${NC}"
            return 1
        fi
        
    else
        log "${RED}✗ New leader not elected within timeout${NC}"
        return 1
    fi
    
    # Wait for original leader to recover
    log "Waiting for original leader to recover as replica..."
    if wait_for_condition "kubectl get pod -n $NAMESPACE $original_leader -o jsonpath='{.status.phase}' | grep -q Running" 300 10; then
        log "${GREEN}✓ Original leader recovered${NC}"
        
        # Check if it's now a replica
        sleep 30  # Wait for Patroni to stabilize
        local recovered_pods=$(get_replicas)
        if echo "$recovered_pods" | grep -q "$original_leader"; then
            log "${GREEN}✓ Original leader is now a replica${NC}"
        else
            log "${YELLOW}⚠ Original leader role unclear${NC}"
        fi
    else
        log "${YELLOW}⚠ Original leader recovery timeout${NC}"
    fi
    
    log "${GREEN}✓ Test 3 completed${NC}"
}

# Test 4: Split-brain prevention test
test_split_brain_prevention() {
    log "${BLUE}=== Test 4: Split-brain Prevention Test ===${NC}"
    
    local leader=$(get_current_leader)
    local replicas=$(get_replicas)
    
    if [ -z "$leader" ] || [ -z "$replicas" ]; then
        log "${YELLOW}⚠ Insufficient nodes for split-brain test${NC}"
        return 0
    fi
    
    # Simulate network partition by blocking Patroni API on leader
    log "${YELLOW}Simulating network partition${NC}"
    kubectl exec -n $NAMESPACE $leader -- iptables -A INPUT -p tcp --dport $PATRONI_PORT -j DROP 2>/dev/null || true
    
    # Wait and check if new leader is elected
    log "Waiting to see if new leader is elected..."
    sleep 60
    
    local current_leader=$(get_current_leader)
    if [ "$current_leader" != "$leader" ] && [ -n "$current_leader" ]; then
        log "${GREEN}✓ New leader elected during partition: $current_leader${NC}"
        
        # Restore network and check for split-brain resolution
        log "Restoring network connectivity..."
        kubectl exec -n $NAMESPACE $leader -- iptables -D INPUT -p tcp --dport $PATRONI_PORT -j DROP 2>/dev/null || true
        
        # Wait for cluster to stabilize
        sleep 30
        
        # Check that there's still only one leader
        local leader_count=0
        local pods=$(kubectl get pods -n $NAMESPACE -l app=postgresql-ha --no-headers -o custom-columns=":metadata.name")
        
        for pod in $pods; do
            local status=$(kubectl exec -n $NAMESPACE $pod -- curl -s http://localhost:$PATRONI_PORT/patroni 2>/dev/null || echo "{}")
            local role=$(echo "$status" | jq -r '.role // "unknown"')
            
            if [ "$role" = "master" ] || [ "$role" = "leader" ]; then
                leader_count=$((leader_count + 1))
            fi
        done
        
        if [ $leader_count -eq 1 ]; then
            log "${GREEN}✓ Split-brain prevented - only one leader exists${NC}"
        else
            log "${RED}✗ Split-brain detected - multiple leaders: $leader_count${NC}"
            return 1
        fi
    else
        log "${YELLOW}⚠ No leadership change during partition${NC}"
    fi
    
    log "${GREEN}✓ Test 4 completed${NC}"
}

# Test 5: Backup and restore test
test_backup_restore() {
    log "${BLUE}=== Test 5: Backup and Restore Test ===${NC}"
    
    local leader=$(get_current_leader)
    if [ -z "$leader" ]; then
        log "${RED}✗ No leader found for backup test${NC}"
        return 1
    fi
    
    # Create test data
    local timestamp=$(create_test_data $leader)
    
    # Create backup
    log "Creating backup..."
    kubectl exec -n $NAMESPACE $leader -- pg_dump -h localhost -p $POSTGRES_PORT -U postgres -d $TEST_DATABASE > /tmp/backup_$timestamp.sql
    
    if [ $? -eq 0 ]; then
        log "${GREEN}✓ Backup created successfully${NC}"
    else
        log "${RED}✗ Backup creation failed${NC}"
        return 1
    fi
    
    # Simulate data corruption by dropping test table
    log "${YELLOW}Simulating data corruption${NC}"
    execute_sql $leader "DROP TABLE IF EXISTS dr_test_data;"
    
    # Restore from backup
    log "Restoring from backup..."
    kubectl exec -n $NAMESPACE $leader -i -- psql -h localhost -p $POSTGRES_PORT -U postgres -d $TEST_DATABASE < /tmp/backup_$timestamp.sql
    
    if [ $? -eq 0 ]; then
        log "${GREEN}✓ Restore completed successfully${NC}"
        
        # Verify restored data
        if verify_test_data $leader $timestamp; then
            log "${GREEN}✓ Restored data verified${NC}"
        else
            log "${RED}✗ Restored data verification failed${NC}"
            return 1
        fi
    else
        log "${RED}✗ Restore failed${NC}"
        return 1
    fi
    
    # Cleanup
    rm -f /tmp/backup_$timestamp.sql
    
    log "${GREEN}✓ Test 5 completed${NC}"
}

# Test 6: Performance under load
test_performance_under_load() {
    log "${BLUE}=== Test 6: Performance Under Load Test ===${NC}"
    
    local leader=$(get_current_leader)
    if [ -z "$leader" ]; then
        log "${RED}✗ No leader found for performance test${NC}"
        return 1
    fi
    
    # Create test table for load testing
    execute_sql $leader "
        CREATE TABLE IF NOT EXISTS load_test (
            id SERIAL PRIMARY KEY,
            data TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    "
    
    # Run concurrent load test
    log "Running load test with concurrent connections..."
    
    local pids=()
    for i in {1..10}; do
        (
            for j in {1..100}; do
                execute_sql $leader "INSERT INTO load_test (data) VALUES ('test_data_${i}_${j}');" > /dev/null 2>&1
            done
        ) &
        pids+=($!)
    done
    
    # Wait for all background jobs
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    # Check results
    local count=$(execute_sql $leader "SELECT COUNT(*) FROM load_test;" | grep -o '[0-9]*' | head -1)
    
    if [ "$count" -ge 1000 ]; then
        log "${GREEN}✓ Load test completed - $count records inserted${NC}"
    else
        log "${YELLOW}⚠ Load test completed with some failures - $count records inserted${NC}"
    fi
    
    # Check replication lag after load
    local replicas=$(get_replicas)
    for replica in $replicas; do
        check_replication_lag $replica
    done
    
    # Cleanup
    execute_sql $leader "DROP TABLE IF EXISTS load_test;"
    
    log "${GREEN}✓ Test 6 completed${NC}"
}

# Main test runner
run_all_tests() {
    log "${BLUE}Starting PostgreSQL HA Disaster Recovery Tests${NC}"
    log "Namespace: $NAMESPACE"
    log "Test Database: $TEST_DATABASE"
    log "Test User: $TEST_USER"
    echo ""
    
    local failed_tests=0
    
    # Run all tests
    test_cluster_health || failed_tests=$((failed_tests + 1))
    echo ""
    
    test_data_replication || failed_tests=$((failed_tests + 1))
    echo ""
    
    test_leader_failover || failed_tests=$((failed_tests + 1))
    echo ""
    
    test_split_brain_prevention || failed_tests=$((failed_tests + 1))
    echo ""
    
    test_backup_restore || failed_tests=$((failed_tests + 1))
    echo ""
    
    test_performance_under_load || failed_tests=$((failed_tests + 1))
    echo ""
    
    # Summary
    log "${BLUE}=== Test Summary ===${NC}"
    if [ $failed_tests -eq 0 ]; then
        log "${GREEN}✓ All tests passed successfully${NC}"
        return 0
    else
        log "${RED}✗ $failed_tests test(s) failed${NC}"
        return 1
    fi
}

# Cleanup function
cleanup() {
    log "${BLUE}Cleaning up test resources...${NC}"
    
    # Remove test data
    local pods=$(kubectl get pods -n $NAMESPACE -l app=postgresql-ha --no-headers -o custom-columns=":metadata.name")
    for pod in $pods; do
        execute_sql $pod "DROP TABLE IF EXISTS dr_test_data;" 2>/dev/null || true
        execute_sql $pod "DROP TABLE IF EXISTS load_test;" 2>/dev/null || true
    done
    
    # Remove any iptables rules
    for pod in $pods; do
        kubectl exec -n $NAMESPACE $pod -- iptables -D INPUT -p tcp --dport $PATRONI_PORT -j DROP 2>/dev/null || true
    done
    
    log "${GREEN}✓ Cleanup completed${NC}"
}

# Signal handlers
trap cleanup EXIT
trap 'log "${RED}Test interrupted${NC}"; exit 1' INT TERM

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    log "${RED}kubectl is required but not installed${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    log "${RED}jq is required but not installed${NC}"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    log "${RED}Namespace $NAMESPACE does not exist${NC}"
    exit 1
fi

# Run tests based on arguments
case "${1:-all}" in
    "health")
        test_cluster_health
        ;;
    "replication")
        test_data_replication
        ;;
    "failover")
        test_leader_failover
        ;;
    "split-brain")
        test_split_brain_prevention
        ;;
    "backup")
        test_backup_restore
        ;;
    "performance")
        test_performance_under_load
        ;;
    "all")
        run_all_tests
        ;;
    *)
        echo "Usage: $0 [health|replication|failover|split-brain|backup|performance|all]"
        exit 1
        ;;
esac