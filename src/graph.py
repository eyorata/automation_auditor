import json
from pathlib import Path
from typing import Dict, List

from langgraph.graph import END, START, StateGraph

from src.nodes.detectives import (
    doc_analyst_node,
    evidence_aggregator_node,
    repo_investigator_node,
    vision_inspector_node,
)
from src.state import AgentState


def load_rubric_dimensions(rubric_path: str) -> List[Dict]:
    path = Path(rubric_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("dimensions", [])


def build_interim_graph():
    builder = StateGraph(AgentState)

    builder.add_node("repo_investigator", repo_investigator_node)
    builder.add_node("doc_analyst", doc_analyst_node)
    builder.add_node("vision_inspector", vision_inspector_node)
    builder.add_node("evidence_aggregator", evidence_aggregator_node)

    # Detective fan-out
    builder.add_edge(START, "repo_investigator")
    builder.add_edge(START, "doc_analyst")
    builder.add_edge(START, "vision_inspector")

    # Detective fan-in
    builder.add_edge("repo_investigator", "evidence_aggregator")
    builder.add_edge("doc_analyst", "evidence_aggregator")
    builder.add_edge("vision_inspector", "evidence_aggregator")

    builder.add_edge("evidence_aggregator", END)
    return builder.compile()


def run_detective_graph(repo_url: str, pdf_path: str, rubric_path: str = "rubric.json"):
    graph = build_interim_graph()
    return graph.invoke(
        {
            "repo_url": repo_url,
            "pdf_path": pdf_path,
            "rubric_dimensions": load_rubric_dimensions(rubric_path),
            "evidences": {},
            "opinions": [],
            "final_report": None,
        }
    )

