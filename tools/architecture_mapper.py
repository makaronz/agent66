#!/usr/bin/env python3
"""
Architecture Mapper
Scans selected files to emit a lightweight component map and a Mermaid diagram.
Stdlib only.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List

IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")
REGISTER_SERVICE_RE = re.compile(r"register_service\(\s*\"([\w_\-]+)\"\s*,")
PORT_RE = re.compile(r"PORT\s*=\s*process\.env\.PORT\s*\|\|\s*(\d+)")
YAML_KEY_RE = re.compile(r"^(\w+):\s*$")


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def map_python(file: Path) -> Dict[str, Any]:
    text = safe_read(file)
    imports: List[str] = []
    for line in text.splitlines():
        m = IMPORT_RE.match(line)
        if m:
            imp = m.group(1) or m.group(2)
            imports.append(imp)
    services = REGISTER_SERVICE_RE.findall(text)
    return {"file": str(file), "imports": sorted(set(imports)), "services": services}


def map_node_server(file: Path) -> Dict[str, Any]:
    text = safe_read(file)
    m = PORT_RE.search(text)
    port = int(m.group(1)) if m else 3002
    return {"file": str(file), "port": port}


def map_yaml_keys(file: Path) -> Dict[str, Any]:
    text = safe_read(file)
    top_keys: List[str] = []
    for line in text.splitlines():
        m = YAML_KEY_RE.match(line.strip())
        if m:
            top_keys.append(m.group(1))
    return {"file": str(file), "topLevel": top_keys}


def build_mermaid(summary: Dict[str, Any]) -> str:
    parts = ["graph TD"]
    parts.append("Web[React] --> API[Node API]")
    parts.append("API --> PY[Python Services]")
    parts.append("PY --> RUST[Rust Executor]")
    if summary.get("node", {}).get("port"):
        parts.append(f"API:::node")
    parts.append("PY --> DB[(Postgres)]")
    parts.append("PY --> K[(Kafka)]")
    parts.append("classDef node fill:#eef,stroke:#99f;")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Map architecture components and emit Mermaid + JSON")
    ap.add_argument("--main", default="smc_trading_agent/main.py")
    ap.add_argument("--services", default="smc_trading_agent/service_manager.py")
    ap.add_argument("--server", default="smc_trading_agent/api/server.ts")
    ap.add_argument("--config", default="smc_trading_agent/config.yaml")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--mermaid-out", default=None)
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    summary: Dict[str, Any] = {
        "python": map_python(Path(args.main)),
        "services": map_python(Path(args.services)),
        "node": map_node_server(Path(args.server)),
        "config": map_yaml_keys(Path(args.config)),
    }
    summary["components"] = {
        "services": summary["services"].get("services", []),
        "configKeys": summary["config"].get("topLevel", []),
    }

    mermaid = build_mermaid(summary)

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.mermaid_out:
        Path(args.mermaid_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.mermaid_out).write_text(mermaid, encoding="utf-8")

    if args.print or (not args.json_out and not args.mermaid_out):
        print(json.dumps(summary, indent=2))
        print("\nMermaid:\n" + mermaid)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
