import json
from pathlib import Path
from typing import Dict, List

from langgraph.graph import END, START, StateGraph

from src.nodes.detectives import (
    doc_analyst_node,
    evidence_aggregator_node,
    error_collector_node,
    insufficient_evidence_node,
    repo_investigator_node,
    vision_inspector_node,
)
from src.nodes.judges import defense_node, prosecutor_node, retry_judge_node, techlead_node
from src.nodes.justice import chief_justice_node
from src.state import AgentState, Evidence


def load_rubric_dimensions(rubric_path: str) -> List[Dict]:
    path = Path(rubric_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("dimensions", [])


def judge_aggregator_node(state: AgentState) -> Dict[str, object]:
    return {
        "evidences": {
            "judge_aggregation": [
                Evidence(
                    goal="Aggregate parallel judicial outputs",
                    found=len(state.get("opinions", [])) > 0,
                    content=f"opinion_count={len(state.get('opinions', []))}",
                    location="graph/judge_aggregator",
                    rationale="Fan-in point before deterministic Chief Justice synthesis.",
                    confidence=0.95,
                )
            ]
        }
    }


def judge_dispatch_node(_state: AgentState) -> Dict[str, object]:
    return {}


def build_final_graph():
    builder = StateGraph(AgentState)

    # Detective layer
    builder.add_node("repo_investigator", repo_investigator_node)
    builder.add_node("doc_analyst", doc_analyst_node)
    builder.add_node("vision_inspector", vision_inspector_node)
    builder.add_node("evidence_aggregator", evidence_aggregator_node)
    builder.add_node("error_collector", error_collector_node)
    builder.add_node("insufficient_evidence", insufficient_evidence_node)

    # Judicial layer
    builder.add_node("prosecutor", prosecutor_node)
    builder.add_node("defense", defense_node)
    builder.add_node("techlead", techlead_node)
    builder.add_node("judge_dispatch", judge_dispatch_node)
    builder.add_node("judge_aggregator", judge_aggregator_node)
    builder.add_node("retry_judge", retry_judge_node)

    # Synthesis
    builder.add_node("chief_justice", chief_justice_node)

    # Detectives fan-out
    builder.add_edge(START, "repo_investigator")
    builder.add_edge(START, "doc_analyst")
    builder.add_edge(START, "vision_inspector")

    # Detectives fan-in
    builder.add_edge("repo_investigator", "evidence_aggregator")
    builder.add_edge("doc_analyst", "evidence_aggregator")
    builder.add_edge("vision_inspector", "evidence_aggregator")

    def _route_after_evidence(state: AgentState):
        flags = state.get("flags", {})
        if flags.get("has_node_errors", False):
            return "error_collector"
        if flags.get("insufficient_evidence", False):
            return "insufficient_evidence"
        return "judge_dispatch"

    builder.add_conditional_edges(
        "evidence_aggregator",
        _route_after_evidence,
        {
            "error_collector": "error_collector",
            "insufficient_evidence": "insufficient_evidence",
            "judge_dispatch": "judge_dispatch",
        },
    )
    builder.add_edge("judge_dispatch", "prosecutor")
    builder.add_edge("judge_dispatch", "defense")
    builder.add_edge("judge_dispatch", "techlead")

    # If evidence paths fail, still continue to retry_judge and produce deterministic fallback opinions.
    builder.add_edge("error_collector", "retry_judge")
    builder.add_edge("insufficient_evidence", "retry_judge")

    # Judges fan-in
    builder.add_edge("prosecutor", "judge_aggregator")
    builder.add_edge("defense", "judge_aggregator")
    builder.add_edge("techlead", "judge_aggregator")

    def _route_after_judges(state: AgentState):
        if state.get("flags", {}).get("judge_output_invalid", False):
            return "retry_judge"
        return "chief_justice"

    builder.add_conditional_edges(
        "judge_aggregator",
        _route_after_judges,
        {"retry_judge": "retry_judge", "chief_justice": "chief_justice"},
    )
    builder.add_edge("retry_judge", "chief_justice")
    builder.add_edge("chief_justice", END)

    return builder.compile()


def _initial_state(repo_url: str, pdf_path: str, rubric_path: str, report_output_path: str) -> AgentState:
    return {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": load_rubric_dimensions(rubric_path),
        "evidences": {},
        "opinions": [],
        "node_errors": [],
        "flags": {},
        "report_output_path": report_output_path,
        "trace_url": None,
        "final_report_markdown": None,
        "final_report": None,
    }


def run_full_audit(
    repo_url: str,
    pdf_path: str,
    rubric_path: str = "rubric.json",
    report_output_path: str = "audit/report_onself_generated/report.md",
):
    graph = build_final_graph()
    return graph.invoke(_initial_state(repo_url, pdf_path, rubric_path, report_output_path))


def run_detective_graph(repo_url: str, pdf_path: str, rubric_path: str = "rubric.json"):
    # Backward-compatible entrypoint for interim tooling.
    return run_full_audit(repo_url, pdf_path, rubric_path=rubric_path)
