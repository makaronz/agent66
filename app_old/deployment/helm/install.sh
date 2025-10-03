#!/bin/bash

# SMC Trading Agent Helm Chart Installation Script
# This script automates the installation and management of the SMC Trading Agent Helm chart

set -euo pipefail

# Configuration
CHART_NAME="smc-trading-agent"
CHART_PATH="./smc-trading-agent"
DEFAULT_NAMESPACE="smc-trading"
DEFAULT_RELEASE_NAME="smc-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Help function
show_help() {
    cat << EOF
SMC Trading Agent Helm Chart Installation Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    install         Install the Helm chart
    upgrade         Upgrade existing installation
    uninstall       Uninstall the Helm chart
    status          Show installation status
    test            Run Helm tests
    lint            Lint the Helm chart
    template        Generate Kubernetes manifests
    package         Package the Helm chart
    dependency      Update chart dependencies
    rollback        Rollback to previous version
    help            Show this help message

Options:
    -n, --namespace NAMESPACE       Kubernetes namespace (default: $DEFAULT_NAMESPACE)
    -r, --release RELEASE          Helm release name (default: $DEFAULT_RELEASE_NAME)
    -e, --environment ENV          Environment (development|staging|production)
    -f, --values-file FILE         Custom values file
    -v, --version VERSION          Chart version to install
    --dry-run                      Perform a dry run
    --wait                         Wait for deployment to complete
    --timeout TIMEOUT             Timeout for operations (default: 300s)
    --create-namespace             Create namespace if it doesn't exist
    --atomic                       Atomic installation (rollback on failure)
    --debug                        Enable debug output
    --force                        Force operation
    -h, --help                     Show this help message

Examples:
    # Install in development environment
    $0 install -e development
    
    # Install in production with custom values
    $0 install -e production -f custom-values.yaml
    
    # Upgrade existing installation
    $0 upgrade -e production --wait
    
    # Check status
    $0 status
    
    # Uninstall
    $0 uninstall

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install Helm first."
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check if chart directory exists
    if [ ! -d "$CHART_PATH" ]; then
        log_error "Chart directory '$CHART_PATH' not found."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Parse command line arguments
parse_args() {
    COMMAND=""
    NAMESPACE="$DEFAULT_NAMESPACE"
    RELEASE_NAME="$DEFAULT_RELEASE_NAME"
    ENVIRONMENT=""
    VALUES_FILE=""
    VERSION=""
    DRY_RUN="false"
    WAIT="false"
    TIMEOUT="300s"
    CREATE_NAMESPACE="false"
    ATOMIC="false"
    DEBUG="false"
    FORCE="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            install|upgrade|uninstall|status|test|lint|template|package|dependency|rollback|help)
                COMMAND="$1"
                shift
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--release)
                RELEASE_NAME="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -f|--values-file)
                VALUES_FILE="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --wait)
                WAIT="true"
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --create-namespace)
                CREATE_NAMESPACE="true"
                shift
                ;;
            --atomic)
                ATOMIC="true"
                shift
                ;;
            --debug)
                DEBUG="true"
                shift
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [ -z "$COMMAND" ]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
}

# Build helm command arguments
build_helm_args() {
    HELM_ARGS=()
    
    if [ "$DRY_RUN" = "true" ]; then
        HELM_ARGS+=("--dry-run")
    fi
    
    if [ "$WAIT" = "true" ]; then
        HELM_ARGS+=("--wait")
    fi
    
    if [ -n "$TIMEOUT" ]; then
        HELM_ARGS+=("--timeout" "$TIMEOUT")
    fi
    
    if [ "$CREATE_NAMESPACE" = "true" ]; then
        HELM_ARGS+=("--create-namespace")
    fi
    
    if [ "$ATOMIC" = "true" ]; then
        HELM_ARGS+=("--atomic")
    fi
    
    if [ "$DEBUG" = "true" ]; then
        HELM_ARGS+=("--debug")
    fi
    
    if [ "$FORCE" = "true" ]; then
        HELM_ARGS+=("--force")
    fi
    
    if [ -n "$VERSION" ]; then
        HELM_ARGS+=("--version" "$VERSION")
    fi
    
    # Add values files based on environment
    if [ -n "$ENVIRONMENT" ]; then
        VALUES_ENV_FILE="$CHART_PATH/values-$ENVIRONMENT.yaml"
        if [ -f "$VALUES_ENV_FILE" ]; then
            HELM_ARGS+=("--values" "$VALUES_ENV_FILE")
            log_info "Using environment values file: $VALUES_ENV_FILE"
        else
            log_warning "Environment values file not found: $VALUES_ENV_FILE"
        fi
    fi
    
    # Add custom values file
    if [ -n "$VALUES_FILE" ]; then
        if [ -f "$VALUES_FILE" ]; then
            HELM_ARGS+=("--values" "$VALUES_FILE")
            log_info "Using custom values file: $VALUES_FILE"
        else
            log_error "Custom values file not found: $VALUES_FILE"
            exit 1
        fi
    fi
}

# Install command
install_chart() {
    log_info "Installing SMC Trading Agent chart..."
    log_info "Release: $RELEASE_NAME"
    log_info "Namespace: $NAMESPACE"
    log_info "Environment: ${ENVIRONMENT:-default}"
    
    build_helm_args
    
    helm install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        "${HELM_ARGS[@]}"
    
    if [ "$DRY_RUN" = "false" ]; then
        log_success "Chart installed successfully!"
        
        # Show status
        log_info "Checking deployment status..."
        kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
        
        # Show service information
        log_info "Service information:"
        kubectl get svc -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    fi
}

# Upgrade command
upgrade_chart() {
    log_info "Upgrading SMC Trading Agent chart..."
    log_info "Release: $RELEASE_NAME"
    log_info "Namespace: $NAMESPACE"
    log_info "Environment: ${ENVIRONMENT:-default}"
    
    build_helm_args
    
    helm upgrade "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        "${HELM_ARGS[@]}"
    
    if [ "$DRY_RUN" = "false" ]; then
        log_success "Chart upgraded successfully!"
        
        # Show status
        log_info "Checking deployment status..."
        kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    fi
}

# Uninstall command
uninstall_chart() {
    log_info "Uninstalling SMC Trading Agent chart..."
    log_info "Release: $RELEASE_NAME"
    log_info "Namespace: $NAMESPACE"
    
    if [ "$DRY_RUN" = "false" ]; then
        read -p "Are you sure you want to uninstall '$RELEASE_NAME'? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Uninstall cancelled"
            exit 0
        fi
    fi
    
    helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE"
    
    log_success "Chart uninstalled successfully!"
}

# Status command
status_chart() {
    log_info "Checking SMC Trading Agent status..."
    
    # Helm status
    helm status "$RELEASE_NAME" --namespace "$NAMESPACE"
    
    # Pod status
    log_info "Pod status:"
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    
    # Service status
    log_info "Service status:"
    kubectl get svc -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    
    # Ingress status (if exists)
    if kubectl get ingress -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" &> /dev/null; then
        log_info "Ingress status:"
        kubectl get ingress -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    fi
}

# Test command
test_chart() {
    log_info "Running Helm tests..."
    
    helm test "$RELEASE_NAME" --namespace "$NAMESPACE"
    
    log_success "Tests completed!"
}

# Lint command
lint_chart() {
    log_info "Linting Helm chart..."
    
    helm lint "$CHART_PATH"
    
    log_success "Lint completed!"
}

# Template command
template_chart() {
    log_info "Generating Kubernetes manifests..."
    
    build_helm_args
    
    helm template "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        "${HELM_ARGS[@]}"
}

# Package command
package_chart() {
    log_info "Packaging Helm chart..."
    
    helm package "$CHART_PATH"
    
    log_success "Chart packaged successfully!"
}

# Dependency command
dependency_chart() {
    log_info "Updating chart dependencies..."
    
    helm dependency update "$CHART_PATH"
    
    log_success "Dependencies updated successfully!"
}

# Rollback command
rollback_chart() {
    log_info "Rolling back SMC Trading Agent chart..."
    
    # Show revision history
    log_info "Revision history:"
    helm history "$RELEASE_NAME" --namespace "$NAMESPACE"
    
    if [ "$DRY_RUN" = "false" ]; then
        read -p "Enter revision number to rollback to (or press Enter for previous): " -r REVISION
        
        if [ -z "$REVISION" ]; then
            helm rollback "$RELEASE_NAME" --namespace "$NAMESPACE"
        else
            helm rollback "$RELEASE_NAME" "$REVISION" --namespace "$NAMESPACE"
        fi
        
        log_success "Rollback completed successfully!"
    fi
}

# Main function
main() {
    parse_args "$@"
    
    if [ "$COMMAND" != "help" ] && [ "$COMMAND" != "lint" ] && [ "$COMMAND" != "template" ] && [ "$COMMAND" != "package" ] && [ "$COMMAND" != "dependency" ]; then
        check_prerequisites
    fi
    
    case $COMMAND in
        install)
            install_chart
            ;;
        upgrade)
            upgrade_chart
            ;;
        uninstall)
            uninstall_chart
            ;;
        status)
            status_chart
            ;;
        test)
            test_chart
            ;;
        lint)
            lint_chart
            ;;
        template)
            template_chart
            ;;
        package)
            package_chart
            ;;
        dependency)
            dependency_chart
            ;;
        rollback)
            rollback_chart
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"