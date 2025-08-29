#!/usr/bin/env python3
"""
Security Policy Enforcement Test Script

This script tests the security policy enforcement functionality,
validates vulnerability scanning results, and ensures compliance
with defined security standards.
"""

import os
import sys
import json
import logging
import argparse
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Add tools directory to path for imports
sys.path.append(str(Path(__file__).parent))

from security_policy import SecurityPolicy
from scan_vulnerabilities import VulnerabilityScanner
from generate_sbom import SBOMGenerator

@dataclass
class TestResult:
    """Represents a test result with status and details."""
    name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None

class SecurityTestRunner:
    """Main class for running security policy tests."""
    
    def __init__(self, project_root: Path, config_dir: Path = None):
        self.project_root = project_root
        self.config_dir = config_dir or project_root / "config"
        self.test_results: List[TestResult] = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        try:
            self.security_policy = SecurityPolicy(
                config_file=self.config_dir / "security_policy.yaml"
            )
            self.logger.info("Security policy loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load security policy: {e}")
            self.security_policy = None
    
    def test_security_policy_loading(self) -> TestResult:
        """Test if security policy configuration loads correctly."""
        try:
            if self.security_policy is None:
                return TestResult(
                    "security_policy_loading",
                    False,
                    "Security policy failed to load"
                )
            
            # Test basic policy access
            severity_levels = self.security_policy.get_severity_thresholds()
            build_fail_severities = self.security_policy.get_build_fail_severities()
            
            return TestResult(
                "security_policy_loading",
                True,
                f"Security policy loaded with {len(severity_levels)} severity levels",
                {
                    "severity_levels": severity_levels,
                    "build_fail_severities": build_fail_severities
                }
            )
        except Exception as e:
            return TestResult(
                "security_policy_loading",
                False,
                f"Security policy test failed: {str(e)}"
            )
    
    def test_sbom_generation(self) -> TestResult:
        """Test SBOM generation functionality."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                sbom_generator = SBOMGenerator(
                    project_root=self.project_root,
                    output_dir=temp_path
                )
                
                # Test Python SBOM generation
                python_sbom = sbom_generator.generate_python_sbom(temp_path)
                
                if python_sbom and python_sbom.exists():
                    # Validate SBOM content
                    with open(python_sbom, 'r') as f:
                        sbom_data = json.load(f)
                    
                    required_fields = ['bomFormat', 'specVersion', 'components']
                    missing_fields = [field for field in required_fields if field not in sbom_data]
                    
                    if missing_fields:
                        return TestResult(
                            "sbom_generation",
                            False,
                            f"SBOM missing required fields: {missing_fields}"
                        )
                    
                    return TestResult(
                        "sbom_generation",
                        True,
                        f"SBOM generated successfully with {len(sbom_data.get('components', []))} components",
                        {
                            "sbom_path": str(python_sbom),
                            "component_count": len(sbom_data.get('components', []))
                        }
                    )
                else:
                    return TestResult(
                        "sbom_generation",
                        False,
                        "Failed to generate Python SBOM"
                    )
        except Exception as e:
            return TestResult(
                "sbom_generation",
                False,
                f"SBOM generation test failed: {str(e)}"
            )
    
    def test_vulnerability_scanning(self) -> TestResult:
        """Test vulnerability scanning functionality."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                scanner = VulnerabilityScanner(
                    project_root=self.project_root,
                    output_dir=temp_path,
                    config_file=self.config_dir / "trivy.yaml"
                )
                
                # Test filesystem scanning
                scan_result = scanner.scan_filesystem()
                
                if scan_result and scan_result.exists():
                    with open(scan_result, 'r') as f:
                        scan_data = json.load(f)
                    
                    return TestResult(
                        "vulnerability_scanning",
                        True,
                        f"Vulnerability scan completed successfully",
                        {
                            "scan_path": str(scan_result),
                            "results_count": len(scan_data.get('Results', []))
                        }
                    )
                else:
                    return TestResult(
                        "vulnerability_scanning",
                        False,
                        "Vulnerability scan failed to produce results"
                    )
        except Exception as e:
            return TestResult(
                "vulnerability_scanning",
                False,
                f"Vulnerability scanning test failed: {str(e)}"
            )
    
    def test_policy_enforcement(self) -> TestResult:
        """Test security policy enforcement with sample vulnerabilities."""
        try:
            if self.security_policy is None:
                return TestResult(
                    "policy_enforcement",
                    False,
                    "Security policy not available for testing"
                )
            
            # Create sample vulnerability data for testing
            sample_vulnerabilities = [
                {
                    "VulnerabilityID": "CVE-2023-0001",
                    "Severity": "CRITICAL",
                    "PkgName": "test-package",
                    "Title": "Critical vulnerability for testing"
                },
                {
                    "VulnerabilityID": "CVE-2023-0002",
                    "Severity": "HIGH",
                    "PkgName": "another-package",
                    "Title": "High severity vulnerability for testing"
                },
                {
                    "VulnerabilityID": "CVE-2023-0003",
                    "Severity": "MEDIUM",
                    "PkgName": "third-package",
                    "Title": "Medium severity vulnerability for testing"
                }
            ]
            
            # Test policy enforcement
            policy_result = self.security_policy.enforce_policy(sample_vulnerabilities)
            should_fail_build = self.security_policy.should_fail_build(sample_vulnerabilities)
            
            return TestResult(
                "policy_enforcement",
                True,
                f"Policy enforcement working correctly. Build should {'fail' if should_fail_build else 'pass'}",
                {
                    "should_fail_build": should_fail_build,
                    "policy_result": policy_result
                }
            )
        except Exception as e:
            return TestResult(
                "policy_enforcement",
                False,
                f"Policy enforcement test failed: {str(e)}"
            )
    
    def test_configuration_files(self) -> TestResult:
        """Test if all required configuration files exist and are valid."""
        try:
            required_files = [
                self.config_dir / "security_policy.yaml",
                self.config_dir / "trivy.yaml"
            ]
            
            missing_files = []
            invalid_files = []
            
            for config_file in required_files:
                if not config_file.exists():
                    missing_files.append(str(config_file))
                else:
                    # Try to parse the file
                    try:
                        import yaml
                        with open(config_file, 'r') as f:
                            yaml.safe_load(f)
                    except Exception as e:
                        invalid_files.append(f"{config_file}: {str(e)}")
            
            if missing_files or invalid_files:
                error_msg = ""
                if missing_files:
                    error_msg += f"Missing files: {missing_files}. "
                if invalid_files:
                    error_msg += f"Invalid files: {invalid_files}."
                
                return TestResult(
                    "configuration_files",
                    False,
                    error_msg.strip()
                )
            
            return TestResult(
                "configuration_files",
                True,
                f"All {len(required_files)} configuration files are valid"
            )
        except Exception as e:
            return TestResult(
                "configuration_files",
                False,
                f"Configuration files test failed: {str(e)}"
            )
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests and return results."""
        self.logger.info("Starting security policy tests...")
        
        # List of all tests to run
        tests = [
            self.test_configuration_files,
            self.test_security_policy_loading,
            self.test_sbom_generation,
            self.test_vulnerability_scanning,
            self.test_policy_enforcement
        ]
        
        # Run each test
        for test_func in tests:
            try:
                result = test_func()
                self.test_results.append(result)
                
                status = "PASS" if result.passed else "FAIL"
                self.logger.info(f"{status}: {result.name} - {result.message}")
                
                if result.details:
                    self.logger.debug(f"Details: {result.details}")
                    
            except Exception as e:
                self.logger.error(f"Test {test_func.__name__} crashed: {str(e)}")
                self.test_results.append(TestResult(
                    test_func.__name__,
                    False,
                    f"Test crashed: {str(e)}"
                ))
        
        # Generate summary
        passed_tests = [r for r in self.test_results if r.passed]
        failed_tests = [r for r in self.test_results if not r.passed]
        
        summary = {
            "total_tests": len(self.test_results),
            "passed": len(passed_tests),
            "failed": len(failed_tests),
            "success_rate": len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                } for r in self.test_results
            ]
        }
        
        self.logger.info(f"Test Summary: {len(passed_tests)}/{len(self.test_results)} tests passed "
                        f"({summary['success_rate']:.1f}%)")
        
        return summary
    
    def generate_report(self, output_file: Path = None) -> Path:
        """Generate a detailed test report."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.project_root / "docs" / "sbom" / f"security_test_report_{timestamp}.json"
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Run tests if not already run
        if not self.test_results:
            self.run_all_tests()
        
        # Generate report data
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed": len([r for r in self.test_results if r.passed]),
                "failed": len([r for r in self.test_results if not r.passed])
            },
            "test_results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                } for r in self.test_results
            ]
        }
        
        # Write report
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"Test report written to: {output_file}")
        return output_file

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Security Policy Enforcement Testing")
    parser.add_argument("--project-root", type=Path, default=Path("."),
                       help="Project root directory")
    parser.add_argument("--config-dir", type=Path,
                       help="Configuration directory (default: PROJECT_ROOT/config)")
    parser.add_argument("--output", type=Path,
                       help="Output file for test report")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize test runner
    test_runner = SecurityTestRunner(
        project_root=args.project_root,
        config_dir=args.config_dir
    )
    
    try:
        # Run tests
        summary = test_runner.run_all_tests()
        
        # Generate report
        report_file = test_runner.generate_report(args.output)
        
        # Exit with appropriate code
        if summary["failed"] > 0:
            print(f"Tests failed: {summary['failed']}/{summary['total_tests']}")
            sys.exit(1)
        else:
            print(f"All tests passed: {summary['passed']}/{summary['total_tests']}")
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Security testing failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()