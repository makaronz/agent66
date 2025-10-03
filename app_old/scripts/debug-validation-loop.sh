#!/bin/bash

# Debug validation loop with detailed logging
set -e

echo "=== DEBUGGING VALIDATION LOOP ==="

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
load_env_file() {
    local env_file="$1"
    
    if [[ -f "$env_file" ]]; then
        log_info "Loading environment variables from $env_file"
        set -a
        
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            
            if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                local var_name="${BASH_REMATCH[1]}"
                local var_value="${BASH_REMATCH[2]}"
                
                if [[ "$var_value" =~ ^["'](.*)['"]$ ]]; then
                    var_value="${BASH_REMATCH[1]}"
                fi
                
                export "$var_name"="$var_value"
            fi
        done < "$env_file"
        
        set +a
    fi
}

# Initialize validation arrays
VALIDATION_VAR_NAMES=()
VALIDATION_RESULTS=()
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0

# Load .env.production
load_env_file ".env.production"

# Required variables and rules
REQUIRED_VARS_NAMES=("VITE_SUPABASE_URL" "VITE_SUPABASE_ANON_KEY" "SUPABASE_SERVICE_ROLE_KEY")
REQUIRED_VARS_RULES=("url" "api_key" "api_key")

# Simplified validate_env_var function with debug
validate_env_var() {
    local var_name="$1"
    local validation_rule="$2"
    local var_value="${!var_name}"
    local is_required="$3"
    
    echo "🔍 DEBUG: Starting validation for $var_name"
    echo "   Value: '$var_value'"
    echo "   Rule: $validation_rule"
    echo "   Required: $is_required"
    
    # Add to validation arrays
    VALIDATION_VAR_NAMES+=("$var_name")
    echo "   Added to VALIDATION_VAR_NAMES (count: ${#VALIDATION_VAR_NAMES[@]})"
    
    # Check if variable is set
    if [[ -z "$var_value" ]]; then
        echo "   Variable is empty"
        if [[ "$is_required" == "true" ]]; then
            VALIDATION_RESULTS+=("ERROR: Required variable not set")
            ((VALIDATION_ERRORS++))
            echo "   Result: ERROR - Required variable not set"
            return 1
        else
            VALIDATION_RESULTS+=("WARNING: Optional variable not set")
            ((VALIDATION_WARNINGS++))
            echo "   Result: WARNING - Optional variable not set"
            return 0
        fi
    fi
    
    echo "   Checking for placeholder values..."
    # Check for placeholder values
    if [[ "$var_value" =~ ^your_.* ]] || [[ "$var_value" =~ your-project ]] || [[ "$var_value" =~ ^\$\{.*\}$ ]] || [[ "$var_value" =~ your_.*_key$ ]]; then
        echo "   Placeholder detected!"
        VALIDATION_RESULTS+=("ERROR: Placeholder value detected")
        ((VALIDATION_ERRORS++))
        echo "   Result: ERROR - Placeholder value detected"
        return 1
    fi
    
    echo "   No placeholder detected, validation passed"
    VALIDATION_RESULTS+=("OK: Variable validated")
    echo "   Result: OK - Variable validated"
    echo "🔍 DEBUG: Finished validation for $var_name"
    echo ""
    
    return 0
}

# Test validation loop
log_info "Starting validation loop..."

for i in "${!REQUIRED_VARS_NAMES[@]}"; do
    var_name="${REQUIRED_VARS_NAMES[$i]}"
    validation_rule="${REQUIRED_VARS_RULES[$i]}"
    
    echo "📋 Processing variable $((i+1))/${#REQUIRED_VARS_NAMES[@]}: $var_name"
    
    validate_env_var "$var_name" "$validation_rule" "true"
    
    echo "📋 Completed variable $((i+1))/${#REQUIRED_VARS_NAMES[@]}: $var_name"
    echo "Current errors: $VALIDATION_ERRORS, warnings: $VALIDATION_WARNINGS"
    echo "----------------------------------------"
done

log_info "Validation loop completed!"
echo "Final results:"
echo "Errors: $VALIDATION_ERRORS"
echo "Warnings: $VALIDATION_WARNINGS"
echo "Variables processed: ${#VALIDATION_VAR_NAMES[@]}"
echo "Results recorded: ${#VALIDATION_RESULTS[@]}"