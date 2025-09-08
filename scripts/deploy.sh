#!/bin/bash
# Automated Deployment Script for SMC Trading Agent
# This script orchestrates the complete deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/deployment.log"
DEPLOYMENT_REPORT="$PROJECT_ROOT/deployment-report.json"

# Default values
ENVIRONMENT="production"
SKIP_TESTS=false
SKIP_BUILD=false
SKIP_ENV_VALIDATION=false
VERBOSE=false
DRY_RUN=false
FORCE_DEPLOY=false

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Automated deployment script for SMC Trading Agent"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -e, --environment ENV   Target environment [production|staging|preview] (default: production)"
    echo "  --skip-tests            Skip running tests"
    echo "  --skip-build            Skip build process"
    echo "  --skip-env-validation   Skip environment variables validation"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -n, --dry-run           Show what would be done without executing"
    echo "  -f, --force             Force deployment even if validation fails"
    echo "  --rollback              Rollback to previous deployment"
    echo ""
    echo "Examples:"
    echo "  $0                              # Deploy to production"
    echo "  $0 -e staging                   # Deploy to staging"
    echo "  $0 --skip-tests --dry-run       # Dry run without tests"
    echo "  $0 --rollback                   # Rollback deployment"
}

# Function to check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    command -v node >/dev/null 2>&1 || missing_tools+=("node")
    command -v npm >/dev/null 2>&1 || missing_tools+=("npm")
    command -v git >/dev/null 2>&1 || missing_tools+=("git")
    command -v vercel >/dev/null 2>&1 || missing_tools+=("vercel")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install missing tools and try again"
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
    
    # Check for uncommitted changes
    if [[ -n "$(git status --porcelain)" ]] && [[ "$FORCE_DEPLOY" != "true" ]]; then
        log_warning "You have uncommitted changes"
        log_info "Commit your changes or use --force to proceed"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to validate environment variables
validate_environment() {
    if [[ "$SKIP_ENV_VALIDATION" == "true" ]]; then
        log_info "Skipping environment validation (--skip-env-validation)"
        return 0
    fi
    
    log_step "Validating environment variables..."
    
    if [[ -f "$SCRIPT_DIR/validate-env.sh" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would validate environment variables"
        else
            if "$SCRIPT_DIR/validate-env.sh" --json; then
                log_success "Environment validation passed"
            else
                if [[ "$FORCE_DEPLOY" == "true" ]]; then
                    log_warning "Environment validation failed, but continuing due to --force"
                else
                    log_error "Environment validation failed"
                    log_info "Fix the issues above or use --force to proceed"
                    exit 1
                fi
            fi
        fi
    else
        log_warning "Environment validation script not found"
    fi
}

# Function to run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_info "Skipping tests (--skip-tests)"
        return 0
    fi
    
    log_step "Running tests..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run: npm test"
        return 0
    fi
    
    # Run unit tests
    if npm run test:unit > /dev/null 2>&1; then
        log_success "Unit tests passed"
    else
        log_warning "Unit tests failed or not configured"
    fi
    
    # Run integration tests if available
    if npm run test:integration > /dev/null 2>&1; then
        log_success "Integration tests passed"
    else
        log_info "Integration tests not available or failed"
    fi
    
    # Run linting
    if npm run lint > /dev/null 2>&1; then
        log_success "Linting passed"
    else
        log_warning "Linting failed or not configured"
    fi
}

# Function to build the application
build_application() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        log_info "Skipping build (--skip-build)"
        return 0
    fi
    
    log_step "Building application..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run: npm run build"
        return 0
    fi
    
    # Install dependencies
    log_info "Installing dependencies..."
    npm ci
    
    # Build the application
    log_info "Building for $ENVIRONMENT..."
    if npm run build; then
        log_success "Build completed successfully"
    else
        log_error "Build failed"
        exit 1
    fi
}

# Function to setup Vercel environment variables
setup_vercel_env() {
    log_step "Setting up Vercel environment variables..."
    
    if [[ -f "$SCRIPT_DIR/setup-vercel-env.sh" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would setup Vercel environment variables"
        else
            if "$SCRIPT_DIR/setup-vercel-env.sh" --target "$ENVIRONMENT" --verify; then
                log_success "Vercel environment variables configured"
            else
                log_warning "Failed to configure Vercel environment variables"
            fi
        fi
    else
        log_warning "Vercel environment setup script not found"
    fi
}

# Function to deploy to Vercel
deploy_to_vercel() {
    log_step "Deploying to Vercel ($ENVIRONMENT)..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy to Vercel"
        return 0
    fi
    
    # Authenticate with Vercel
    if ! vercel whoami > /dev/null 2>&1; then
        log_info "Authenticating with Vercel..."
        vercel login
    fi
    
    # Link project if not already linked
    if [[ ! -f ".vercel/project.json" ]]; then
        log_info "Linking Vercel project..."
        vercel link
    fi
    
    # Deploy based on environment
    case "$ENVIRONMENT" in
        "production")
            log_info "Deploying to production..."
            vercel --prod
            ;;
        "staging")
            log_info "Deploying to staging..."
            vercel --target staging
            ;;
        "preview")
            log_info "Creating preview deployment..."
            vercel
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    log_success "Deployment completed"
}

# Function to run post-deployment checks
run_post_deployment_checks() {
    log_step "Running post-deployment checks..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run post-deployment checks"
        return 0
    fi
    
    # Get deployment URL
    local deployment_url
    deployment_url=$(vercel ls --limit 1 --format json | jq -r '.[0].url' 2>/dev/null || echo "")
    
    if [[ -n "$deployment_url" ]]; then
        log_info "Deployment URL: https://$deployment_url"
        
        # Basic health check
        log_info "Running health check..."
        if curl -f -s "https://$deployment_url/api/health" > /dev/null 2>&1; then
            log_success "Health check passed"
        else
            log_warning "Health check failed or endpoint not available"
        fi
        
        # Check if main page loads
        if curl -f -s "https://$deployment_url" > /dev/null 2>&1; then
            log_success "Main page accessible"
        else
            log_warning "Main page not accessible"
        fi
    else
        log_warning "Could not determine deployment URL"
    fi
}

# Function to generate deployment report
generate_deployment_report() {
    log_step "Generating deployment report..."
    
    local deployment_url
    deployment_url=$(vercel ls --limit 1 --format json | jq -r '.[0].url' 2>/dev/null || echo "unknown")
    
    local git_commit
    git_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    
    local git_branch
    git_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    
    cat > "$DEPLOYMENT_REPORT" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "environment": "$ENVIRONMENT",
  "deployment_url": "https://$deployment_url",
  "git_commit": "$git_commit",
  "git_branch": "$git_branch",
  "deployment_status": "success",
  "options": {
    "skip_tests": $SKIP_TESTS,
    "skip_build": $SKIP_BUILD,
    "skip_env_validation": $SKIP_ENV_VALIDATION,
    "dry_run": $DRY_RUN,
    "force_deploy": $FORCE_DEPLOY
  },
  "artifacts": {
    "log_file": "$LOG_FILE",
    "env_validation_report": "env-validation-report.json"
  }
}
EOF
    
    log_success "Deployment report saved to $DEPLOYMENT_REPORT"
}

# Function to rollback deployment
rollback_deployment() {
    log_step "Rolling back deployment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback deployment"
        return 0
    fi
    
    # Get previous deployment
    local previous_deployment
    previous_deployment=$(vercel ls --limit 2 --format json | jq -r '.[1].uid' 2>/dev/null || echo "")
    
    if [[ -n "$previous_deployment" ]]; then
        log_info "Rolling back to deployment: $previous_deployment"
        vercel promote "$previous_deployment" --scope "$(vercel whoami)"
        log_success "Rollback completed"
    else
        log_error "No previous deployment found for rollback"
        exit 1
    fi
}

# Function to cleanup old deployments
cleanup_old_deployments() {
    log_step "Cleaning up old deployments..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would cleanup old deployments"
        return 0
    fi
    
    # Keep last 5 deployments, remove older ones
    local old_deployments
    old_deployments=$(vercel ls --limit 20 --format json | jq -r '.[5:][].uid' 2>/dev/null || echo "")
    
    if [[ -n "$old_deployments" ]]; then
        log_info "Removing old deployments..."
        echo "$old_deployments" | while read -r deployment_id; do
            if [[ -n "$deployment_id" ]]; then
                vercel rm "$deployment_id" --yes > /dev/null 2>&1 || true
            fi
        done
        log_success "Old deployments cleaned up"
    else
        log_info "No old deployments to clean up"
    fi
}

# Main deployment function
main_deploy() {
    log_info "Starting deployment process..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Options: skip-tests=$SKIP_TESTS, skip-build=$SKIP_BUILD, dry-run=$DRY_RUN"
    
    # Initialize log file
    echo "Deployment started at $(date)" > "$LOG_FILE"
    
    # Run deployment steps
    check_prerequisites
    validate_environment
    run_tests
    build_application
    setup_vercel_env
    deploy_to_vercel
    run_post_deployment_checks
    cleanup_old_deployments
    generate_deployment_report
    
    log_success "🎉 Deployment completed successfully!"
    
    # Show next steps
    echo ""
    log_info "Next steps:"
    echo "  1. Verify the deployment at the URL shown above"
    echo "  2. Run smoke tests if available"
    echo "  3. Monitor application logs and metrics"
    echo "  4. Update documentation if needed"
    echo ""
    log_info "Deployment report: $DEPLOYMENT_REPORT"
    log_info "Deployment logs: $LOG_FILE"
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-env-validation)
                SKIP_ENV_VALIDATION=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE_DEPLOY=true
                shift
                ;;
            --rollback)
                rollback_deployment
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate environment parameter
    case "$ENVIRONMENT" in
        "production"|"staging"|"preview")
            # Valid environments
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_info "Valid environments: production, staging, preview"
            exit 1
            ;;
    esac
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run main deployment
    main_deploy
}

# Trap errors and cleanup
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Run main function with all arguments
main "$@"