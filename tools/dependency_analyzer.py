#!/usr/bin/env python3
"""
Dependency Analyzer
Parses requirements.txt and package.json to emit a consolidated dependency inventory.
Stdlib only. Outputs JSON to stdout or file, optional CSV summary.
"""
from __future__ import annotations
import argparse
import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Any

REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)(?:\[.*?\])?\s*==\s*([A-Za-z0-9_.\-]+)\s*$")


def parse_requirements(path: Path) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    if not path.exists():
        return items
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = REQ_LINE.match(line)
        if not m:
            # skip unpinned or complex lines; still record raw
            items.append({"name": line, "version": "unparsed"})
            continue
        name, version = m.group(1), m.group(2)
        items.append({"name": name, "version": version})
    return items


def parse_package_json(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {"dependencies": {}, "devDependencies": {}}
    data = json.loads(path.read_text())
    return {
        "dependencies": data.get("dependencies", {}) or {},
        "devDependencies": data.get("devDependencies", {}) or {},
    }


def build_inventory(reqs: List[Dict[str, str]], pkg: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    # naive categorization for Python: split dev by common tool names
    dev_tools = {"pytest", "pytest-asyncio", "pytest-cov", "black", "isort", "flake8", "mypy"}
    py_prod, py_dev = [], []
    for it in reqs:
        if it["name"].split("[")[0] in dev_tools:
            py_dev.append({"name": it["name"], "version": it["version"]})
        else:
            py_prod.append({"name": it["name"], "version": it["version"]})

    return {
        "python": {"production": py_prod, "development": py_dev},
        "node": {
            "dependencies": pkg.get("dependencies", {}),
            "devDependencies": pkg.get("devDependencies", {}),
        },
    }


def write_json(inv: Dict[str, Any], out: Path | None) -> None:
    payload = json.dumps(inv, indent=2, ensure_ascii=False)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload)
    else:
        print(payload)


def write_csv(inv: Dict[str, Any], out: Path) -> None:
    rows: List[List[str]] = []
    for dep in inv.get("python", {}).get("production", []):
        rows.append(["python", "production", dep["name"], dep["version"]])
    for dep in inv.get("python", {}).get("development", []):
        rows.append(["python", "development", dep["name"], dep["version"]])
    for name, ver in inv.get("node", {}).get("dependencies", {}).items():
        rows.append(["node", "dependencies", name, ver])
    for name, ver in inv.get("node", {}).get("devDependencies", {}).items():
        rows.append(["node", "devDependencies", name, ver])

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ecosystem", "scope", "name", "version"])
        w.writerows(rows)


def main() -> int:
    p = argparse.ArgumentParser(description="Generate dependency inventory from requirements.txt and package.json")
    p.add_argument("--requirements", default="smc_trading_agent/requirements.txt")
    p.add_argument("--package", dest="package_json", default="smc_trading_agent/package.json")
    p.add_argument("--json-out", dest="json_out", default=None)
    p.add_argument("--csv-out", dest="csv_out", default=None)
    args = p.parse_args()

    reqs = parse_requirements(Path(args.requirements))
    pkg = parse_package_json(Path(args.package_json))
    inv = build_inventory(reqs, pkg)

    if args.json_out:
        write_json(inv, Path(args.json_out))
    else:
        write_json(inv, None)

    if args.csv_out:
        write_csv(inv, Path(args.csv_out))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
