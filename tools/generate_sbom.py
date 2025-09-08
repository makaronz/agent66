#!/usr/bin/env python3
"""
SBOM Generation Tool for SMC Trading Agent
Generates CycloneDX Software Bill of Materials (SBOM) for Python and Node.js components
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SBOMGenerator:
    """Comprehensive SBOM generation for multi-language codebase"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for SBOM generation"""
        logger = logging.getLogger("sbom_generator")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def detect_package_manager(self) -> str:
        """Detect package manager (npm vs pnpm) based on lock files"""
        if (self.project_root / "pnpm-lock.yaml").exists():
            self.logger.info("Detected pnpm package manager")
            return "pnpm"
        elif (self.project_root / "package-lock.json").exists():
            self.logger.info("Detected npm package manager")
            return "npm"
        elif (self.project_root / "package.json").exists():
            self.logger.info("Found package.json, defaulting to npm")
            return "npm"
        else:
            self.logger.warning("No package manager detected")
            return "npm"

    def validate_dependencies(self) -> Tuple[bool, bool]:
        """Validate that dependency files exist"""
        requirements_exists = (self.project_root / "requirements.txt").exists()
        package_json_exists = (self.project_root / "package.json").exists()
        
        if not requirements_exists:
            self.logger.warning("requirements.txt not found")
        if not package_json_exists:
            self.logger.warning("package.json not found")
            
        return requirements_exists, package_json_exists

    def generate_python_sbom(self, output_dir: Path, format_type: str = "json") -> Optional[Path]:
        """Generate SBOM for Python dependencies using cyclonedx library"""
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            self.logger.warning("No requirements.txt found, skipping Python SBOM generation")
            return None
        
        output_file = output_dir / f"python.sbom.{format_type}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Generating Python SBOM from {requirements_file}")
        
        try:
            from cyclonedx.model.bom import Bom
            from cyclonedx.output.json import JsonV1Dot5
            from cyclonedx.output.xml import XmlV1Dot5
            from cyclonedx.model.component import Component, ComponentType
            from packageurl import PackageURL
            import hashlib
            import re
            
            # Create BOM
            bom = Bom()
            
            # Parse requirements.txt
            with open(requirements_file, 'r') as f:
                requirements = f.readlines()
            
            for req_line in requirements:
                req_line = req_line.strip()
                if not req_line or req_line.startswith('#'):
                    continue
                    
                # Simple parsing - split on == or >= etc.
                match = re.match(r'^([a-zA-Z0-9_-]+)([><=!]+)?(.*)?$', req_line)
                if match:
                    package_name = match.group(1)
                    version_raw = match.group(3) if match.group(3) else None
                    version = version_raw.strip() if version_raw and version_raw.strip() else "unknown"
                    
                    self.logger.debug(f"Processing package: {package_name}, version_raw: {version_raw}, version: {version}")
                    
                    # Create component
                    try:
                        self.logger.debug(f"About to create Component with: name={package_name}, type={ComponentType.LIBRARY}, version={version}")
                        self.logger.debug(f"ComponentType.LIBRARY type: {type(ComponentType.LIBRARY)}")
                        
                        # Create PackageURL object
                        if version != "unknown":
                            purl = PackageURL(type="pypi", name=package_name, version=version)
                        else:
                            purl = PackageURL(type="pypi", name=package_name)
                        
                        component = Component(
                            type=ComponentType.LIBRARY,
                            name=package_name,
                            version=version if version != "unknown" else None,
                            purl=purl
                        )
                        self.logger.debug(f"Component created successfully: {component}")
                        bom.components.add(component)
                        self.logger.debug(f"Successfully added component: {package_name}")
                    except Exception as e:
                        self.logger.error(f"Error creating component for {package_name}: {e}")
                        import traceback
                        self.logger.error(f"Traceback: {traceback.format_exc()}")
                        raise
            
            # Write SBOM to file
            if format_type.lower() == "json":
                serializer = JsonV1Dot5(bom)
            else:  # xml
                serializer = XmlV1Dot5(bom)
            
            with open(output_file, 'w') as f:
                f.write(serializer.output_as_string())
            
            if output_file.exists():
                self.logger.info(f"Python SBOM successfully generated: {output_file}")
                return output_file
            else:
                self.logger.error("Python SBOM file was not created")
                return None
                
        except ImportError as e:
            self.logger.error(f"cyclonedx library not found. Install with: pip install cyclonedx-bom. Error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error generating Python SBOM: {e}")
            return None

    def generate_nodejs_sbom(self, output_dir: Path, format_type: str = "json") -> Optional[Path]:
        """Generate SBOM for Node.js dependencies using @cyclonedx/cdxgen"""
        package_json = self.project_root / "package.json"
        
        if not package_json.exists():
            self.logger.error("package.json not found, skipping Node.js SBOM generation")
            return None

        # Determine output filename based on format
        if format_type.lower() == "xml":
            output_file = output_dir / "node.sbom.xml"
            fmt_flags: List[str] = ["--format", "xml"]
        else:
            output_file = output_dir / "node.sbom.json"
            fmt_flags = []

        self.logger.info(f"Generating Node.js SBOM from {package_json}")

        # Choose execution strategy based on package manager and local availability
        pkg_mgr = self.detect_package_manager()
        try:
            local_cdxgen = self.project_root / "node_modules" / ".bin" / "cdxgen"
            if local_cdxgen.exists():
                base_cmd = [str(local_cdxgen)]
            elif pkg_mgr == "pnpm":
                base_cmd = ["pnpm", "exec", "cdxgen"]
            else:
                base_cmd = ["npx", "@cyclonedx/cdxgen"]

            cmd = base_cmd + [
                "-o", str(output_file),
                "-t", "js",
                "--spec-version", "1.5",
                str(self.project_root)
            ] + fmt_flags

            self.logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode == 0:
                self.logger.info(f"Node.js SBOM successfully generated: {output_file}")
                return output_file
            else:
                self.logger.error(f"cdxgen failed with return code {result.returncode}")
                self.logger.error(f"Error output: {result.stderr}")
                return None

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error running cdxgen: {e}")
            self.logger.error(f"Command output: {e.stdout}")
            self.logger.error(f"Command error: {e.stderr}")
            return None
        except FileNotFoundError:
            self.logger.error("cdxgen not found. Ensure Node.js is installed and @cyclonedx/cdxgen is available")
            return None

    def generate_all_sboms(self, output_dir: Path, format_type: str = "json") -> Dict[str, Optional[Path]]:
        """Generate SBOMs for all detected languages"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "python": None,
            "nodejs": None
        }
        
        # Generate Python SBOM
        python_sbom = self.generate_python_sbom(output_dir, format_type)
        if python_sbom:
            results["python"] = python_sbom
            
        # Generate Node.js SBOM
        nodejs_sbom = self.generate_nodejs_sbom(output_dir, format_type)
        if nodejs_sbom:
            results["nodejs"] = nodejs_sbom
            
        return results

    def generate_summary_report(self, output_dir: Path, sbom_results: Dict[str, Optional[Path]]) -> Path:
        """Generate a summary report of SBOM generation"""
        summary_file = output_dir / "sbom_generation_summary.json"
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "generated_sboms": {},
            "status": "success" if any(sbom_results.values()) else "failed"
        }
        
        for lang, sbom_path in sbom_results.items():
            if sbom_path:
                summary["generated_sboms"][lang] = {
                    "path": str(sbom_path),
                    "size_bytes": sbom_path.stat().st_size if sbom_path.exists() else 0,
                    "status": "success"
                }
            else:
                summary["generated_sboms"][lang] = {
                    "path": None,
                    "status": "failed"
                }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        self.logger.info(f"Summary report generated: {summary_file}")
        return summary_file


def main():
    """Main entry point for SBOM generation"""
    parser = argparse.ArgumentParser(
        description="Generate Software Bill of Materials (SBOM) for SMC Trading Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --output docs/sbom --format json
  %(prog)s --output /tmp/sbom --format xml --verbose
  %(prog)s --python-only --output docs/sbom
        """
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="docs/sbom",
        help="Output directory for SBOM files (default: docs/sbom)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "xml"],
        default="json",
        help="Output format for SBOM files (default: json)"
    )
    
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="Generate only Python SBOM"
    )
    
    parser.add_argument(
        "--nodejs-only",
        action="store_true",
        help="Generate only Node.js SBOM"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger("sbom_generator").setLevel(logging.DEBUG)
    
    # Initialize generator
    generator = SBOMGenerator(args.project_root)
    output_dir = Path(args.output)
    
    try:
        # Validate dependencies
        has_requirements, has_package_json = generator.validate_dependencies()
        
        if not has_requirements and not has_package_json:
            generator.logger.error("No dependency files found (requirements.txt or package.json)")
            sys.exit(1)
        
        # Generate SBOMs based on arguments
        results = {}
        
        if args.python_only:
            python_sbom = generator.generate_python_sbom(output_dir, args.format)
            results["python"] = python_sbom
        elif args.nodejs_only:
            nodejs_sbom = generator.generate_nodejs_sbom(output_dir, args.format)
            results["nodejs"] = nodejs_sbom
        else:
            results = generator.generate_all_sboms(output_dir, args.format)
        
        # Generate summary report
        summary_file = generator.generate_summary_report(output_dir, results)
        
        # Check if any SBOMs were generated successfully
        success_count = sum(1 for sbom in results.values() if sbom is not None)
        total_count = len(results)
        
        if success_count == 0:
            generator.logger.error("No SBOMs were generated successfully")
            sys.exit(1)
        elif success_count < total_count:
            generator.logger.warning(f"Only {success_count}/{total_count} SBOMs generated successfully")
            sys.exit(0)
        else:
            generator.logger.info(f"All {success_count} SBOMs generated successfully")
            sys.exit(0)
            
    except Exception as e:
        generator.logger.error(f"Unexpected error during SBOM generation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()