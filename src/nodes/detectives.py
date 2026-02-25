from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools.doc_tools import collect_doc_evidence
from src.tools.repo_tools import collect_repo_evidence


def repo_investigator_node(state: AgentState) -> Dict[str, Dict[str, List[Evidence]]]:
    evidences = collect_repo_evidence(repo_url=state["repo_url"])
    return {"evidences": evidences}


def doc_analyst_node(state: AgentState) -> Dict[str, Dict[str, List[Evidence]]]:
    doc_evidences = collect_doc_evidence(pdf_path=state["pdf_path"])
    return {"evidences": {"pdf_report_analysis": doc_evidences}}


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
    return {
        "evidences": {
            "evidence_aggregation": [
                Evidence(
                    goal="Aggregate detective outputs",
                    found=True,
                    content=str(summary),
                    location="graph/evidence_aggregator",
                    rationale="Fan-in point confirms collection across parallel detective branches.",
                    confidence=0.95,
                )
            ]
        }
    }

