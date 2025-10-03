#!/bin/bash

# Test load_env_file function
set -e

echo "=== TESTING LOAD_ENV_FILE ==="

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test load_env_file function
load_env_file() {
    local env_file="$1"
    
    if [[ -f "$env_file" ]]; then
        log_info "Loading environment variables from $env_file"
        set -a  # automatically export all variables
        
        # Read file line by line and export variables safely
        while IFS= read -r line || [[ -n "$line" ]]; do
            echo "Processing line: $line"
            
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            
            # Check if line contains variable assignment
            if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                local var_name="${BASH_REMATCH[1]}"
                local var_value="${BASH_REMATCH[2]}"
                
                echo "  Found variable: $var_name = $var_value"
                
                # Remove quotes if present
                if [[ "$var_value" =~ ^["'](.*)['"]\$ ]]; then
                    echo "  Removing quotes from: $var_value"
                    var_value="${BASH_REMATCH[1]}"
                    echo "  New value: $var_value"
                fi
                
                # Export the variable
                export "$var_name"="$var_value"
                echo "  Exported: $var_name"
            fi
        done < "$env_file"
        
        set +a
    else
        log_warning "Environment file $env_file not found"
    fi
}

# Test with .env.production
load_env_file ".env.production"

echo "=== TESTING COMPLETE ==="
echo "VITE_SUPABASE_URL: ${VITE_SUPABASE_URL}"
echo "NODE_ENV: ${NODE_ENV}"