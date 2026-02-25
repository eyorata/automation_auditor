from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools.doc_tools import collect_doc_evidence, cross_reference_claimed_paths, extract_claimed_paths
from src.tools.repo_tools import classify_confidence_tier, collect_repo_evidence


def _error_evidence(scope: str, message: str) -> Evidence:
    return Evidence(
        goal=f"Node error in {scope}",
        found=False,
        content=message,
        location=scope,
        rationale="Captured exception as forensic evidence to avoid silent graph failure.",
        confidence=1.0,
    )


def repo_investigator_node(state: AgentState) -> Dict[str, object]:
    try:
        evidences = collect_repo_evidence(repo_url=state["repo_url"])
        return {"evidences": evidences}
    except Exception as exc:
        msg = f"repo_investigator failed: {exc}"
        return {
            "evidences": {"repo_investigator_error": [_error_evidence("repo_investigator", msg)]},
            "node_errors": [msg],
            "flags": {"repo_investigator_failed": True},
        }


def doc_analyst_node(state: AgentState) -> Dict[str, object]:
    try:
        doc_evidences = collect_doc_evidence(pdf_path=state["pdf_path"])
        return {"evidences": {"pdf_report_analysis": doc_evidences}}
    except Exception as exc:
        msg = f"doc_analyst failed: {exc}"
        return {
            "evidences": {"doc_analyst_error": [_error_evidence("doc_analyst", msg)]},
            "node_errors": [msg],
            "flags": {"doc_analyst_failed": True},
        }


def vision_inspector_node(_state: AgentState) -> Dict[str, Dict[str, List[Evidence]]]:
    return {
        "evidences": {
            "pdf_images": [
                Evidence(
                    goal="Extract and inspect architectural diagrams",
                    found=False,
                    content="Vision analysis is scaffolded but not executed in interim scope.",
                    location="src/nodes/detectives.py",
                    rationale="Interim submission requires implementation readiness; execution is optional.",
                    confidence=0.6,
                )
            ]
        }
    }


def evidence_aggregator_node(state: AgentState) -> Dict[str, object]:
    summary = {k: len(v) for k, v in state.get("evidences", {}).items()}
    errors = state.get("node_errors", [])
    insufficient = sum(summary.values()) < 3

    repo_inventory = state.get("evidences", {}).get("repo_file_inventory", [])
    doc_analysis = state.get("evidences", {}).get("pdf_report_analysis", [])
    cross_ref = {"verified_paths": [], "hallucinated_paths": []}
    if repo_inventory and doc_analysis:
        try:
            repo_files_str = repo_inventory[0].content or "[]"
            claimed_paths_str = doc_analysis[-1].content or ""
            import json

            repo_files = json.loads(repo_files_str)
            claimed_paths = [p.strip() for p in claimed_paths_str.splitlines() if p.strip()]
            # Fallback parse if no extracted paths were present in evidence content.
            if not claimed_paths and doc_analysis[0].content:
                claimed_paths = extract_claimed_paths(doc_analysis[0].content)
            cross_ref = cross_reference_claimed_paths(claimed_paths=claimed_paths, repo_files=repo_files)
        except Exception:
            cross_ref = {"verified_paths": [], "hallucinated_paths": []}

    avg_conf = 0.0
    all_items: List[Evidence] = []
    for values in state.get("evidences", {}).values():
        all_items.extend(values)
    if all_items:
        avg_conf = sum(item.confidence for item in all_items) / len(all_items)
    conf_tier = classify_confidence_tier(avg_conf)

    return {
        "evidences": {
            "evidence_aggregation": [
                Evidence(
                    goal="Aggregate detective outputs",
                    found=True,
                    content=str(
                        {
                            "evidence_counts": summary,
                            "node_errors": errors,
                            "insufficient_evidence": insufficient,
                            "cross_reference": cross_ref,
                            "confidence_tier": conf_tier,
                        }
                    ),
                    location="graph/evidence_aggregator",
                    rationale="Fan-in point confirms collection across parallel detective branches.",
                    confidence=0.95,
                )
            ]
        },
        "flags": {
            "insufficient_evidence": insufficient,
            "has_node_errors": len(errors) > 0,
        },
    }


def error_collector_node(state: AgentState) -> Dict[str, object]:
    errors = state.get("node_errors", [])
    return {
        "evidences": {
            "error_collection": [
                Evidence(
                    goal="Collect node failures for governed error handling",
                    found=len(errors) > 0,
                    content="\n".join(errors),
                    location="graph/error_collector",
                    rationale="Centralized error evidence supports deterministic downgrade paths.",
                    confidence=1.0,
                )
            ]
        }
    }


def insufficient_evidence_node(state: AgentState) -> Dict[str, object]:
    return {
        "evidences": {
            "insufficient_evidence": [
                Evidence(
                    goal="Flag insufficient evidence volume",
                    found=bool(state.get("flags", {}).get("insufficient_evidence", False)),
                    content=str({k: len(v) for k, v in state.get("evidences", {}).items()}),
                    location="graph/insufficient_evidence",
                    rationale="Explicit path for low-evidence conditions to prevent overconfident judgment.",
                    confidence=0.9,
                )
            ]
        }
    }
