#!/bin/bash

# Simple test validation script
set -e

# Test arrays
REQUIRED_VARS_NAMES=("VITE_SUPABASE_URL" "NODE_ENV")
REQUIRED_VARS_RULES=("url" "enum:development,staging,production")

# Test variables
VALIDATION_VAR_NAMES=()
VALIDATION_RESULTS=()
VALIDATION_ERRORS=0

echo "Starting simple validation test..."

# Load environment variables
if [[ -f ".env.production" ]]; then
    echo "Loading .env.production..."
    set -a
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            var_name="${BASH_REMATCH[1]}"
            var_value="${BASH_REMATCH[2]}"
            if [[ "$var_value" =~ ^["'](.*)['"]\$ ]]; then
                var_value="${BASH_REMATCH[1]}"
            fi
            export "$var_name"="$var_value"
        fi
    done < ".env.production"
    set +a
fi

echo "Testing validation loop..."
for i in "${!REQUIRED_VARS_NAMES[@]}"; do
    var_name="${REQUIRED_VARS_NAMES[$i]}"
    var_rule="${REQUIRED_VARS_RULES[$i]}"
    var_value="${!var_name}"
    
    echo "Validating $var_name (rule: $var_rule, value: $var_value)"
    
    VALIDATION_VAR_NAMES+=("$var_name")
    
    if [[ -z "$var_value" ]]; then
        VALIDATION_RESULTS+=("ERROR: Variable not set")
        ((VALIDATION_ERRORS++))
    elif [[ "$var_value" =~ ^your_.*$ ]] || [[ "$var_value" =~ your-project ]] || [[ "$var_value" =~ ^\$\{.*\}$ ]]; then
        VALIDATION_RESULTS+=("ERROR: Placeholder value")
        ((VALIDATION_ERRORS++))
    else
        VALIDATION_RESULTS+=("OK: Variable set")
    fi
    
    # Get last element of array (compatible with older bash versions)
    last_index=$((${#VALIDATION_RESULTS[@]} - 1))
    echo "  Result: ${VALIDATION_RESULTS[$last_index]}"
done

echo "Validation complete. Errors: $VALIDATION_ERRORS"
exit $VALIDATION_ERRORS