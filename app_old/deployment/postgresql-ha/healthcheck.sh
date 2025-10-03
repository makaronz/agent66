#!/bin/bash

# Health check script for Patroni PostgreSQL cluster
# Checks both PostgreSQL and Patroni health

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check PostgreSQL connectivity
check_postgresql() {
    if pg_isready -h localhost -p 5432 -U postgres > /dev/null 2>&1; then
        log "${GREEN}✓ PostgreSQL is accepting connections${NC}"
        return 0
    else
        log "${RED}✗ PostgreSQL is not accepting connections${NC}"
        return 1
    fi
}

# Function to check Patroni REST API
check_patroni_api() {
    local response
    local http_code
    
    response=$(curl -s -w "%{http_code}" http://localhost:8008/health 2>/dev/null || echo "000")
    http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        log "${GREEN}✓ Patroni REST API is healthy${NC}"
        return 0
    else
        log "${RED}✗ Patroni REST API is unhealthy (HTTP $http_code)${NC}"
        return 1
    fi
}

# Function to check cluster status
check_cluster_status() {
    local cluster_info
    
    cluster_info=$(curl -s http://localhost:8008/cluster 2>/dev/null || echo "{}")
    
    if echo "$cluster_info" | jq -e '.members' > /dev/null 2>&1; then
        local member_count
        local leader_count
        
        member_count=$(echo "$cluster_info" | jq '.members | length')
        leader_count=$(echo "$cluster_info" | jq '[.members[] | select(.role == "leader")] | length')
        
        log "Cluster members: $member_count"
        log "Leaders: $leader_count"
        
        if [ "$leader_count" -eq 1 ]; then
            log "${GREEN}✓ Cluster has exactly one leader${NC}"
            return 0
        else
            log "${YELLOW}⚠ Cluster has $leader_count leaders (expected: 1)${NC}"
            return 1
        fi
    else
        log "${RED}✗ Unable to retrieve cluster information${NC}"
        return 1
    fi
}

# Function to check replication lag
check_replication_lag() {
    local lag_info
    
    # Only check replication lag if this is a replica
    local role
    role=$(curl -s http://localhost:8008/patroni 2>/dev/null | jq -r '.role // "unknown"')
    
    if [ "$role" = "replica" ]; then
        lag_info=$(psql -h localhost -p 5432 -U postgres -d postgres -t -c "
            SELECT COALESCE(
                EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())), 
                0
            )::int;
        " 2>/dev/null || echo "999")
        
        if [ "$lag_info" -lt 10 ]; then
            log "${GREEN}✓ Replication lag: ${lag_info}s${NC}"
            return 0
        elif [ "$lag_info" -lt 60 ]; then
            log "${YELLOW}⚠ Replication lag: ${lag_info}s${NC}"
            return 0
        else
            log "${RED}✗ High replication lag: ${lag_info}s${NC}"
            return 1
        fi
    else
        log "Node role: $role (skipping replication lag check)"
        return 0
    fi
}

# Function to check database connectivity
check_database_connectivity() {
    local query_result
    
    query_result=$(psql -h localhost -p 5432 -U postgres -d smc_trading_agent -t -c "SELECT 1;" 2>/dev/null || echo "")
    
    if [ "$query_result" = " 1" ]; then
        log "${GREEN}✓ Application database is accessible${NC}"
        return 0
    else
        log "${RED}✗ Application database is not accessible${NC}"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    local data_dir_usage
    local log_dir_usage
    
    data_dir_usage=$(df /var/lib/postgresql/data | awk 'NR==2 {print $5}' | sed 's/%//')
    log_dir_usage=$(df /var/log/postgresql | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$data_dir_usage" -lt 80 ] && [ "$log_dir_usage" -lt 80 ]; then
        log "${GREEN}✓ Disk usage: data ${data_dir_usage}%, logs ${log_dir_usage}%${NC}"
        return 0
    elif [ "$data_dir_usage" -lt 90 ] && [ "$log_dir_usage" -lt 90 ]; then
        log "${YELLOW}⚠ Disk usage: data ${data_dir_usage}%, logs ${log_dir_usage}%${NC}"
        return 0
    else
        log "${RED}✗ High disk usage: data ${data_dir_usage}%, logs ${log_dir_usage}%${NC}"
        return 1
    fi
}

# Main health check function
main() {
    local exit_code=0
    
    log "Starting PostgreSQL HA health check..."
    
    # Run all health checks
    check_postgresql || exit_code=1
    check_patroni_api || exit_code=1
    check_cluster_status || exit_code=1
    check_replication_lag || exit_code=1
    check_database_connectivity || exit_code=1
    check_disk_space || exit_code=1
    
    if [ $exit_code -eq 0 ]; then
        log "${GREEN}✓ All health checks passed${NC}"
    else
        log "${RED}✗ Some health checks failed${NC}"
    fi
    
    return $exit_code
}

# Run health check
main "$@"