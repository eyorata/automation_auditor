import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.graph import run_detective_graph


MERMAID_ARCH = """```mermaid
flowchart TD
    S([START])
    RI[RepoInvestigator]
    DA[DocAnalyst]
    VI[VisionInspector]
    EA[EvidenceAggregator]
    EC[ErrorCollector]
    IE[InsufficientEvidence]
    E([END])

    S --> RI
    S --> DA
    S --> VI
    RI --> EA
    DA --> EA
    VI --> EA
    EA -->|has_node_errors| EC
    EA -->|insufficient_evidence| IE
    EA -->|healthy path| E
    EC --> E
    IE --> E
```
"""


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


def _collect_evidence_summary(evidences: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    counts = {k: len(v) for k, v in evidences.items()}
    all_items = [item for values in evidences.values() for item in values]
    avg_conf = 0.0
    if all_items:
        avg_conf = sum(float(item.get("confidence", 0.0)) for item in all_items) / len(all_items)
    return {"counts": counts, "total_items": len(all_items), "average_confidence": round(avg_conf, 3)}


def _build_markdown(
    repo_url: str,
    pdf_path: str,
    result: Dict[str, Any],
    json_path: Path,
) -> str:
    evidences = result.get("evidences", {})
    summary = _collect_evidence_summary(evidences)
    flags = result.get("flags", {})
    node_errors = result.get("node_errors", [])

    lines = [
        "# Audit Snapshot",
        "",
        f"- Generated UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Repo URL: `{repo_url}`",
        f"- PDF Path: `{pdf_path}`",
        f"- Raw JSON: `{json_path.as_posix()}`",
        "",
        "## Architecture Diagram",
        "",
        MERMAID_ARCH.strip(),
        "",
        "## Runtime Summary",
        "",
        f"- Total Evidence Items: **{summary['total_items']}**",
        f"- Average Confidence: **{summary['average_confidence']}**",
        f"- Flags: `{flags}`",
        f"- Node Errors: `{len(node_errors)}`",
        "",
        "## Evidence Counts By Bucket",
        "",
    ]

    for key, count in sorted(summary["counts"].items()):
        lines.append(f"- `{key}`: {count}")

    if node_errors:
        lines.extend(["", "## Node Errors", ""])
        for err in node_errors:
            lines.append(f"- {err}")

    lines.extend(["", "## Quick Notes", ""])
    if flags.get("has_node_errors", False):
        lines.append("- Execution had node failures; review `error_collection` evidence before grading.")
    if flags.get("insufficient_evidence", False):
        lines.append("- Evidence was marked insufficient; avoid overconfident scoring.")
    if not flags.get("has_node_errors", False) and not flags.get("insufficient_evidence", False):
        lines.append("- Detective run completed on healthy path.")

    return "\n".join(lines) + "\n"


def run_audit_snapshot(repo_url: str, pdf_path: str, output_dir: str) -> Dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"audit_snapshot_{stamp}.json"
    md_path = out_dir / f"audit_snapshot_{stamp}.md"

    result = run_detective_graph(repo_url=repo_url, pdf_path=pdf_path)
    json_result = _to_jsonable(result)
    json_path.write_text(json.dumps(json_result, indent=2), encoding="utf-8")

    md = _build_markdown(repo_url=repo_url, pdf_path=pdf_path, result=json_result, json_path=json_path)
    md_path.write_text(md, encoding="utf-8")

    return {"json": str(json_path), "markdown": str(md_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Automaton Auditor utilities.")
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("audit-snapshot", help="Run detective graph and write JSON + markdown snapshot.")
    snap.add_argument("--repo-url", required=True, help="Target repository URL.")
    snap.add_argument("--pdf-path", required=True, help="Path to report PDF.")
    snap.add_argument("--output-dir", default="audit/generated", help="Where to write snapshot artifacts.")

    args = parser.parse_args()

    if args.command == "audit-snapshot":
        paths = run_audit_snapshot(args.repo_url, args.pdf_path, args.output_dir)
        print(f"Snapshot JSON: {paths['json']}")
        print(f"Snapshot Markdown: {paths['markdown']}")


if __name__ == "__main__":
    main()

