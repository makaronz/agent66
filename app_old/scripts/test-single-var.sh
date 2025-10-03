#!/bin/bash

# Test single variable validation
set -e

echo "=== TESTING SINGLE VARIABLE VALIDATION ==="

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

# Test arrays
REQUIRED_VARS_NAMES=("VITE_SUPABASE_URL" "NODE_ENV")
REQUIRED_VARS_RULES=("url" "enum:development,staging,production")

echo "Array length: ${#REQUIRED_VARS_NAMES[@]}"
echo "First variable: ${REQUIRED_VARS_NAMES[0]}"
echo "Second variable: ${REQUIRED_VARS_NAMES[1]}"

# Test simple loop
log_info "Testing simple loop..."
for i in "${!REQUIRED_VARS_NAMES[@]}"; do
    echo "Index: $i"
    echo "Variable: ${REQUIRED_VARS_NAMES[$i]}"
    echo "Rule: ${REQUIRED_VARS_RULES[$i]}"
    echo "---"
done

log_info "Loop completed successfully"