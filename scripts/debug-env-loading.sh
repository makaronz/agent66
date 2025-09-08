#!/bin/bash

# Debug environment loading
set -e

echo "=== DEBUGGING ENVIRONMENT LOADING ==="

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

# Load environment variables using the same method as validate-env.sh
load_env_file() {
    local env_file="$1"
    
    if [[ -f "$env_file" ]]; then
        log_info "Loading environment variables from $env_file"
        set -a  # automatically export all variables
        
        # Read file line by line and export variables safely
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            
            # Check if line contains variable assignment
            if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                local var_name="${BASH_REMATCH[1]}"
                local var_value="${BASH_REMATCH[2]}"
                
                # Remove quotes if present
                if [[ "$var_value" =~ ^["'](.*)['"]\$ ]]; then
                    var_value="${BASH_REMATCH[1]}"
                fi
                
                # Export the variable
                export "$var_name"="$var_value"
                echo "Loaded: $var_name = $var_value"
            fi
        done < "$env_file"
        
        set +a
    else
        echo "Environment file $env_file not found"
    fi
}

# Load .env.production
load_env_file ".env.production"

echo ""
log_info "Checking required variables:"

# Required variables
REQUIRED_VARS_NAMES=("VITE_SUPABASE_URL" "VITE_SUPABASE_ANON_KEY" "SUPABASE_SERVICE_ROLE_KEY" "SUPABASE_URL" "ENCRYPTION_KEY" "BINANCE_API_KEY" "BINANCE_API_SECRET" "NODE_ENV" "PORT" "LOG_LEVEL")

for var_name in "${REQUIRED_VARS_NAMES[@]}"; do
    var_value="${!var_name}"
    if [[ -z "$var_value" ]]; then
        echo "❌ $var_name: NOT SET"
    else
        echo "✅ $var_name: '$var_value'"
    fi
done

echo ""
log_info "Testing first variable validation..."

# Test just the first variable
var_name="VITE_SUPABASE_URL"
var_value="${!var_name}"

echo "Variable: $var_name"
echo "Value: '$var_value'"
echo "Is empty: $([ -z "$var_value" ] && echo "YES" || echo "NO")"
echo "Contains placeholder: $([ "$var_value" =~ your-project ] && echo "YES" || echo "NO")"