#!/usr/bin/env python3
"""
Security Policy Enforcement Tool for SMC Trading Agent
Applies security policies to Trivy scan results with support for allowlists,
thresholds, and environment-specific configurations.
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml


@dataclass
class Policy:
    fail_on_severity: str
    warn_on_severities: List[str]
    thresholds: Dict[str, int]
    allowlist_cves: List[str]
    allowlist_packages: List[str]


class SecurityPolicy:
    def __init__(self, policy_path: str = "config/security_policy.yaml", environment: str = "development"):
        with open(policy_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        env = raw.get("environments", {}).get(environment, {})
        root = raw.get("policy", {})

        self.policy = Policy(
            fail_on_severity=env.get("fail_on", {}).get("severity", root.get("fail_on", {}).get("severity", "CRITICAL")),
            warn_on_severities=env.get("warn_on", {}).get("severities", root.get("warn_on", {}).get("severities", ["HIGH"])),
            thresholds=root.get("thresholds", {"max_high": 0, "max_medium": 0}),
            allowlist_cves=root.get("allowlist", {}).get("cves", []),
            allowlist_packages=root.get("allowlist", {}).get("packages", []),
        )

    def is_allowed(self, vuln: Dict[str, Any]) -> bool:
        if vuln.get("VulnerabilityID") in self.policy.allowlist_cves:
            return True
        pkg_name = (vuln.get("PkgName") or vuln.get("PackageName") or "").lower()
        if pkg_name in {p.lower() for p in self.policy.allowlist_packages}:
            return True
        return False

    def severity_order(self, sev: str) -> int:
        order = ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        try:
            return order.index((sev or "UNKNOWN").upper())
        except ValueError:
            return 0

    def should_fail(self, aggregated: Dict[str, int]) -> bool:
        # Fail if any severity >= fail_on_severity exists
        threshold_idx = self.severity_order(self.policy.fail_on_severity)
        for sev, count in aggregated.items():
            if count > 0 and self.severity_order(sev) >= threshold_idx:
                return True
        # Check thresholds
        if aggregated.get("HIGH", 0) > self.policy.thresholds.get("max_high", 0):
            return True
        if aggregated.get("MEDIUM", 0) > self.policy.thresholds.get("max_medium", 0):
            return True
        return False

    def summarize(self, vulns: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        for v in vulns:
            if self.is_allowed(v):
                continue
            summary[v.get("Severity", "UNKNOWN").upper()] = summary.get(v.get("Severity", "UNKNOWN").upper(), 0) + 1
        return summary


class PolicyEnforcer:
    """Main policy enforcement orchestrator"""
    
    def __init__(self, config_path: str, environment: str = "development"):
        self.config_path = config_path
        self.environment = environment
        self.policy = SecurityPolicy(config_path, environment)
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for policy enforcement"""
        logger = logging.getLogger("security_policy")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def load_scan_results(self, input_files: List[str]) -> List[Dict[str, Any]]:
        """Load and parse Trivy scan results from multiple files"""
        all_vulnerabilities = []
        
        for input_file in input_files:
            if not os.path.exists(input_file):
                self.logger.warning(f"Input file not found: {input_file}")
                continue
                
            try:
                with open(input_file, 'r') as f:
                    data = json.load(f)
                
                # Handle different Trivy output formats
                if isinstance(data, dict):
                    if 'Results' in data:
                        # Standard Trivy format
                        for result in data['Results']:
                            vulnerabilities = result.get('Vulnerabilities', [])
                            all_vulnerabilities.extend(vulnerabilities)
                    elif 'vulnerabilities' in data:
                        # Alternative format
                        all_vulnerabilities.extend(data['vulnerabilities'])
                elif isinstance(data, list):
                    # Direct list of vulnerabilities
                    all_vulnerabilities.extend(data)
                    
                self.logger.info(f"Loaded {len(all_vulnerabilities)} vulnerabilities from {input_file}")
                
            except Exception as e:
                self.logger.error(f"Error loading scan results from {input_file}: {e}")
                
        return all_vulnerabilities
    
    def generate_report(self, vulnerabilities: List[Dict[str, Any]], 
                       output_dir: str, format_type: str) -> Optional[str]:
        """Generate security report in specified format"""
        summary = self.policy.summarize(vulnerabilities)
        should_fail = self.policy.should_fail(summary)
        
        report_data = {
            "metadata": {
                "timestamp": "2024-01-01T00:00:00Z",  # Will be updated with actual timestamp
                "environment": self.environment,
                "policy_config": self.config_path
            },
            "summary": summary,
            "policy_violations": should_fail,
            "total_vulnerabilities": len(vulnerabilities),
            "filtered_vulnerabilities": len([v for v in vulnerabilities if not self.policy.is_allowed(v)]),
            "vulnerabilities": vulnerabilities
        }
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if format_type.lower() == "json":
            report_file = output_path / "security_policy_report.json"
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            return str(report_file)
            
        elif format_type.lower() == "table":
            report_file = output_path / "security_policy_report.txt"
            with open(report_file, 'w') as f:
                f.write("SMC Trading Agent - Security Policy Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Environment: {self.environment}\n")
                f.write(f"Policy Violations: {'YES' if should_fail else 'NO'}\n\n")
                f.write("Vulnerability Summary:\n")
                for severity, count in summary.items():
                    f.write(f"  {severity}: {count}\n")
                f.write(f"\nTotal Vulnerabilities: {len(vulnerabilities)}\n")
                f.write(f"Filtered (Allowed): {len(vulnerabilities) - len([v for v in vulnerabilities if not self.policy.is_allowed(v)])}\n")
            return str(report_file)
            
        elif format_type.lower() == "sarif":
            report_file = output_path / "security_policy_report.sarif"
            sarif_data = {
                "version": "2.1.0",
                "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
                "runs": [{
                    "tool": {
                        "driver": {
                            "name": "SMC Security Policy",
                            "version": "1.0.0"
                        }
                    },
                    "results": []
                }]
            }
            
            for vuln in vulnerabilities:
                if not self.policy.is_allowed(vuln):
                    sarif_data["runs"][0]["results"].append({
                        "ruleId": vuln.get("VulnerabilityID", "unknown"),
                        "level": "error" if vuln.get("Severity", "").upper() in ["CRITICAL", "HIGH"] else "warning",
                        "message": {
                            "text": f"Security vulnerability: {vuln.get('Title', 'Unknown vulnerability')}"
                        }
                    })
            
            with open(report_file, 'w') as f:
                json.dump(sarif_data, f, indent=2)
            return str(report_file)
        
        return None
    
    def enforce_policies(self, input_files: List[str], output_dir: str, 
                        format_type: str) -> int:
        """Main policy enforcement function"""
        self.logger.info(f"Starting security policy enforcement for environment: {self.environment}")
        
        # Load scan results
        vulnerabilities = self.load_scan_results(input_files)
        
        if not vulnerabilities:
            self.logger.warning("No vulnerabilities found in input files")
            return 0
        
        # Generate summary
        summary = self.policy.summarize(vulnerabilities)
        should_fail = self.policy.should_fail(summary)
        
        # Log summary
        self.logger.info(f"Vulnerability summary: {summary}")
        self.logger.info(f"Policy violations detected: {should_fail}")
        
        # Generate report
        report_file = self.generate_report(vulnerabilities, output_dir, format_type)
        if report_file:
            self.logger.info(f"Security report generated: {report_file}")
        
        # Return appropriate exit code
        if should_fail:
            self.logger.error("Security policy violations detected - failing build")
            return 1
        else:
            self.logger.info("No security policy violations detected")
            return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Security Policy Enforcement Tool for SMC Trading Agent"
    )
    
    parser.add_argument(
        "--config",
        default="config/security_policy.yaml",
        help="Path to security policy configuration file"
    )
    
    parser.add_argument(
        "--environment",
        default="development",
        choices=["development", "staging", "production"],
        help="Environment for policy enforcement"
    )
    
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "table", "sarif"],
        help="Output format for reports"
    )
    
    parser.add_argument(
        "--output",
        default="docs/sbom",
        help="Output directory for reports"
    )
    
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Input scan result files (can be specified multiple times)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create policy enforcer
    enforcer = PolicyEnforcer(args.config, args.environment)
    
    # Enforce policies
    exit_code = enforcer.enforce_policies(args.input, args.output, args.format)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()