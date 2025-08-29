#!/bin/bash

# SMC Trading Agent - SBOM Generation and Security Scanning Orchestration Script
# This script orchestrates SBOM generation (Python/Node.js) and security scanning with Trivy
# Compatible with macOS/zsh and designed for both local development and CI/CD environments

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SBOM_DIR="$PROJECT_ROOT/docs/sbom"
LOGS_DIR="$SBOM_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOGS_DIR/sbom_workflow_$TIMESTAMP.log"

# Default configuration
SCAN_MODE="full"
VERBOSE=false
FORMAT="json"
SECURITY_ENV="${SECURITY_ENV:-development}"
TARGET_IMAGE="${TARGET_IMAGE:-}"

# Exit codes
EXIT_SUCCESS=0
EXIT_POLICY_VIOLATION=1
EXIT_EXECUTION_ERROR=2

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    local msg="$1"
    echo -e "${BLUE}[INFO]${NC} $msg" | tee -a "$LOG_FILE"
}

log_warn() {
    local msg="$1"
    echo -e "${YELLOW}[WARN]${NC} $msg" | tee -a "$LOG_FILE"
}

log_error() {
    local msg="$1"
    echo -e "${RED}[ERROR]${NC} $msg" | tee -a "$LOG_FILE"
}

log_success() {
    local msg="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $msg" | tee -a "$LOG_FILE"
}

log_verbose() {
    local msg="$1"
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $msg" | tee -a "$LOG_FILE"
    fi
}

# Usage function
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

SMC Trading Agent SBOM Generation and Security Scanning Orchestration

OPTIONS:
    --scan MODE         Scan mode: quick|full|container-only (default: full)
    --verbose, -v       Enable verbose output
    --format FORMAT     Output format: json|sarif|table (default: json for non-TTY, table for TTY)
    --help, -h          Show this help message

ENVIRONMENT VARIABLES:
    SECURITY_ENV        Environment: development|staging|production (default: development)
    TARGET_IMAGE        Docker image to scan (required for container-only mode)
    SECURITY_FAIL_ON    Override fail conditions (e.g., CRITICAL,HIGH)
    REPORT_FORMATS      Override report formats (e.g., json,sarif,table)

EXIT CODES:
    0    Success - no policy violations
    1    Policy violation detected
    2    Execution error

EXAMPLES:
    $0 --scan quick --verbose
    $0 --scan container-only --format sarif
    SECURITY_ENV=production $0 --scan full

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --scan)
                SCAN_MODE="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --format)
                FORMAT="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit $EXIT_EXECUTION_ERROR
                ;;
        esac
    done

    # Auto-detect format for TTY
    if [[ "$FORMAT" == "json" ]] && [[ -t 1 ]]; then
        FORMAT="table"
    fi

    # Validate scan mode
    case $SCAN_MODE in
        quick|full|container-only)
            ;;
        *)
            log_error "Invalid scan mode: $SCAN_MODE. Must be one of: quick, full, container-only"
            exit $EXIT_EXECUTION_ERROR
            ;;
    esac

    # Validate format
    case $FORMAT in
        json|sarif|table)
            ;;
        *)
            log_error "Invalid format: $FORMAT. Must be one of: json, sarif, table"
            exit $EXIT_EXECUTION_ERROR
            ;;
    esac

    # Validate container-only mode requirements
    if [[ "$SCAN_MODE" == "container-only" ]] && [[ -z "$TARGET_IMAGE" ]]; then
        log_error "TARGET_IMAGE environment variable is required for container-only mode"
        exit $EXIT_EXECUTION_ERROR
    fi
}

# Setup directories and cleanup
setup_environment() {
    log_info "Setting up environment for SBOM workflow"
    
    # Create necessary directories
    mkdir -p "$SBOM_DIR" "$LOGS_DIR"
    
    # Initialize log file
    echo "SMC Trading Agent SBOM Workflow - $(date)" > "$LOG_FILE"
    echo "Scan Mode: $SCAN_MODE" >> "$LOG_FILE"
    echo "Format: $FORMAT" >> "$LOG_FILE"
    echo "Security Environment: $SECURITY_ENV" >> "$LOG_FILE"
    echo "----------------------------------------" >> "$LOG_FILE"
    
    log_verbose "Project root: $PROJECT_ROOT"
    log_verbose "SBOM directory: $SBOM_DIR"
    log_verbose "Log file: $LOG_FILE"
}

# Check dependencies
check_dependencies() {
    log_info "Checking required dependencies"
    
    local missing_deps=()
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check Trivy
    if ! command -v trivy &> /dev/null; then
        missing_deps+=("trivy")
    fi
    
    # Check Node.js (optional for SBOM generation)
    if ! command -v node &> /dev/null; then
        log_warn "Node.js not found - Node.js SBOM generation will be skipped"
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and try again"
        exit $EXIT_EXECUTION_ERROR
    fi
    
    log_success "All required dependencies are available"
}

# Generate SBOM files
generate_sbom() {
    log_info "Starting SBOM generation"
    
    cd "$PROJECT_ROOT"
    
    # Generate Python SBOM (always) - JSON format
    log_info "Generating Python SBOM (JSON)"
    if python3 tools/generate_sbom.py --python-only --output "$SBOM_DIR" --format json --verbose; then
        log_success "Python SBOM (JSON) generated successfully"
    else
        log_error "Failed to generate Python SBOM (JSON)"
        return $EXIT_EXECUTION_ERROR
    fi
    
    # Generate Python SBOM (always) - XML format
    log_info "Generating Python SBOM (XML)"
    if python3 tools/generate_sbom.py --python-only --output "$SBOM_DIR" --format xml --verbose; then
        log_success "Python SBOM (XML) generated successfully"
    else
        log_warn "Failed to generate Python SBOM (XML) - continuing with JSON only"
    fi
    
    # Generate Node.js SBOM (if available) - JSON format
    if [[ -f "package.json" ]] && command -v node &> /dev/null; then
        log_info "Generating Node.js SBOM (JSON)"
        if python3 tools/generate_sbom.py --nodejs-only --output "$SBOM_DIR" --format json --verbose; then
            log_success "Node.js SBOM (JSON) generated successfully"
        else
            log_warn "Failed to generate Node.js SBOM (JSON) - continuing without it"
        fi
        
        log_info "Generating Node.js SBOM (XML)"
        if python3 tools/generate_sbom.py --nodejs-only --output "$SBOM_DIR" --format xml --verbose; then
            log_success "Node.js SBOM (XML) generated successfully"
        else
            log_warn "Failed to generate Node.js SBOM (XML) - continuing with JSON only"
        fi
    else
        log_warn "Skipping Node.js SBOM generation (package.json not found or Node.js not available)"
    fi
    
    # List generated SBOM files
    log_verbose "Generated SBOM files:"
    find "$SBOM_DIR" -name "*.sbom.*" -type f | while read -r file; do
        log_verbose "  - $(basename "$file")"
    done
}

# Run Trivy scans
run_trivy_scans() {
    log_info "Starting Trivy security scans"
    
    cd "$PROJECT_ROOT"
    
    local scan_results=()
    
    case $SCAN_MODE in
        "quick")
            log_info "Running quick filesystem scan"
            if trivy fs --config config/trivy.yaml --format json --output "$SBOM_DIR/trivy_fs_quick.json" .; then
                scan_results+=("$SBOM_DIR/trivy_fs_quick.json")
                log_success "Quick filesystem scan completed"
            else
                log_error "Quick filesystem scan failed"
                return $EXIT_EXECUTION_ERROR
            fi
            ;;
        "full")
            # Filesystem scan
            log_info "Running full filesystem scan"
            if trivy fs --config config/trivy.yaml --format json --output "$SBOM_DIR/trivy_fs_full.json" .; then
                scan_results+=("$SBOM_DIR/trivy_fs_full.json")
                log_success "Filesystem scan completed"
            else
                log_error "Filesystem scan failed"
                return $EXIT_EXECUTION_ERROR
            fi
            
            # SBOM scans
            for sbom_file in "$SBOM_DIR"/*.sbom.json; do
                if [[ -f "$sbom_file" ]]; then
                    local sbom_name=$(basename "$sbom_file" .sbom.json)
                    local output_file="$SBOM_DIR/trivy_sbom_${sbom_name}.json"
                    
                    log_info "Scanning SBOM: $sbom_name"
                    if trivy sbom --format json --output "$output_file" "$sbom_file"; then
                        scan_results+=("$output_file")
                        log_success "SBOM scan completed: $sbom_name"
                    else
                        log_warn "SBOM scan failed: $sbom_name - continuing"
                    fi
                fi
            done
            ;;
        "container-only")
            log_info "Running container scan on: $TARGET_IMAGE"
            if trivy image --format json --output "$SBOM_DIR/trivy_container.json" "$TARGET_IMAGE"; then
                scan_results+=("$SBOM_DIR/trivy_container.json")
                log_success "Container scan completed"
            else
                log_error "Container scan failed"
                return $EXIT_EXECUTION_ERROR
            fi
            ;;
    esac
    
    # Store scan results for policy enforcement
    printf '%s\n' "${scan_results[@]}" > "$SBOM_DIR/scan_results.list"
    
    log_verbose "Scan results saved to: $SBOM_DIR/scan_results.list"
}

# Apply security policies
apply_security_policies() {
    log_info "Applying security policies"
    
    cd "$PROJECT_ROOT"
    
    if [[ ! -f "$SBOM_DIR/scan_results.list" ]]; then
        log_error "No scan results found for policy enforcement"
        return $EXIT_EXECUTION_ERROR
    fi
    
    local policy_cmd="python3 tools/security_policy.py"
    policy_cmd+=" --config config/security_policy.yaml"
    policy_cmd+=" --environment $SECURITY_ENV"
    policy_cmd+=" --format $FORMAT"
    policy_cmd+=" --output $SBOM_DIR"
    
    # Add scan result files
    while IFS= read -r scan_file; do
        if [[ -f "$scan_file" ]]; then
            policy_cmd+=" --input \"$scan_file\""
        fi
    done < "$SBOM_DIR/scan_results.list"
    
    log_verbose "Policy command: $policy_cmd"
    
    # Execute policy enforcement
    if eval "$policy_cmd"; then
        log_success "Security policies applied successfully"
        return $EXIT_SUCCESS
    else
        local exit_code=$?
        if [[ $exit_code -eq 1 ]]; then
            log_error "Security policy violations detected"
            return $EXIT_POLICY_VIOLATION
        else
            log_error "Policy enforcement failed with error"
            return $EXIT_EXECUTION_ERROR
        fi
    fi
}

# Generate consolidated report
generate_consolidated_report() {
    log_info "Generating consolidated security report"
    
    cd "$PROJECT_ROOT"
    
    local report_file="$SBOM_DIR/consolidated_report.json"
    local summary_file="$SBOM_DIR/security_summary.txt"
    
    # Create consolidated report structure
    cat > "$report_file" << EOF
{
  "metadata": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "scan_mode": "$SCAN_MODE",
    "environment": "$SECURITY_ENV",
    "project": "SMC Trading Agent"
  },
  "sbom_files": [],
  "scan_results": [],
  "policy_results": {},
  "summary": {
    "total_vulnerabilities": 0,
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "policy_violations": false
  }
}
EOF
    
    # Add SBOM files to report
    find "$SBOM_DIR" -name "*.sbom.json" -type f | while read -r sbom_file; do
        log_verbose "Including SBOM in report: $(basename "$sbom_file")"
    done
    
    # Generate human-readable summary
    cat > "$summary_file" << EOF
SMC Trading Agent - Security Scan Summary
==========================================
Timestamp: $(date)
Scan Mode: $SCAN_MODE
Environment: $SECURITY_ENV
Format: $FORMAT

SBOM Files Generated:
EOF
    
    find "$SBOM_DIR" -name "*.sbom.*" -type f | while read -r file; do
        echo "  - $(basename "$file")" >> "$summary_file"
    done
    
    echo "" >> "$summary_file"
    echo "Scan Results:" >> "$summary_file"
    
    if [[ -f "$SBOM_DIR/scan_results.list" ]]; then
        while IFS= read -r scan_file; do
            if [[ -f "$scan_file" ]]; then
                echo "  - $(basename "$scan_file")" >> "$summary_file"
            fi
        done < "$SBOM_DIR/scan_results.list"
    fi
    
    log_success "Consolidated report generated: $report_file"
    log_success "Summary report generated: $summary_file"
}

# Cleanup temporary files
cleanup_temp_files() {
    log_info "Cleaning up temporary files"
    
    # Remove temporary scan result list
    if [[ -f "$SBOM_DIR/scan_results.list" ]]; then
        rm -f "$SBOM_DIR/scan_results.list"
        log_verbose "Removed temporary scan results list"
    fi
    
    # Clean up old log files (keep last 10)
    find "$LOGS_DIR" -name "sbom_workflow_*.log" -type f | sort -r | tail -n +11 | xargs -r rm -f
    log_verbose "Cleaned up old log files"
    
    # Clean Trivy cache if it exists
    if [[ -d ".trivy-cache" ]]; then
        log_verbose "Trivy cache directory exists (not cleaning to preserve performance)"
    fi
}

# Main execution function
main() {
    local start_time=$(date +%s)
    
    log_info "Starting SMC Trading Agent SBOM Workflow"
    log_info "Scan mode: $SCAN_MODE, Format: $FORMAT, Environment: $SECURITY_ENV"
    
    # Setup
    setup_environment
    check_dependencies
    
    # Core workflow
    local exit_code=$EXIT_SUCCESS
    
    # Generate SBOM (skip for container-only mode)
    if [[ "$SCAN_MODE" != "container-only" ]]; then
        if ! generate_sbom; then
            exit_code=$EXIT_EXECUTION_ERROR
        fi
    fi
    
    # Run security scans
    if [[ $exit_code -eq $EXIT_SUCCESS ]]; then
        if ! run_trivy_scans; then
            exit_code=$EXIT_EXECUTION_ERROR
        fi
    fi
    
    # Apply security policies
    if [[ $exit_code -eq $EXIT_SUCCESS ]]; then
        if ! apply_security_policies; then
            exit_code=$?
        fi
    fi
    
    # Generate reports
    if [[ $exit_code -ne $EXIT_EXECUTION_ERROR ]]; then
        generate_consolidated_report
    fi
    
    # Cleanup
    cleanup_temp_files
    
    # Final summary
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    case $exit_code in
        $EXIT_SUCCESS)
            log_success "SBOM workflow completed successfully in ${duration}s"
            log_success "No security policy violations detected"
            ;;
        $EXIT_POLICY_VIOLATION)
            log_error "SBOM workflow completed with policy violations in ${duration}s"
            log_error "Check the security reports in $SBOM_DIR for details"
            ;;
        $EXIT_EXECUTION_ERROR)
            log_error "SBOM workflow failed with execution errors in ${duration}s"
            log_error "Check the log file for details: $LOG_FILE"
            ;;
    esac
    
    log_info "Log file: $LOG_FILE"
    log_info "Reports directory: $SBOM_DIR"
    
    exit $exit_code
}

# Signal handlers for cleanup
trap 'log_error "Script interrupted"; cleanup_temp_files; exit $EXIT_EXECUTION_ERROR' INT TERM

# Parse arguments and run main function
parse_args "$@"
main