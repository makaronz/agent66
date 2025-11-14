#!/bin/bash
# Film Industry Time Tracking System - Backup Strategy

set -euo pipefail

# Configuration
BACKUP_DIR="/backups/film-tracker"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
S3_BUCKET="${S3_BUCKET:-film-tracker-backups}"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Send Slack notification
send_slack_notification() {
    local message="$1"
    local status="$2"

    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🎬 Film Tracker Backup: $message\", \"status\":\"$status\"}" \
            "$SLACK_WEBHOOK" || log "Failed to send Slack notification"
    fi
}

# Database backup
backup_database() {
    log "Starting database backup..."

    local backup_file="$BACKUP_DIR/postgres_backup_$DATE.sql"

    # Create database backup
    docker exec film-tracker-postgres pg_dump \
        -h localhost \
        -U "${POSTGRES_USER:-postgres}" \
        -d "${POSTGRES_DB:-film_tracker}" \
        --no-password \
        --verbose \
        --clean \
        --if-exists \
        --format=custom \
        --file="/tmp/backup_$DATE.sql"

    # Copy backup from container
    docker cp "film-tracker-postgres:/tmp/backup_$DATE.sql" "$backup_file"

    # Compress backup
    gzip "$backup_file"
    backup_file="${backup_file}.gz"

    # Upload to S3 if configured
    if [[ -n "${AWS_ACCESS_KEY_ID}" && -n "${AWS_SECRET_ACCESS_KEY}" ]]; then
        aws s3 cp "$backup_file" "s3://$S3_BUCKET/database/" \
            --storage-class STANDARD_IA \
            --server-side-encryption AES256
    fi

    log "Database backup completed: $backup_file"
}

# Redis backup
backup_redis() {
    log "Starting Redis backup..."

    local backup_file="$BACKUP_DIR/redis_backup_$DATE.rdb"

    # Trigger Redis background save
    docker exec film-tracker-redis redis-cli BGSAVE

    # Wait for background save to complete
    while [[ $(docker exec film-tracker-redis redis-cli LASTSAVE) -eq $(docker exec film-tracker-redis redis-cli LASTSAVE) ]]; do
        sleep 1
    done

    # Copy RDB file from container
    docker cp "film-tracker-redis:/data/dump.rdb" "$backup_file"

    # Compress backup
    gzip "$backup_file"
    backup_file="${backup_file}.gz"

    # Upload to S3 if configured
    if [[ -n "${AWS_ACCESS_KEY_ID}" && -n "${AWS_SECRET_ACCESS_KEY}" ]]; then
        aws s3 cp "$backup_file" "s3://$S3_BUCKET/redis/" \
            --storage-class STANDARD_IA \
            --server-side-encryption AES256
    fi

    log "Redis backup completed: $backup_file"
}

# File storage backup
backup_files() {
    log "Starting file storage backup..."

    local backup_file="$BACKUP_DIR/files_backup_$DATE.tar.gz"

    # Backup uploaded files and logs
    tar -czf "$backup_file" \
        --exclude=node_modules \
        --exclude=.git \
        ./uploads \
        ./logs

    # Upload to S3 if configured
    if [[ -n "${AWS_ACCESS_KEY_ID}" && -n "${AWS_SECRET_ACCESS_KEY}" ]]; then
        aws s3 cp "$backup_file" "s3://$S3_BUCKET/files/" \
            --storage-class STANDARD_IA \
            --server-side-encryption AES256
    fi

    log "File backup completed: $backup_file"
}

# Configuration backup
backup_config() {
    log "Starting configuration backup..."

    local backup_file="$BACKUP_DIR/config_backup_$DATE.tar.gz"

    # Backup configuration files
    tar -czf "$backup_file" \
        ./config \
        ./docker-compose*.yml \
        ./.env.production \
        ./nginx.conf

    # Upload to S3 if configured
    if [[ -n "${AWS_ACCESS_KEY_ID}" && -n "${AWS_SECRET_ACCESS_KEY}" ]]; then
        aws s3 cp "$backup_file" "s3://$S3_BUCKET/config/" \
            --storage-class STANDARD_IA \
            --server-side-encryption AES256
    fi

    log "Configuration backup completed: $backup_file"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."

    # Clean up local backups
    find "$BACKUP_DIR" -type f -mtime "+$RETENTION_DAYS" -delete

    # Clean up S3 backups if configured
    if [[ -n "${AWS_ACCESS_KEY_ID}" && -n "${AWS_SECRET_ACCESS_KEY}" ]]; then
        aws s3 ls "s3://$S3_BUCKET/" --recursive | \
        while read -r line; do
            file_date=$(echo "$line" | awk '{print $1" "$2}')
            file_path=$(echo "$line" | awk '{print $4}')

            if [[ $(date -d "$file_date" +%s) -lt $(date -d "$RETENTION_DAYS days ago" +%s) ]]; then
                aws s3 rm "s3://$S3_BUCKET/$file_path"
            fi
        done
    fi

    log "Cleanup completed"
}

# Verify backup integrity
verify_backups() {
    log "Verifying backup integrity..."

    local errors=0

    # Check if backup files exist and are not empty
    for backup_type in database redis files config; do
        local latest_backup=$(find "$BACKUP_DIR" -name "${backup_type}_backup_*.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)

        if [[ -n "$latest_backup" && -s "$latest_backup" ]]; then
            log "✅ $backup_type backup verified: $latest_backup"
        else
            log "❌ $backup_type backup verification failed"
            ((errors++))
        fi
    done

    return $errors
}

# Main backup execution
main() {
    log "🎬 Starting Film Industry Time Tracking System backup..."

    local start_time=$(date +%s)
    local exit_code=0

    # Send start notification
    send_slack_notification "Backup process started" "info"

    # Execute backups
    backup_database || exit_code=$?
    backup_redis || exit_code=$?
    backup_files || exit_code=$?
    backup_config || exit_code=$?

    # Cleanup old backups
    cleanup_old_backups

    # Verify backups
    if ! verify_backups; then
        exit_code=1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Send completion notification
    if [[ $exit_code -eq 0 ]]; then
        send_slack_notification "Backup completed successfully in ${duration}s" "success"
        log "✅ Backup completed successfully in ${duration}s"
    else
        send_slack_notification "Backup failed after ${duration}s" "error"
        log "❌ Backup failed after ${duration}s"
    fi

    exit $exit_code
}

# Handle script arguments
case "${1:-all}" in
    database)
        backup_database
        ;;
    redis)
        backup_redis
        ;;
    files)
        backup_files
        ;;
    config)
        backup_config
        ;;
    cleanup)
        cleanup_old_backups
        ;;
    verify)
        verify_backups
        ;;
    all)
        main
        ;;
    *)
        echo "Usage: $0 {database|redis|files|config|cleanup|verify|all}"
        exit 1
        ;;
esac