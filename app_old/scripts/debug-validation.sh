#!/bin/bash

# Debug version of validation script
set -e

echo "=== DEBUG VALIDATION START ==="

# Load environment variables
if [[ -f ".env.production" ]]; then
    echo "Loading .env.production..."
    set -a
    source .env.production
    set +a
else
    echo "ERROR: .env.production not found"
    exit 1
fi

# Test variables one by one
REQUIRED_VARS=("VITE_SUPABASE_URL" "NODE_ENV")

echo "Testing individual variables:"
for var_name in "${REQUIRED_VARS[@]}"; do
    echo "Checking $var_name..."
    var_value="${!var_name}"
    echo "  Value: $var_value"
    
    if [[ -z "$var_value" ]]; then
        echo "  Status: EMPTY"
    elif [[ "$var_value" =~ your-project ]]; then
        echo "  Status: PLACEHOLDER"
    else
        echo "  Status: OK"
    fi
    echo "  ---"
done

echo "=== DEBUG VALIDATION END ==="