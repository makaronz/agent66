#!/bin/bash

# Post-bootstrap script for PostgreSQL cluster initialization
# This script runs after the initial cluster is created

set -e

echo "Running post-bootstrap configuration..."

# Wait for PostgreSQL to be ready
until pg_isready -h localhost -p 5432; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

# Connect to PostgreSQL and run initialization
psql -h localhost -p 5432 -U postgres -d postgres << 'EOF'

-- Create application database
CREATE DATABASE smc_trading_agent;

-- Create application users with proper permissions
CREATE USER smc_app_user WITH PASSWORD 'change_me_in_production';
CREATE USER smc_read_user WITH PASSWORD 'change_me_in_production';

-- Grant permissions
GRANT CONNECT ON DATABASE smc_trading_agent TO smc_app_user;
GRANT CONNECT ON DATABASE smc_trading_agent TO smc_read_user;

-- Connect to application database
\c smc_trading_agent

-- Create schema and grant permissions
GRANT USAGE ON SCHEMA public TO smc_app_user;
GRANT USAGE ON SCHEMA public TO smc_read_user;

GRANT CREATE ON SCHEMA public TO smc_app_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO smc_read_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO smc_app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO smc_app_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO smc_read_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO smc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO smc_app_user;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "auto_explain";

-- Create monitoring user for metrics collection
CREATE USER postgres_exporter WITH PASSWORD 'change_me_in_production';
GRANT pg_monitor TO postgres_exporter;

-- Create replication monitoring view
CREATE OR REPLACE VIEW replication_status AS
SELECT 
    client_addr,
    client_hostname,
    client_port,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    write_lag,
    flush_lag,
    replay_lag,
    sync_priority,
    sync_state
FROM pg_stat_replication;

GRANT SELECT ON replication_status TO postgres_exporter;

-- Create cluster health monitoring function
CREATE OR REPLACE FUNCTION cluster_health_check()
RETURNS TABLE(
    metric_name text,
    metric_value numeric,
    status text
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        'active_connections'::text,
        COUNT(*)::numeric,
        CASE WHEN COUNT(*) < 180 THEN 'OK' ELSE 'WARNING' END
    FROM pg_stat_activity
    WHERE state = 'active'
    
    UNION ALL
    
    SELECT 
        'replication_lag_bytes'::text,
        COALESCE(MAX(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)), 0)::numeric,
        CASE 
            WHEN MAX(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) < 1048576 THEN 'OK'
            WHEN MAX(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) < 10485760 THEN 'WARNING'
            ELSE 'CRITICAL'
        END
    FROM pg_stat_replication
    
    UNION ALL
    
    SELECT 
        'database_size_mb'::text,
        (pg_database_size(current_database()) / 1024 / 1024)::numeric,
        'INFO'::text
    
    UNION ALL
    
    SELECT 
        'cache_hit_ratio'::text,
        ROUND(
            (sum(blks_hit) * 100.0 / NULLIF(sum(blks_hit) + sum(blks_read), 0))::numeric, 
            2
        ),
        CASE 
            WHEN ROUND((sum(blks_hit) * 100.0 / NULLIF(sum(blks_hit) + sum(blks_read), 0))::numeric, 2) > 95 THEN 'OK'
            WHEN ROUND((sum(blks_hit) * 100.0 / NULLIF(sum(blks_hit) + sum(blks_read), 0))::numeric, 2) > 90 THEN 'WARNING'
            ELSE 'CRITICAL'
        END
    FROM pg_stat_database
    WHERE datname = current_database();
END;
$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION cluster_health_check() TO postgres_exporter;

EOF

echo "Post-bootstrap configuration completed successfully"