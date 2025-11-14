#!/usr/bin/env python3
"""
Vulnerability Scanning Tool for SMC Trading Agent
- Filesystem scanning using Trivy
- SBOM-based scanning for Python and Node.js
- Optional container image scanning for Docker builds
- Policy enforcement using tools/security_policy.py
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Local imports
from security_policy import SecurityPolicy


class VulnerabilityScanner:
    def __init__(self, project_root: str = ".", environment: str = "development"):
        self.project_root = Path(project_root).resolve()
        self.environment = environment
        self.logger = self._setup_logging()
        self.output_dir = self.project_root / "docs" / "sbom"
        self.config_path = self.project_root / "config" / "trivy.yaml"
        self.ensure_output_dir()

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("vuln_scanner")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _trivy_available(self) -> bool:
        return shutil.which("trivy") is not None

    def _docker_available(self) -> bool:
        return shutil.which("docker") is not None

    # -----------------------
    # Trivy runners
    # -----------------------
    def run_trivy_fs(self, fmt: str = "json", output_file: Optional[Path] = None) -> Optional[Path]:
        if not self._trivy_available():
            self.logger.error("Trivy not found. Please install Trivy to run scans.")
            return None

        out = output_file or (self.output_dir / ("trivy_scan.sarif" if fmt == "sarif" else "trivy_scan.json"))
        cmd = [
            "trivy", "fs",
            "--quiet",
            "--format", fmt,
            "--output", str(out),
        ]
        # Use config if present
        if self.config_path.exists():
            cmd.extend(["--config", str(self.config_path)])
        cmd.append(str(self.project_root))

        return self._exec_trivy(cmd, out)

    def run_trivy_sbom(self, sbom_file: Path, fmt: str = "json", output_suffix: str = "") -> Optional[Path]:
        if not self._trivy_available():
            self.logger.error("Trivy not found. Please install Trivy to run scans.")
            return None
        name = sbom_file.stem.replace(".", "_")
        out_name = f"{name}_vulns.{('sarif' if fmt=='sarif' else 'json')}"
        if output_suffix:
            parts = out_name.split('.')
            out_name = f"{parts[0]}_{output_suffix}.{parts[1]}"
        out = self.output_dir / out_name
        cmd = [
            "trivy", "sbom",
            "--quiet",
            "--format", fmt,
            "--output", str(out),
        ]
        if self.config_path.exists():
            cmd.extend(["--config", str(self.config_path)])
        cmd.append(str(sbom_file))
        return self._exec_trivy(cmd, out)

    def run_trivy_image(self, image: str, fmt: str = "json") -> Optional[Path]:
        if not self._trivy_available():
            self.logger.error("Trivy not found. Please install Trivy to run scans.")
            return None
        safe = image.replace(":", "_").replace("/", "_")
        out = self.output_dir / f"trivy_image_{safe}.{('sarif' if fmt=='sarif' else 'json')}"
        cmd = [
            "trivy", "image",
            "--quiet",
            "--format", fmt,
            "--output", str(out),
            image,
        ]
        return self._exec_trivy(cmd, out)

    def _exec_trivy(self, cmd: List[str], out: Path) -> Optional[Path]:
        try:
            self.logger.info(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, cwd=self.project_root, check=True, text=True, capture_output=True)
            self.logger.info(f"Scan completed: {out}")
            return out
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Trivy command failed: {e}")
            self.logger.error(f"Stdout: {e.stdout}\nStderr: {e.stderr}")
            return None
        except FileNotFoundError:
            self.logger.error("Trivy executable not found.")
            return None

    # -----------------------
    # Docker image build & scan
    # -----------------------
    def build_and_scan_images(self, dockerfiles: List[Path], fmt: str = "json") -> List[Path]:
        results: List[Path] = []
        if not self._docker_available():
            self.logger.warning("Docker not available. Skipping container image scanning.")
            return results

        for df in dockerfiles:
            tag = f"smc/{df.stem.lower()}:scan"
            try:
                self.logger.info(f"Building image {tag} from {df}")
                subprocess.run([
                    "docker", "build", "-f", str(df), "-t", tag, "."
                ], cwd=self.project_root, check=True)
                res = self.run_trivy_image(tag, fmt)
                if res:
                    results.append(res)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Docker build failed for {df}: {e}")
                continue
        return results

    # -----------------------
    # Parsing & policy
    # -----------------------
    def parse_trivy_json(self, file_path: Path) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            return []

        vulns: List[Dict[str, Any]] = []
        # Trivy JSON structures can differ by command; handle common schema
        results = data.get("Results", []) if isinstance(data, dict) else []
        for r in results:
            for v in r.get("Vulnerabilities", []) or []:
                # Normalize keys we care about
                vulns.append({
                    "Target": r.get("Target"),
                    "Type": r.get("Type"),
                    "VulnerabilityID": v.get("VulnerabilityID"),
                    "PkgName": v.get("PkgName") or v.get("PackageName"),
                    "InstalledVersion": v.get("InstalledVersion"),
                    "FixedVersion": v.get("FixedVersion"),
                    "Severity": (v.get("Severity") or "UNKNOWN").upper(),
                    "Title": v.get("Title"),
                    "PrimaryURL": v.get("PrimaryURL") or v.get("PrimaryURL"),
                })
        return vulns

    def aggregate_by_severity(self, vulns: List[Dict[str, Any]], policy: SecurityPolicy) -> Dict[str, int]:
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        for v in vulns:
            if policy.is_allowed(v):
                continue
            sev = (v.get("Severity") or "UNKNOWN").upper()
            if sev not in summary:
                summary[sev] = 0
            summary[sev] += 1
        return summary

    def print_table_summary(self, title: str, summary: Dict[str, int]) -> None:
        total = sum(summary.values())
        self.logger.info(f"=== {title} ===")
        self.logger.info(f"Total: {total} | CRITICAL: {summary.get('CRITICAL',0)} | HIGH: {summary.get('HIGH',0)} | MEDIUM: {summary.get('MEDIUM',0)} | LOW: {summary.get('LOW',0)} | UNKNOWN: {summary.get('UNKNOWN',0)}")

    # -----------------------
    # High-level modes
    # -----------------------
    def run(self, mode: str = "full", fmt: str = "json") -> int:
        policy = SecurityPolicy(environment=self.environment)
        report: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "environment": self.environment,
            "mode": mode,
            "format": fmt,
            "scans": {},
            "errors": [],
        }

        # Locate SBOMs (support both naming conventions)
        sbom_candidates = [
            self.output_dir / "python.sbom.json",
            self.output_dir / "node.sbom.json",
            self.output_dir / "python_sbom.json",
            self.output_dir / "nodejs_sbom.json",
            self.output_dir / "python_sbom.xml",
            self.output_dir / "nodejs_sbom.xml",
            self.output_dir / "python.sbom.xml",
            self.output_dir / "node.sbom.xml",
        ]
        sboms = [p for p in sbom_candidates if p.exists()]

        # 1) Filesystem scan
        fs_result_path: Optional[Path] = None
        if mode in ("full",):
            fs_result_path = self.run_trivy_fs(fmt=("sarif" if fmt=="sarif" else "json"))
            if fs_result_path and fs_result_path.suffix == ".json":
                fs_vulns = self.parse_trivy_json(fs_result_path)
                fs_summary = self.aggregate_by_severity(fs_vulns, policy)
                report["scans"]["filesystem"] = {
                    "file": str(fs_result_path),
                    "summary": fs_summary,
                }
                if fmt == "table":
                    self.print_table_summary("Filesystem Scan", fs_summary)
            elif fs_result_path is None:
                report["errors"].append("Filesystem scan failed")

        # 2) SBOM scans (quick mode prefers this)
        if mode in ("full", "quick"):
            for sbom in sboms:
                sbom_fmt = "sarif" if fmt == "sarif" else "json"
                sbom_scan_path = self.run_trivy_sbom(sbom, fmt=sbom_fmt)
                key = f"sbom:{sbom.name}"
                if sbom_scan_path and sbom_scan_path.suffix == ".json":
                    vulns = self.parse_trivy_json(sbom_scan_path)
                    summary = self.aggregate_by_severity(vulns, policy)
                    report["scans"][key] = {"file": str(sbom_scan_path), "summary": summary}
                    if fmt == "table":
                        self.print_table_summary(f"SBOM Scan - {sbom.name}", summary)
                elif sbom_scan_path is None:
                    report["errors"].append(f"SBOM scan failed for {sbom}")
                else:
                    # SARIF output; just record the file path
                    report["scans"][key] = {"file": str(sbom_scan_path)}

        # 3) Container image scans (only in full mode and if Docker is available)
        if mode == "full":
            dockerfiles = [
                self.project_root / "smc_agent.Dockerfile",
                self.project_root / "data_pipeline.Dockerfile",
            ]
            dockerfiles = [p for p in dockerfiles if p.exists()]
            if dockerfiles:
                image_results = self.build_and_scan_images(dockerfiles, fmt=("sarif" if fmt=="sarif" else "json"))
                report["scans"]["images"] = [str(p) for p in image_results]

        # Aggregate totals for JSON report
        aggregated: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        for scan in report["scans"].values():
            if isinstance(scan, dict) and "summary" in scan:
                for sev, cnt in scan["summary"].items():
                    aggregated[sev] = aggregated.get(sev, 0) + cnt
        report["aggregated"] = aggregated

        # Policy decision
        report["policy"] = {
            "environment": self.environment,
            "fail_on_severity": policy.policy.fail_on_severity,
            "thresholds": policy.policy.thresholds,
        }
        should_fail = policy.should_fail(aggregated)
        report["result"] = "FAIL" if should_fail else "PASS"

        # Output handling
        exit_code = 1 if should_fail else 0
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        if fmt == "table":
            self.print_table_summary("Aggregated", aggregated)
            self.logger.info(f"Policy result: {report['result']}")
        else:
            # Always write a consolidated JSON report for machine consumption
            out_report = self.output_dir / f"security_report_{ts}.json"
            with open(out_report, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            self.logger.info(f"Security report written: {out_report}")

        return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Run security vulnerability scans with Trivy")
    parser.add_argument("--mode", choices=["full", "quick", "report"], default="full", help="Scan mode")
    parser.add_argument("--format", dest="fmt", choices=["json", "table", "sarif"], default="json", help="Output format for scans")
    parser.add_argument("--env", dest="environment", choices=["development", "production"], default="development", help="Policy environment")

    args = parser.parse_args()

    scanner = VulnerabilityScanner(project_root=".", environment=args.environment)

    if args.mode == "report":
        # In report mode, do not run scans; just summarize existing Trivy JSON if present
        # We'll look for the latest trivy_scan.json and SBOM vuln files and produce a consolidated report
        return_code = scanner.run(mode="quick", fmt=args.fmt)
        sys.exit(return_code)

    rc = scanner.run(mode=args.mode, fmt=args.fmt)
    sys.exit(rc)


if __name__ == "__main__":
    main()