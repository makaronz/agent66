#!/bin/bash
# Setup Vercel Environment Variables Script
# This script automates the process of setting up environment variables for Vercel deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="smc-trading-agent"
ENV_TEMPLATE=".env.production"
ENV_LOCAL=".env.local"
VERCEL_PROJECT_ID=""
VERCEL_ORG_ID=""

# Function to print colored output
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

# Function to check if required tools are installed
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v vercel &> /dev/null; then
        log_error "Vercel CLI is not installed. Install it with: npm install -g vercel"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed. Some features may not work properly."
        log_info "Install jq with: brew install jq (macOS) or apt-get install jq (Ubuntu)"
    fi
    
    log_success "Prerequisites check completed"
}

# Function to authenticate with Vercel
vercel_auth() {
    log_info "Checking Vercel authentication..."
    
    if ! vercel whoami &> /dev/null; then
        log_info "Not authenticated with Vercel. Starting authentication..."
        vercel login
    else
        log_success "Already authenticated with Vercel"
    fi
}

# Function to link Vercel project
link_project() {
    log_info "Linking Vercel project..."
    
    if [ ! -f ".vercel/project.json" ]; then
        log_info "Project not linked. Linking now..."
        vercel link --yes
    else
        log_success "Project already linked"
    fi
    
    # Extract project and org IDs
    if [ -f ".vercel/project.json" ] && command -v jq &> /dev/null; then
        VERCEL_PROJECT_ID=$(jq -r '.projectId' .vercel/project.json)
        VERCEL_ORG_ID=$(jq -r '.orgId' .vercel/project.json)
        log_info "Project ID: $VERCEL_PROJECT_ID"
        log_info "Org ID: $VERCEL_ORG_ID"
    fi
}

# Function to read environment variables from template
read_env_template() {
    log_info "Reading environment variables from $ENV_TEMPLATE..."
    
    if [ ! -f "$ENV_TEMPLATE" ]; then
        log_error "Environment template file $ENV_TEMPLATE not found!"
        exit 1
    fi
    
    # Count variables
    local var_count=$(grep -E '^[A-Z_]+=.*' "$ENV_TEMPLATE" | wc -l | tr -d ' ')
    log_info "Found $var_count environment variables in template"
}

# Function to set environment variables on Vercel
set_vercel_env() {
    local env_name="$1"
    local env_value="$2"
    local target="$3"
    
    log_info "Setting $env_name for $target environment..."
    
    # Use vercel env add command
    echo "$env_value" | vercel env add "$env_name" "$target" --force
    
    if [ $? -eq 0 ]; then
        log_success "✓ $env_name set successfully"
    else
        log_error "✗ Failed to set $env_name"
        return 1
    fi
}

# Function to process environment variables
process_env_vars() {
    local target="$1"
    log_info "Processing environment variables for $target environment..."
    
    local success_count=0
    local error_count=0
    
    # Read variables from template and local env file
    local env_file="$ENV_TEMPLATE"
    if [ -f "$ENV_LOCAL" ] && [ "$target" != "production" ]; then
        env_file="$ENV_LOCAL"
        log_info "Using local environment file: $ENV_LOCAL"
    fi
    
    # Process each variable
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ "$key" =~ ^#.*$ ]] || [[ -z "$key" ]]; then
            continue
        fi
        
        # Remove quotes from value
        value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/' | sed "s/^'\(.*\)'$/\1/")
        
        # Skip placeholder values
        if [[ "$value" =~ ^your_.*$ ]] || [[ "$value" =~ ^\$\{.*\}$ ]] || [[ -z "$value" ]]; then
            log_warning "Skipping $key (placeholder or empty value)"
            continue
        fi
        
        # Set the environment variable
        if set_vercel_env "$key" "$value" "$target"; then
            ((success_count++))
        else
            ((error_count++))
        fi
        
        # Add small delay to avoid rate limiting
        sleep 0.5
        
    done < <(grep -E '^[A-Z_]+=.*' "$env_file")
    
    log_info "Environment variables processing completed:"
    log_success "✓ Successfully set: $success_count variables"
    if [ $error_count -gt 0 ]; then
        log_error "✗ Failed to set: $error_count variables"
    fi
}

# Function to verify environment variables
verify_env_vars() {
    local target="$1"
    log_info "Verifying environment variables for $target environment..."
    
    # List current environment variables
    vercel env ls "$target"
    
    log_success "Environment variables verification completed"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [TARGET]"
    echo ""
    echo "Setup Vercel environment variables from template"
    echo ""
    echo "Arguments:"
    echo "  TARGET          Target environment (preview, production, development) [default: preview]"
    echo ""
    echo "Options:"
    echo "  -h, --help      Show this help message"
    echo "  -v, --verify    Only verify existing environment variables"
    echo "  -f, --force     Force update existing variables"
    echo "  --template FILE Use custom template file [default: .env.production]"
    echo "  --local FILE    Use local environment file for non-production [default: .env.local]"
    echo ""
    echo "Examples:"
    echo "  $0                          # Setup preview environment"
    echo "  $0 production               # Setup production environment"
    echo "  $0 --verify production      # Verify production environment"
    echo "  $0 --template .env.staging  # Use custom template"
}

# Main function
main() {
    local target="preview"
    local verify_only=false
    local force_update=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--verify)
                verify_only=true
                shift
                ;;
            -f|--force)
                force_update=true
                shift
                ;;
            --template)
                ENV_TEMPLATE="$2"
                shift 2
                ;;
            --local)
                ENV_LOCAL="$2"
                shift 2
                ;;
            preview|production|development)
                target="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log_info "Starting Vercel environment setup for $target environment..."
    
    # Run setup steps
    check_prerequisites
    vercel_auth
    link_project
    
    if [ "$verify_only" = true ]; then
        verify_env_vars "$target"
    else
        read_env_template
        process_env_vars "$target"
        verify_env_vars "$target"
    fi
    
    log_success "Vercel environment setup completed successfully!"
    
    # Show next steps
    echo ""
    log_info "Next steps:"
    echo "1. Verify all environment variables are set correctly"
    echo "2. Update any placeholder values in Vercel dashboard"
    echo "3. Test deployment with: vercel --prod (for production)"
    echo "4. Monitor deployment logs for any configuration issues"
    
    if [ "$target" = "production" ]; then
        echo ""
        log_warning "IMPORTANT: Production environment configured!"
        echo "- Ensure all API keys and secrets are properly set"
        echo "- Verify Supabase configuration is correct"
        echo "- Test thoroughly before going live"
    fi
}

# Run main function with all arguments
main "$@"