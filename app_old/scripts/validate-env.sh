#!/bin/bash
# Environment Variables Validation Script
# This script validates that all required environment variables are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_TEMPLATE=".env.production"
ENV_LOCAL=".env.local"
VALIDATION_REPORT="env-validation-report.json"

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

# Required environment variables with their validation rules
# Using arrays instead of associative arrays for compatibility
REQUIRED_VARS_NAMES=("VITE_SUPABASE_URL" "VITE_SUPABASE_ANON_KEY" "SUPABASE_SERVICE_ROLE_KEY" "SUPABASE_URL" "ENCRYPTION_KEY" "BINANCE_API_KEY" "BINANCE_API_SECRET" "NODE_ENV" "PORT" "LOG_LEVEL")
REQUIRED_VARS_RULES=("url" "key" "key" "url" "encryption_key" "api_key" "api_secret" "enum:development,staging,production" "port" "enum:DEBUG,INFO,WARN,ERROR")

# Optional environment variables
OPTIONAL_VARS_NAMES=("DATABASE_URL" "REDIS_URL" "VAULT_ENABLED" "REDIS_ENABLED" "DEFAULT_RISK_PERCENTAGE" "MAX_CONCURRENT_TRADES" "DEFAULT_STOP_LOSS_PERCENTAGE" "DEFAULT_TAKE_PROFIT_PERCENTAGE" "RATE_LIMIT_WINDOW_MS" "RATE_LIMIT_MAX_REQUESTS")
OPTIONAL_VARS_RULES=("url" "url" "boolean" "boolean" "number" "number" "number" "number" "number" "number")

# Validation results - using simple arrays
VALIDATION_VAR_NAMES=()
VALIDATION_RESULTS=()
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0

# Function to validate URL format
validate_url() {
    local url="$1"
    # Support HTTP/HTTPS, PostgreSQL, Redis, and other common schemes
    if [[ "$url" =~ ^(https?|postgresql|redis)://[a-zA-Z0-9._:-]+@?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(:[0-9]+)?(/.*)?$ ]] || [[ "$url" =~ ^(https?|postgresql|redis)://[a-zA-Z0-9._:-]+@?[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate API key format
validate_api_key() {
    local key="$1"
    # Accept JWT tokens (with dots) and regular API keys
    if [[ ${#key} -ge 16 ]] && [[ "$key" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate encryption key
validate_encryption_key() {
    local key="$1"
    if [[ ${#key} -eq 32 ]] && [[ "$key" =~ ^[a-zA-Z0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate port number
validate_port() {
    local port="$1"
    if [[ "$port" =~ ^[0-9]+$ ]] && [ "$port" -ge 1 ] && [ "$port" -le 65535 ]; then
        return 0
    else
        return 1
    fi
}

# Function to validate number
validate_number() {
    local num="$1"
    if [[ "$num" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate boolean
validate_boolean() {
    local bool="$1"
    if [[ "$bool" =~ ^(true|false|TRUE|FALSE|1|0)$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate enum values
validate_enum() {
    local value="$1"
    local allowed="$2"
    IFS=',' read -ra ALLOWED_VALUES <<< "$allowed"
    for allowed_value in "${ALLOWED_VALUES[@]}"; do
        if [[ "$value" == "$allowed_value" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to validate a single environment variable
validate_env_var() {
    local var_name="$1"
    local validation_rule="$2"
    local var_value="${!var_name}"
    local is_required="$3"
    
    # Store validation result
    VALIDATION_VAR_NAMES+=("$var_name")
    
    # Check if variable is set
    if [[ -z "$var_value" ]]; then
        if [[ "$is_required" == "true" ]]; then
            VALIDATION_RESULTS+=("ERROR: Required variable not set")
            ((VALIDATION_ERRORS++))
            return 1
        else
            VALIDATION_RESULTS+=("WARNING: Optional variable not set")
            ((VALIDATION_WARNINGS++))
            return 0
        fi
    fi
    
    # Check for placeholder values
    if [[ "$var_value" =~ ^your_.*$ ]] || [[ "$var_value" =~ your-project ]] || [[ "$var_value" =~ ^\$\{.*\}$ ]] || [[ "$var_value" =~ your_.*_key$ ]]; then
        VALIDATION_RESULTS+=("ERROR: Placeholder value detected")
        ((VALIDATION_ERRORS++))
        return 1
    fi
    
    # Validate based on rule
    case "$validation_rule" in
        "url")
            if validate_url "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid URL")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid URL format")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        "key")
            if validate_api_key "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid API key format")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid API key format (min 16 chars, alphanumeric)")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        "api_key")
            if validate_api_key "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid API key format")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid API key format")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        "api_secret")
            if validate_api_key "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid API secret format")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid API secret format")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        "encryption_key")
            if validate_encryption_key "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid encryption key (32 chars)")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid encryption key (must be 32 alphanumeric chars)")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        "port")
            if validate_port "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid port number")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid port number (1-65535)")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        "number")
            if validate_number "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid number")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid number format")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        "boolean")
            if validate_boolean "$var_value"; then
                VALIDATION_RESULTS+=("OK: Valid boolean")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid boolean (use true/false)")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        enum:*)
            local allowed_values="${validation_rule#enum:}"
            if validate_enum "$var_value" "$allowed_values"; then
                VALIDATION_RESULTS+=("OK: Valid enum value")
            else
                VALIDATION_RESULTS+=("ERROR: Invalid enum value (allowed: $allowed_values)")
                ((VALIDATION_ERRORS++))
                return 1
            fi
            ;;
        *)
            VALIDATION_RESULTS+=("OK: No specific validation")
            ;;
    esac
    
    return 0
}

# Function to load environment variables from file
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
                if [[ "$var_value" =~ ^["'](.*)['"]$ ]]; then
                    var_value="${BASH_REMATCH[1]}"
                fi
                
                # Export the variable
                export "$var_name"="$var_value"
            fi
        done < "$env_file"
        
        set +a
    else
        log_warning "Environment file $env_file not found"
    fi
}

# Function to validate all environment variables
validate_all_vars() {
    log_info "Validating required environment variables..."
    
    # Validate required variables
    for i in "${!REQUIRED_VARS_NAMES[@]}"; do
        # Disable exit on error for validation to continue even if individual variables fail
        set +e
        validate_env_var "${REQUIRED_VARS_NAMES[$i]}" "${REQUIRED_VARS_RULES[$i]}" "true"
        set -e
    done
    
    log_info "Validating optional environment variables..."
    
    # Validate optional variables
    for i in "${!OPTIONAL_VARS_NAMES[@]}"; do
        # Disable exit on error for validation to continue even if individual variables fail
        set +e
        validate_env_var "${OPTIONAL_VARS_NAMES[$i]}" "${OPTIONAL_VARS_RULES[$i]}" "false"
        set -e
    done
}

# Function to generate validation report
generate_report() {
    local output_format="$1"
    
    if [[ "$output_format" == "json" ]]; then
        # Generate JSON report
        cat > "$VALIDATION_REPORT" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "validation_summary": {
    "total_variables": $((${#REQUIRED_VARS_NAMES[@]} + ${#OPTIONAL_VARS_NAMES[@]})),
    "required_variables": ${#REQUIRED_VARS_NAMES[@]},
    "optional_variables": ${#OPTIONAL_VARS_NAMES[@]},
    "errors": $VALIDATION_ERRORS,
    "warnings": $VALIDATION_WARNINGS,
    "status": "$([ $VALIDATION_ERRORS -eq 0 ] && echo "PASS" || echo "FAIL")"
  },
  "results": {
EOF
        
        local first=true
        for i in "${!VALIDATION_VAR_NAMES[@]}"; do
            if [[ "$first" == "true" ]]; then
                first=false
            else
                echo "," >> "$VALIDATION_REPORT"
            fi
            echo "    \"${VALIDATION_VAR_NAMES[$i]}\": \"${VALIDATION_RESULTS[$i]}\"" >> "$VALIDATION_REPORT"
        done
        
        cat >> "$VALIDATION_REPORT" << EOF

  }
}
EOF
        
        log_info "JSON validation report saved to $VALIDATION_REPORT"
    fi
}

# Function to print validation results
print_results() {
    echo ""
    log_info "Environment Variables Validation Results:"
    echo "========================================="
    
    # Print results by category
    echo ""
    log_info "Required Variables:"
    for i in "${!REQUIRED_VARS_NAMES[@]}"; do
        local var_name="${REQUIRED_VARS_NAMES[$i]}"
        # Find result for this variable
        for j in "${!VALIDATION_VAR_NAMES[@]}"; do
            if [[ "${VALIDATION_VAR_NAMES[$j]}" == "$var_name" ]]; then
                local result="${VALIDATION_RESULTS[$j]}"
                if [[ "$result" =~ ^OK:.* ]]; then
                    log_success "✓ $var_name: $result"
                elif [[ "$result" =~ ^WARNING:.* ]]; then
                    log_warning "⚠ $var_name: $result"
                else
                    log_error "✗ $var_name: $result"
                fi
                break
            fi
        done
    done
    
    echo ""
    log_info "Optional Variables:"
    for i in "${!OPTIONAL_VARS_NAMES[@]}"; do
        local var_name="${OPTIONAL_VARS_NAMES[$i]}"
        # Find result for this variable
        for j in "${!VALIDATION_VAR_NAMES[@]}"; do
            if [[ "${VALIDATION_VAR_NAMES[$j]}" == "$var_name" ]]; then
                local result="${VALIDATION_RESULTS[$j]}"
                if [[ "$result" =~ ^OK:.* ]]; then
                    log_success "✓ $var_name: $result"
                elif [[ "$result" =~ ^WARNING:.* ]]; then
                    log_warning "⚠ $var_name: $result"
                else
                    log_error "✗ $var_name: $result"
                fi
                break
            fi
        done
    done
    
    # Print summary
    echo ""
    log_info "Validation Summary:"
    echo "=================="
    log_info "Total Variables: $((${#REQUIRED_VARS_NAMES[@]} + ${#OPTIONAL_VARS_NAMES[@]}))"
    log_info "Required Variables: ${#REQUIRED_VARS_NAMES[@]}"
    log_info "Optional Variables: ${#OPTIONAL_VARS_NAMES[@]}"
    
    if [[ $VALIDATION_ERRORS -eq 0 ]]; then
        log_success "✓ Errors: $VALIDATION_ERRORS"
    else
        log_error "✗ Errors: $VALIDATION_ERRORS"
    fi
    
    if [[ $VALIDATION_WARNINGS -eq 0 ]]; then
        log_success "✓ Warnings: $VALIDATION_WARNINGS"
    else
        log_warning "⚠ Warnings: $VALIDATION_WARNINGS"
    fi
    
    echo ""
    if [[ $VALIDATION_ERRORS -eq 0 ]]; then
        log_success "🎉 Environment validation PASSED!"
        echo "All required environment variables are properly configured."
    else
        log_error "❌ Environment validation FAILED!"
        echo "Please fix the errors above before proceeding with deployment."
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Validate environment variables for deployment"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -f, --file FILE     Use specific environment file [default: .env.local or .env.production]"
    echo "  -j, --json          Generate JSON report"
    echo "  -q, --quiet         Quiet mode (only show summary)"
    echo "  --template FILE     Use custom template file [default: .env.production]"
    echo ""
    echo "Examples:"
    echo "  $0                      # Validate using .env.local or .env.production"
    echo "  $0 -f .env.staging      # Validate specific environment file"
    echo "  $0 --json               # Generate JSON validation report"
}

# Main function
main() {
    local env_file=""
    local generate_json=false
    local quiet_mode=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--file)
                env_file="$2"
                shift 2
                ;;
            -j|--json)
                generate_json=true
                shift
                ;;
            -q|--quiet)
                quiet_mode=true
                shift
                ;;
            --template)
                ENV_TEMPLATE="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log_info "Starting environment variables validation..."
    
    # Determine which environment file to use
    if [[ -n "$env_file" ]]; then
        load_env_file "$env_file"
    elif [[ -f "$ENV_LOCAL" ]]; then
        load_env_file "$ENV_LOCAL"
    elif [[ -f "$ENV_TEMPLATE" ]]; then
        load_env_file "$ENV_TEMPLATE"
    else
        log_warning "No environment file found, using system environment variables"
    fi
    
    # Run validation
    validate_all_vars
    
    # Generate reports
    if [[ "$generate_json" == "true" ]]; then
        generate_report "json"
    fi
    
    # Print results
    if [[ "$quiet_mode" != "true" ]]; then
        print_results
    else
        # Just print summary in quiet mode
        if [[ $VALIDATION_ERRORS -eq 0 ]]; then
            log_success "Environment validation PASSED (Errors: $VALIDATION_ERRORS, Warnings: $VALIDATION_WARNINGS)"
        else
            log_error "Environment validation FAILED (Errors: $VALIDATION_ERRORS, Warnings: $VALIDATION_WARNINGS)"
        fi
    fi
    
    # Exit with appropriate code
    exit $VALIDATION_ERRORS
}

# Run main function with all arguments only if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi