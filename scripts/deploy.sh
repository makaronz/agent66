#!/bin/bash

# =============================================================================
# SMC Trading Agent - Production Deployment Script
# =============================================================================
# This script orchestrates the production deployment of the SMC Trading Agent
# Usage: ./scripts/deploy.sh [environment]
# Environment: production (default), staging, development

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default environment
ENVIRONMENT="${1:-production}"

# Configuration files based on environment
case "$ENVIRONMENT" in
    "production")
        CONFIG_FILE="config.production.yaml"
        DOCKER_COMPOSE_FILE="docker-compose.production.yml"
        ENV_FILE=".env"
        ;;
    "staging")
        CONFIG_FILE="config.staging.yaml"
        DOCKER_COMPOSE_FILE="docker-compose.staging.yml"
        ENV_FILE=".env.staging"
        ;;
    "development")
        CONFIG_FILE="config.yaml"
        DOCKER_COMPOSE_FILE="docker-compose.yml"
        ENV_FILE=".env"
        ;;
    *)
        echo "❌ Invalid environment: $ENVIRONMENT"
        echo "Usage: $0 [production|staging|development]"
        exit 1
        ;;
esac

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# PRE-DEPLOYMENT CHECKS
# =============================================================================
check_prerequisites() {
    log_info "Checking deployment prerequisites..."

    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi

    # Check if required files exist
    local required_files=(
        "$PROJECT_ROOT/$CONFIG_FILE"
        "$PROJECT_ROOT/$DOCKER_COMPOSE_FILE"
        "$PROJECT_ROOT/$ENV_FILE"
        "$PROJECT_ROOT/Dockerfile"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done

    log_success "All prerequisites satisfied"
}

check_environment_variables() {
    log_info "Checking environment variables..."

    # Source the environment file
    if [[ -f "$PROJECT_ROOT/$ENV_FILE" ]]; then
        source "$PROJECT_ROOT/$ENV_FILE"
    else
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi

    # Critical variables for production
    local critical_vars=(
        "BINANCE_API_KEY"
        "BINANCE_API_SECRET"
        "DB_PASSWORD"
        "REDIS_PASSWORD"
        "JWT_SECRET"
        "GRAFANA_PASSWORD"
    )

    local missing_vars=()

    for var in "${critical_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing critical environment variables:"
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        exit 1
    fi

    log_success "All environment variables are set"
}

check_disk_space() {
    log_info "Checking available disk space..."

    local available_space
    available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    local required_space=10485760  # 10GB in KB

    if [[ $available_space -lt $required_space ]]; then
        log_error "Insufficient disk space. Required: 10GB, Available: $((available_space / 1024 / 1024))GB"
        exit 1
    fi

    log_success "Sufficient disk space available"
}

check_network_connectivity() {
    log_info "Checking network connectivity..."

    # Check if we can reach the exchanges
    local exchanges=(
        "api.binance.com"
        "api.bybit.com"
        "api-fxpractice.oanda.com"
    )

    for exchange in "${exchanges[@]}"; do
        if ! curl -s --connect-timeout 5 "https://$exchange" > /dev/null; then
            log_warning "Cannot reach $exchange. Check network connectivity."
        fi
    done

    log_success "Network connectivity check completed"
}

# =============================================================================
# DEPLOYMENT FUNCTIONS
# =============================================================================
build_images() {
    log_info "Building Docker images..."

    cd "$PROJECT_ROOT"

    # Build with no cache to ensure fresh images
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache

    log_success "Docker images built successfully"
}

stop_services() {
    log_info "Stopping existing services..."

    cd "$PROJECT_ROOT"

    # Stop and remove existing containers
    docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans || true

    log_success "Existing services stopped"
}

start_services() {
    log_info "Starting services..."

    cd "$PROJECT_ROOT"

    # Start services in dependency order
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres redis

    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    sleep 30

    # Start remaining services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

    log_success "All services started"
}

wait_for_services() {
    log_info "Waiting for services to be healthy..."

    local max_attempts=60
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        local healthy_count=0
        local total_services=0

        # Check each service
        local services=("postgres" "redis" "prometheus" "grafana" "smc-trading-agent")

        for service in "${services[@]}"; do
            ((total_services++))

            if docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q "$service" | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
                ((healthy_count++))
            elif docker-compose -f "$DOCKER_COMPOSE_FILE" ps "$service" | grep -q "Up"; then
                # Service is running but might not have health check
                ((healthy_count++))
            fi
        done

        log_info "Health check: $healthy_count/$total_services services healthy"

        if [[ $healthy_count -eq $total_services ]]; then
            log_success "All services are healthy"
            return 0
        fi

        sleep 10
        ((attempt++))
    done

    log_error "Services failed to become healthy within expected time"
    return 1
}

# =============================================================================
# POST-DEPLOYMENT VERIFICATION
# =============================================================================
verify_deployment() {
    log_info "Verifying deployment..."

    # Check if main application is responding
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f "http://localhost:8000/health" > /dev/null 2>&1; then
            log_success "Main application is responding"
            break
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Main application failed to respond"
            return 1
        fi

        sleep 5
        ((attempt++))
    done

    log_success "Deployment verification completed"
}

run_health_checks() {
    log_info "Running comprehensive health checks..."

    # System health check
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T smc-trading-agent python -c "
import requests
import sys
try:
    response = requests.get('http://localhost:8080/health', timeout=10)
    response.raise_for_status()
    print('✓ System health check passed')
except Exception as e:
    print(f'✗ System health check failed: {e}')
    sys.exit(1)
"; then
        log_success "System health checks passed"
    else
        log_error "System health checks failed"
        return 1
    fi

    log_success "All health checks passed"
}

# =============================================================================
# MAIN DEPLOYMENT FLOW
# =============================================================================
main() {
    log_info "Starting SMC Trading Agent deployment to $ENVIRONMENT environment"
    log_info "Deployment started at: $(date)"

    # Change to project directory
    cd "$PROJECT_ROOT"

    # Run pre-deployment checks
    check_prerequisites
    check_environment_variables

    if [[ "$ENVIRONMENT" == "production" ]]; then
        check_disk_space
        check_network_connectivity
    fi

    # Deployment process
    build_images
    stop_services
    start_services

    # Verify deployment
    if wait_for_services && verify_deployment && run_health_checks; then
        log_success "🎉 Deployment completed successfully!"
        log_info "Services are now running:"
        log_info "  - Main Application: http://localhost:8000"
        log_info "  - Grafana Dashboard: http://localhost:3000"
        log_info "  - Prometheus Metrics: http://localhost:9090"

        log_info "Deployment completed at: $(date)"
    else
        log_error "Deployment verification failed"
        exit 1
    fi
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi