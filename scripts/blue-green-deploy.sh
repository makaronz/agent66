#!/bin/bash

# Blue-Green Deployment Script for Film Industry Time Tracking System
# This script enables zero-downtime deployments by managing two identical environments

set -euo pipefail

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
BLUE_ENV="blue"
GREEN_ENV="green"
CURRENT_ENV_FILE=".current_env"
HEALTH_CHECK_TIMEOUT=300
HEALTH_CHECK_INTERVAL=10
MAX_RETRIES=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${2:-$NC}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_info() {
    log "$1" "$BLUE"
}

log_success() {
    log "$1" "$GREEN"
}

log_warning() {
    log "$1" "$YELLOW"
}

log_error() {
    log "$1" "$RED"
}

# Get current environment
get_current_env() {
    if [[ -f "$CURRENT_ENV_FILE" ]]; then
        cat "$CURRENT_ENV_FILE"
    else
        echo "$BLUE_ENV"
    fi
}

# Get target environment (the one that's not currently active)
get_target_env() {
    local current=$(get_current_env)
    if [[ "$current" == "$BLUE_ENV" ]]; then
        echo "$GREEN_ENV"
    else
        echo "$BLUE_ENV"
    fi
}

# Set current environment
set_current_env() {
    echo "$1" > "$CURRENT_ENV_FILE"
}

# Check if environment is healthy
check_health() {
    local env=$1
    local url=$2
    local retries=0

    log_info "Checking health of $env environment at $url"

    while [[ $retries -lt $MAX_RETRIES ]]; do
        if curl -f -s "$url/api/health" > /dev/null; then
            log_success "$env environment is healthy"
            return 0
        fi

        retries=$((retries + 1))
        log_warning "Health check attempt $retries/$MAX_RETRIES failed for $env"
        sleep $HEALTH_CHECK_INTERVAL
    done

    log_error "Health check failed for $env after $MAX_RETRIES attempts"
    return 1
}

# Scale up service
scale_service() {
    local env=$1
    local service=$2
    local replicas=$3

    log_info "Scaling $service to $replicas replicas in $env environment"
    docker-compose -f "$COMPOSE_FILE" -p "film-tracker-$env" up -d --scale "$service=$replicas"
}

# Deploy to target environment
deploy_to_env() {
    local env=$1
    local tag=$2

    log_info "Deploying to $env environment with tag: $tag"

    # Export environment variables
    export ENVIRONMENT="$env"
    export IMAGE_TAG="$tag"

    # Pull latest images
    docker-compose -f "$COMPOSE_FILE" -p "film-tracker-$env" pull

    # Deploy services
    docker-compose -f "$COMPOSE_FILE" -p "film-tracker-$env" up -d

    log_info "Deployment to $env environment completed"
}

# Switch traffic to target environment
switch_traffic() {
    local target_env=$1
    local current_env=$2

    log_info "Switching traffic from $current_env to $target_env"

    # Update load balancer configuration
    # This is a placeholder - implement based on your load balancer
    # For example, update Nginx upstream or AWS ALB target group

    # For Docker-based load balancer
    if [[ "$target_env" == "$BLUE_ENV" ]]; then
        docker-compose -f "docker-compose.lb.yml" up -d --scale nginx-lb=1
    else
        docker-compose -f "docker-compose.lb.yml" up -d --scale nginx-lb=1
    fi

    set_current_env "$target_env"
    log_success "Traffic switched to $target_env environment"
}

# Cleanup old environment
cleanup_old_env() {
    local env=$1

    log_info "Cleaning up old $env environment"
    docker-compose -f "$COMPOSE_FILE" -p "film-tracker-$env" down
    log_success "Old $env environment cleaned up"
}

# Rollback function
rollback() {
    local target_env=$1

    log_warning "Initiating rollback to $target_env environment"
    switch_traffic "$target_env" "$(get_current_env)"
    log_success "Rollback completed"
}

# Main deployment function
main() {
    local image_tag=${1:-latest}
    local skip_health_check=${2:-false}

    log_info "Starting blue-green deployment"
    log_info "Image tag: $image_tag"

    # Get current and target environments
    local current_env=$(get_current_env)
    local target_env=$(get_target_env)

    log_info "Current environment: $current_env"
    log_info "Target environment: $target_env"

    # Trap for cleanup on failure
    trap 'log_error "Deployment failed. Check logs for details."; exit 1' ERR

    # Deploy to target environment
    deploy_to_env "$target_env" "$image_tag"

    # Health check
    if [[ "$skip_health_check" != "true" ]]; then
        # Determine health check URL based on environment
        local health_url="http://localhost"
        if [[ "$target_env" == "$BLUE_ENV" ]]; then
            health_url="http://localhost:8080"
        else
            health_url="http://localhost:8081"
        fi

        if ! check_health "$target_env" "$health_url"; then
            log_error "Health check failed for $target_env environment"
            log_info "Rolling back to $current_env environment"
            rollback "$current_env"
            exit 1
        fi
    fi

    # Switch traffic
    switch_traffic "$target_env" "$current_env"

    # Cleanup old environment (optional)
    read -p "Clean up old $current_env environment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_old_env "$current_env"
    fi

    log_success "Blue-green deployment completed successfully"
    log_info "Active environment: $(get_current_env)"
}

# Parse command line arguments
case "${1:-}" in
    "rollback")
        current_env=$(get_current_env)
        target_env=$(get_target_env)
        rollback "$target_env"
        ;;
    "status")
        current_env=$(get_current_env)
        log_info "Current active environment: $current_env"
        log_info "Target environment: $(get_target_env)"

        # Show running containers
        echo
        log_info "Running containers:"
        docker-compose -f "$COMPOSE_FILE" -p "film-tracker-$current_env" ps
        ;;
    "health")
        current_env=$(get_current_env)
        health_url="http://localhost"
        if [[ "$current_env" == "$BLUE_ENV" ]]; then
            health_url="http://localhost:8080"
        else
            health_url="http://localhost:8081"
        fi

        if check_health "$current_env" "$health_url"; then
            log_success "Current environment is healthy"
        else
            log_error "Current environment is unhealthy"
            exit 1
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Blue-Green Deployment Script"
        echo
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo
        echo "Commands:"
        echo "  deploy [TAG]       Deploy with specified image tag (default: latest)"
        echo "  rollback           Rollback to previous environment"
        echo "  status             Show current deployment status"
        echo "  health             Check health of current environment"
        echo "  help               Show this help message"
        echo
        echo "Examples:"
        echo "  $0 deploy v1.2.3"
        echo "  $0 deploy latest"
        echo "  $0 rollback"
        echo "  $0 status"
        ;;
    *)
        main "${1:-latest}" "${2:-false}"
        ;;
esac