#!/bin/bash
# Film Industry Time Tracking System - Deployment Script

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-staging}"
COMPOSE_FILE="docker-compose.yml"
FORCE_DEPLOY="${FORCE_DEPLOY:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check environment file
    local env_file=".env.${ENVIRONMENT}"
    if [[ ! -f "$env_file" ]]; then
        log_error "Environment file $env_file not found"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Load environment variables
load_environment() {
    log "Loading environment variables for $ENVIRONMENT..."

    local env_file=".env.${ENVIRONMENT}"
    if [[ -f "$env_file" ]]; then
        set -a
        source "$env_file"
        set +a
        log_success "Environment variables loaded"
    else
        log_error "Environment file $env_file not found"
        exit 1
    fi
}

# Set compose file based on environment
set_compose_file() {
    case "$ENVIRONMENT" in
        "production")
            COMPOSE_FILE="docker-compose.prod.yml"
            ;;
        "staging")
            COMPOSE_FILE="docker-compose.yml"
            ;;
        "development")
            COMPOSE_FILE="docker-compose.dev.yml"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    log "Using compose file: $COMPOSE_FILE"
}

# Backup current deployment
backup_deployment() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log "Creating backup of current production deployment..."

        local backup_dir="backups/pre-deploy-$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"

        # Backup database
        if docker ps | grep -q "postgres"; then
            docker exec film-tracker-postgres pg_dump \
                -U "${POSTGRES_USER:-postgres}" \
                -d "${POSTGRES_DB:-film_tracker}" \
                > "$backup_dir/database_backup.sql"
        fi

        # Backup Redis
        if docker ps | grep -q "redis"; then
            docker exec film-tracker-redis redis-cli BGSAVE
            sleep 5
            docker cp "film-tracker-redis:/data/dump.rdb" "$backup_dir/"
        fi

        log_success "Backup created in $backup_dir"
    fi
}

# Build and deploy
build_and_deploy() {
    log "Building and deploying to $ENVIRONMENT..."

    cd "$PROJECT_ROOT"

    # Stop existing services
    log "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down || true

    # Pull latest images
    log "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull

    # Build services
    log "Building services..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache

    # Start services
    log "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d

    log_success "Deployment completed"
}

# Health checks
health_checks() {
    log "Running health checks..."

    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        log "Health check attempt $attempt/$max_attempts..."

        # Check backend health
        if curl -f http://localhost:3002/api/health &> /dev/null; then
            log_success "Backend health check passed"
            break
        fi

        # Check frontend health
        if curl -f http://localhost:3000 &> /dev/null; then
            log_success "Frontend health check passed"
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Health checks failed after $max_attempts attempts"
            return 1
        fi

        sleep 10
        ((attempt++))
    done

    log_success "All health checks passed"
}

# Run smoke tests
run_smoke_tests() {
    log "Running smoke tests..."

    # Test API endpoints
    local endpoints=(
        "http://localhost:3002/api/health"
        "http://localhost:3002/api/crew"
        "http://localhost:3002/api/projects"
    )

    for endpoint in "${endpoints[@]}"; do
        if curl -f "$endpoint" &> /dev/null; then
            log_success "✅ $endpoint"
        else
            log_error "❌ $endpoint"
            return 1
        fi
    done

    log_success "Smoke tests passed"
}

# Post-deployment cleanup
post_deploy_cleanup() {
    log "Running post-deployment cleanup..."

    # Remove unused Docker images
    docker image prune -f

    # Remove unused containers
    docker container prune -f

    # Remove unused volumes (with caution in production)
    if [[ "$ENVIRONMENT" != "production" ]]; then
        docker volume prune -f
    fi

    log_success "Cleanup completed"
}

# Rollback function
rollback() {
    log_error "Deployment failed, initiating rollback..."

    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" down

    # Restore from backup if available
    local latest_backup=$(find backups -name "pre-deploy-*" -type d | sort | tail -1)
    if [[ -n "$latest_backup" && -d "$latest_backup" ]]; then
        log "Restoring from backup: $latest_backup"

        # Restore database
        if [[ -f "$latest_backup/database_backup.sql" ]]; then
            docker-compose -f "$COMPOSE_FILE" up -d postgres
            sleep 10
            docker exec -i film-tracker-postgres psql \
                -U "${POSTGRES_USER:-postgres}" \
                -d "${POSTGRES_DB:-film_tracker}" \
                < "$latest_backup/database_backup.sql"
        fi
    fi

    log_error "Rollback completed"
}

# Main deployment function
main() {
    log "🎬 Starting Film Industry Time Tracking System deployment to $ENVIRONMENT..."

    # Check if force deploy is enabled
    if [[ "$FORCE_DEPLOY" == "true" ]]; then
        log_warning "Force deploy enabled, skipping some safety checks"
    fi

    # Execute deployment steps
    check_prerequisites
    load_environment
    set_compose_file

    if [[ "$FORCE_DEPLOY" != "true" ]]; then
        backup_deployment
    fi

    if build_and_deploy; then
        if health_checks && run_smoke_tests; then
            post_deploy_cleanup
            log_success "🎉 Deployment to $ENVIRONMENT completed successfully!"
        else
            rollback
            exit 1
        fi
    else
        rollback
        exit 1
    fi
}

# Handle script arguments
case "${1:-help}" in
    staging|production|development)
        main "$@"
        ;;
    health)
        health_checks
        ;;
    rollback)
        rollback
        ;;
    cleanup)
        post_deploy_cleanup
        ;;
    *)
        echo "Usage: $0 {staging|production|development|health|rollback|cleanup}"
        echo ""
        echo "Environment variables:"
        echo "  FORCE_DEPLOY=true    Skip safety checks and force deployment"
        echo ""
        exit 1
        ;;
esac