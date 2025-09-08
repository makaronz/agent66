#!/bin/bash

# Test validate_env_var function
set -e

echo "=== TESTING VALIDATE_ENV_VAR FUNCTION ==="

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

# Load environment variables
if [[ -f ".env.production" ]]; then
    log_info "Loading .env.production"
    set -a
    source .env.production
    set +a
fi

# Initialize validation arrays
VALIDATION_VAR_NAMES=()
VALIDATION_RESULTS=()
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0

# Simple URL validation function
validate_url() {
    local url="$1"
    echo "Validating URL: $url"
    
    # Basic URL validation
    if [[ "$url" =~ ^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$ ]]; then
        echo "URL is valid"
        return 0
    else
        echo "URL is invalid"
        return 1
    fi
}

# Simplified validate_env_var function
validate_env_var() {
    local var_name="$1"
    local validation_rule="$2"
    local var_value="${!var_name}"
    local is_required="$3"
    
    echo "Validating: $var_name = '$var_value' (rule: $validation_rule, required: $is_required)"
    
    # Store validation result
    VALIDATION_VAR_NAMES+=("$var_name")
    
    # Check if variable is set
    if [[ -z "$var_value" ]]; then
        if [[ "$is_required" == "true" ]]; then
            VALIDATION_RESULTS+=("ERROR: Required variable not set")
            ((VALIDATION_ERRORS++))
            echo "Result: ERROR - Required variable not set"
            return 1
        else
            VALIDATION_RESULTS+=("WARNING: Optional variable not set")
            ((VALIDATION_WARNINGS++))
            echo "Result: WARNING - Optional variable not set"
            return 0
        fi
    fi
    
    # Check for placeholder values
    if [[ "$var_value" =~ ^your_.*$ ]] || [[ "$var_value" =~ your-project ]] || [[ "$var_value" =~ ^\$\{.*\}$ ]] || [[ "$var_value" =~ your_.*_key$ ]]; then
        VALIDATION_RESULTS+=("ERROR: Placeholder value detected")
        ((VALIDATION_ERRORS++))
        echo "Result: ERROR - Placeholder value detected"
        return 1
    fi
    
    # Validate based on rule
    case "$validation_rule" in
        "url")
            if validate_url "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid URL")
                echo "Result: OK - Valid URL"
            else
                VALIDATION_RESULTS+=("ERROR: Invalid URL format")
                ((VALIDATION_ERRORS++))
                echo "Result: ERROR - Invalid URL format"
                return 1
            fi
            ;;
        *)
            VALIDATION_RESULTS+=("OK: No specific validation")
            echo "Result: OK - No specific validation"
            ;;
    esac
    
    return 0
}

# Test with VITE_SUPABASE_URL
log_info "Testing VITE_SUPABASE_URL validation..."
validate_env_var "VITE_SUPABASE_URL" "url" "true"

echo ""
log_info "Validation completed"
echo "Errors: $VALIDATION_ERRORS"
echo "Warnings: $VALIDATION_WARNINGS"