#!/bin/bash

# =============================================================================
# SMC Trading Agent - Configuration Validation Script
# =============================================================================
# This script validates all configuration files before deployment
# Usage: ./scripts/validate_config.sh [environment]

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Environment (default: production)
ENVIRONMENT="${1:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation results
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0

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
    ((VALIDATION_WARNINGS++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((VALIDATION_ERRORS++))
}

# =============================================================================
# YAML VALIDATION
# =============================================================================
validate_yaml() {
    local file="$1"
    log_info "Validating YAML file: $file"

    if command -v python3 &> /dev/null; then
        if python3 -c "
import yaml
import sys
try:
    with open('$file', 'r') as f:
        yaml.safe_load(f)
    print('✓ YAML syntax is valid')
except yaml.YAMLError as e:
    print(f'✗ YAML syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'✗ Error reading file: {e}')
    sys.exit(1)
"; then
            log_success "YAML validation passed: $file"
        else
            log_error "YAML validation failed: $file"
            return 1
        fi
    else
        log_warning "Python3 not available, skipping YAML syntax validation for $file"
    fi
}

# =============================================================================
# JSON VALIDATION
# =============================================================================
validate_json() {
    local file="$1"
    log_info "Validating JSON file: $file"

    if command -v python3 &> /dev/null; then
        if python3 -c "
import json
import sys
try:
    with open('$file', 'r') as f:
        json.load(f)
    print('✓ JSON syntax is valid')
except json.JSONDecodeError as e:
    print(f'✗ JSON syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'✗ Error reading file: {e}')
    sys.exit(1)
"; then
            log_success "JSON validation passed: $file"
        else
            log_error "JSON validation failed: $file"
            return 1
        fi
    else
        log_warning "Python3 not available, skipping JSON syntax validation for $file"
    fi
}

# =============================================================================
# ENVIRONMENT VARIABLE VALIDATION
# =============================================================================
validate_env_file() {
    local env_file="$1"
    log_info "Validating environment file: $env_file"

    if [[ ! -f "$env_file" ]]; then
        log_error "Environment file not found: $env_file"
        return 1
    fi

    # Check for common issues
    local issues=0

    # Check for spaces around equals signs
    if grep -q " = " "$env_file"; then
        log_error "Spaces around '=' found in $env_file"
        ((issues++))
    fi

    # Check for unquoted values with special characters
    if grep -E "^[A-Z_]+=[^'\"]*[&|;$]" "$env_file"; then
        log_warning "Unquoted values with special characters found in $env_file"
        ((issues++))
    fi

    # Check for empty values
    local empty_vars
    empty_vars=$(grep -E "^[A-Z_]+=$" "$env_file" | wc -l)
    if [[ $empty_vars -gt 0 ]]; then
        log_warning "$empty_vars empty variable values found in $env_file"
        ((issues++))
    fi

    # Check for duplicate variables
    local duplicates
    duplicates=$(cut -d= -f1 "$env_file" | sort | uniq -d | wc -l)
    if [[ $duplicates -gt 0 ]]; then
        log_error "$duplicates duplicate variables found in $env_file"
        ((issues++))
    fi

    if [[ $issues -eq 0 ]]; then
        log_success "Environment file validation passed: $env_file"
    else
        log_error "Environment file validation failed: $env_file ($issues issues)"
        return 1
    fi
}

# =============================================================================
# CONFIGURATION CONTENT VALIDATION
# =============================================================================
validate_config_content() {
    local config_file="$1"
    log_info "Validating configuration content: $config_file"

    # Check for required sections
    local required_sections=(
        "app"
        "exchanges"
        "risk_management"
        "monitoring"
        "logging"
    )

    for section in "${required_sections[@]}"; do
        if ! grep -q "^$section:" "$config_file"; then
            log_error "Required section '$section' not found in $config_file"
            return 1
        fi
    done

    # Check for environment variable placeholders
    local unresolved_vars
    unresolved_vars=$(grep -o '\${[^}]*}' "$config_file" | sort -u | wc -l)
    if [[ $unresolved_vars -gt 10 ]]; then
        log_warning "High number of unresolved environment variables ($unresolved_vars) in $config_file"
    fi

    # Check for placeholder values
    if grep -q "your_.*_here" "$config_file"; then
        log_error "Placeholder values found in $config_file"
        return 1
    fi

    # Check for production-specific settings
    if [[ "$ENVIRONMENT" == "production" ]]; then
        if grep -q "environment.*development" "$config_file"; then
            log_error "Development environment found in production config: $config_file"
            return 1
        fi

        if grep -q "debug.*true" "$config_file"; then
            log_error "Debug mode enabled in production config: $config_file"
            return 1
        fi

        if grep -q "testnet.*true" "$config_file"; then
            log_error "Testnet enabled in production config: $config_file"
            return 1
        fi
    fi

    log_success "Configuration content validation passed: $config_file"
}

# =============================================================================
# SECURITY VALIDATION
# =============================================================================
validate_security() {
    local config_file="$1"
    log_info "Validating security configuration: $config_file"

    # Check for hardcoded secrets
    if grep -qi "password.*password" "$config_file"; then
        log_error "Potential hardcoded password found in $config_file"
        return 1
    fi

    # Check for default passwords
    if grep -qi "admin.*password.*admin" "$config_file"; then
        log_error "Default admin password found in $config_file"
        return 1
    fi

    # Check for weak security settings
    if grep -qi "ssl_mode.*disable" "$config_file"; then
        log_error "SSL disabled in configuration: $config_file"
        return 1
    fi

    # Check for missing JWT secret
    if ! grep -q "jwt_secret" "$config_file"; then
        log_error "JWT secret not configured in $config_file"
        return 1
    fi

    # Check for API key configuration
    if ! grep -q "api_key.*\${" "$config_file"; then
        log_warning "API keys should use environment variables in $config_file"
    fi

    log_success "Security validation passed: $config_file"
}

# =============================================================================
# DOCKER COMPOSE VALIDATION
# =============================================================================
validate_docker_compose() {
    local compose_file="$1"
    log_info "Validating Docker Compose file: $compose_file"

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_warning "Docker Compose not available, skipping validation"
        return 0
    fi

    # Validate Docker Compose syntax
    if docker-compose -f "$compose_file" config --quiet; then
        log_success "Docker Compose validation passed: $compose_file"
    else
        log_error "Docker Compose validation failed: $compose_file"
        return 1
    fi

    # Check for common Docker Compose issues
    local issues=0

    # Check for exposed ports (warning in production)
    if [[ "$ENVIRONMENT" == "production" ]]; then
        local exposed_ports
        exposed_ports=$(grep -E "ports:\s*-\s*\"[0-9]+" "$compose_file" | wc -l)
        if [[ $exposed_ports -gt 0 ]]; then
            log_warning "$exposed_ports ports exposed to host in production Docker Compose"
            ((issues++))
        fi
    fi

    # Check for health checks
    local services_with_health_checks
    services_with_health_checks=$(grep -A 10 "healthcheck:" "$compose_file" | wc -l)
    if [[ $services_with_health_checks -lt 3 ]]; then
        log_warning "Insufficient health checks in Docker Compose"
        ((issues++))
    fi

    # Check for resource limits
    local services_with_limits
    services_with_limits=$(grep -A 5 "deploy:" "$compose_file" | grep -c "limits:" || true)
    if [[ $services_with_limits -lt 2 ]]; then
        log_warning "Insufficient resource limits in Docker Compose"
        ((issues++))
    fi

    if [[ $issues -eq 0 ]]; then
        log_success "Docker Compose best practices validation passed"
    fi
}

# =============================================================================
# DEPENDENCY VALIDATION
# =============================================================================
validate_dependencies() {
    log_info "Validating system dependencies"

    local missing_deps=()
    local optional_deps=()

    # Required dependencies
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi

    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi

    # Optional dependencies
    if ! command -v python3 &> /dev/null; then
        optional_deps+=("python3")
    fi

    if ! command -v curl &> /dev/null; then
        optional_deps+=("curl")
    fi

    # Report missing dependencies
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        return 1
    fi

    # Report optional dependencies
    if [[ ${#optional_deps[@]} -gt 0 ]]; then
        log_warning "Missing optional dependencies: ${optional_deps[*]}"
    fi

    log_success "System dependencies validation passed"
}

# =============================================================================
# NETWORK CONNECTIVITY VALIDATION
# =============================================================================
validate_network() {
    log_info "Validating network connectivity"

    local failed_hosts=()

    # Check connectivity to exchanges
    local exchanges=(
        "api.binance.com"
        "api.bybit.com"
        "api-fxpractice.oanda.com"
    )

    for host in "${exchanges[@]}"; do
        if ! curl -s --connect-timeout 5 "https://$host" > /dev/null; then
            failed_hosts+=("$host")
        fi
    done

    if [[ ${#failed_hosts[@]} -gt 0 ]]; then
        log_warning "Cannot reach some exchanges: ${failed_hosts[*]}"
    else
        log_success "Network connectivity validation passed"
    fi
}

# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================
main() {
    log_info "Starting configuration validation for $ENVIRONMENT environment"
    log_info "Validation started at: $(date)"

    # Change to project directory
    cd "$PROJECT_ROOT"

    # Define configuration files based on environment
    local config_file
    local env_file
    local docker_compose_file
    local ml_config_file

    case "$ENVIRONMENT" in
        "production")
            config_file="config.production.yaml"
            env_file=".env"
            docker_compose_file="docker-compose.production.yml"
            ml_config_file="config/ml_config.production.json"
            ;;
        "staging")
            config_file="config.staging.yaml"
            env_file=".env.staging"
            docker_compose_file="docker-compose.staging.yml"
            ml_config_file="config/ml_config.staging.json"
            ;;
        "development")
            config_file="config.yaml"
            env_file=".env"
            docker_compose_file="docker-compose.yml"
            ml_config_file="config/ml_config.json"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            exit 1
            ;;
    esac

    # Validate dependencies first
    validate_dependencies

    # Validate environment file
    if [[ -f "$env_file" ]]; then
        validate_env_file "$env_file"
    else
        log_error "Environment file not found: $env_file"
    fi

    # Validate main configuration file
    if [[ -f "$config_file" ]]; then
        validate_yaml "$config_file"
        validate_config_content "$config_file"
        validate_security "$config_file"
    else
        log_error "Configuration file not found: $config_file"
    fi

    # Validate ML configuration
    if [[ -f "$ml_config_file" ]]; then
        validate_json "$ml_config_file"
    else
        log_warning "ML configuration file not found: $ml_config_file"
    fi

    # Validate Docker Compose
    if [[ -f "$docker_compose_file" ]]; then
        validate_docker_compose "$docker_compose_file"
    else
        log_error "Docker Compose file not found: $docker_compose_file"
    fi

    # Validate network connectivity (only for production)
    if [[ "$ENVIRONMENT" == "production" ]]; then
        validate_network
    fi

    # =============================================================================
    # VALIDATION SUMMARY
    # =============================================================================
    echo
    echo "=============================================="
    echo "VALIDATION SUMMARY"
    echo "=============================================="

    if [[ $VALIDATION_ERRORS -eq 0 ]]; then
        log_success "✅ All critical validations passed!"

        if [[ $VALIDATION_WARNINGS -eq 0 ]]; then
            log_success "🎉 Configuration is ready for deployment!"
        else
            log_warning "⚠️  $VALIDATION_WARNINGS warnings found. Review before deployment."
        fi
    else
        log_error "❌ $VALIDATION_ERRORS validation errors found!"
        log_error "Please fix errors before deployment."
        exit 1
    fi

    log_info "Validation completed at: $(date)"
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi