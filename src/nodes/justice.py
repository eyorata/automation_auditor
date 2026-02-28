from pathlib import Path
from statistics import mean
from typing import Dict, List

from src.state import AgentState, AuditReport, CriterionResult, JudicialOpinion


def _criteria_lookup(state: AgentState) -> Dict[str, Dict]:
    dims = state.get("rubric_dimensions", [])
    return {d["id"]: d for d in dims if isinstance(d, dict) and "id" in d}


def _by_criterion(opinions: List[JudicialOpinion]) -> Dict[str, List[JudicialOpinion]]:
    out: Dict[str, List[JudicialOpinion]] = {}
    for op in opinions:
        out.setdefault(op.criterion_id, []).append(op)
    return out


def _has_security_issue(state: AgentState, ops: List[JudicialOpinion]) -> bool:
    prosecutor_text = " ".join(op.argument.lower() for op in ops if op.judge == "Prosecutor")
    if any(term in prosecutor_text for term in ("security", "injection", "unsafe", "os.system")):
        return True
    for items in state.get("evidences", {}).values():
        for ev in items:
            content = (ev.content or "").lower()
            if "os.system(" in content:
                return True
    return False


def _defense_hallucination(ops: List[JudicialOpinion], state: AgentState) -> bool:
    defense_text = " ".join(op.argument.lower() for op in ops if op.judge == "Defense")
    if "metacognition" in defense_text and not state.get("evidences", {}).get("pdf_report_analysis"):
        return True
    return False


def _choose_final_score(criterion_id: str, ops: List[JudicialOpinion], state: AgentState) -> int:
    scores = [op.score for op in ops]
    if not scores:
        return 1
    prosecutor = next((op for op in ops if op.judge == "Prosecutor"), None)
    defense = next((op for op in ops if op.judge == "Defense"), None)
    techlead = next((op for op in ops if op.judge == "TechLead"), None)

    # Rule of Security
    if _has_security_issue(state, ops):
        return min(3, techlead.score if techlead else int(round(mean(scores))))

    # Rule of Evidence (fact supremacy over unsupported optimism)
    if defense and _defense_hallucination(ops, state):
        scores = [s for s in scores if s != defense.score] or scores

    # Rule of Functionality (tech lead weighted on architecture criterion)
    if criterion_id == "graph_orchestration" and techlead:
        return int(max(1, min(5, round((techlead.score * 0.6) + (mean(scores) * 0.4)))))

    if prosecutor and defense and abs(prosecutor.score - defense.score) > 2 and techlead:
        # variance re-evaluation -> tie-break toward tech lead
        return techlead.score

    return int(max(1, min(5, round(mean(scores)))))


def _remediation_for(criterion_id: str) -> str:
    mapping = {
        "git_forensic_analysis": "Use smaller, atomic commits and descriptive messages in the repository history.",
        "state_management_rigor": "Refine src/state.py to ensure reducer annotations cover all parallel write paths.",
        "graph_orchestration": "Ensure dual fan-out/fan-in in src/graph.py and conditional error edges are complete.",
        "safe_tool_engineering": "Strengthen subprocess error handling and URL validation in src/tools/repo_tools.py.",
        "structured_output_enforcement": "Use strict Pydantic schema validation and retries in src/nodes/judges.py.",
        "judicial_nuance": "Increase persona divergence in system prompts and preserve evidence-grounded arguments.",
        "chief_justice_synthesis": "Expand deterministic rules in src/nodes/justice.py and document precedence clearly.",
        "theoretical_depth": "Add deeper architectural explanations in reports/final_report.pdf and linked markdown.",
        "report_accuracy": "Cross-check all report file claims against repo evidence before finalizing report text.",
        "swarm_visual": "Include precise fan-out/fan-in diagrams in reports and ensure they match actual graph wiring.",
    }
    return mapping.get(criterion_id, "Provide criterion-specific remediation in the referenced implementation file.")


def _to_markdown(report: AuditReport) -> str:
    lines = [
        "# Audit Report",
        "",
        "## Executive Summary",
        "",
        report.executive_summary,
        "",
        f"- Repo: `{report.repo_url}`",
        f"- Overall Score: **{report.overall_score:.2f}/5.00**",
        "",
        "## Criterion Breakdown",
        "",
    ]
    for c in report.criteria:
        lines.extend([f"### {c.dimension_name} (`{c.dimension_id}`)", "", f"- Final Score: **{c.final_score}/5**"])
        for op in c.judge_opinions:
            lines.extend(
                [
                    f"- {op.judge}: **{op.score}/5**",
                    f"  - Argument: {op.argument}",
                    f"  - Cited Evidence: {', '.join(op.cited_evidence) if op.cited_evidence else 'None'}",
                ]
            )
        if c.dissent_summary:
            lines.append(f"- Dissent: {c.dissent_summary}")
        lines.extend(["- Remediation:", f"  - {c.remediation}", ""])
    lines.extend(["## Remediation Plan", "", report.remediation_plan, ""])
    return "\n".join(lines)


def chief_justice_node(state: AgentState) -> Dict[str, object]:
    opinions = state.get("opinions", [])
    by_dim = _by_criterion(opinions)
    dims = _criteria_lookup(state)
    criteria_results: List[CriterionResult] = []

    for dim_id, ops in by_dim.items():
        scores = [op.score for op in ops]
        final_score = _choose_final_score(dim_id, ops, state)
        dissent = None
        if scores and (max(scores) - min(scores) > 2):
            dissent = (
                "High score variance detected; Chief Justice prioritized deterministic rules "
                "and evidence-grounded tie-break decisions."
            )
        criteria_results.append(
            CriterionResult(
                dimension_id=dim_id,
                dimension_name=dims.get(dim_id, {}).get("name", dim_id),
                final_score=final_score,
                judge_opinions=ops,
                dissent_summary=dissent,
                remediation=_remediation_for(dim_id),
            )
        )

    overall = mean([c.final_score for c in criteria_results]) if criteria_results else 1.0
    has_repo_error = bool(state.get("evidences", {}).get("repo_investigator_error"))
    has_git_evidence = bool(state.get("evidences", {}).get("git_forensic_analysis"))
    degraded_run = has_repo_error or (not has_git_evidence)

    exec_summary = (
        "Chief Justice synthesized parallel judicial opinions using deterministic rules "
        "including security override, fact supremacy, and variance re-evaluation."
    )
    if degraded_run:
        exec_summary = (
            "[RUN QUALITY WARNING] Repository forensic evidence is incomplete due to clone/tool errors. "
            "Scores may be conservative and less reliable until a clean run is completed.\n\n"
            + exec_summary
        )

    report = AuditReport(
        repo_url=state["repo_url"],
        executive_summary=exec_summary,
        overall_score=float(round(overall, 2)),
        criteria=criteria_results,
        remediation_plan=(
            "Prioritize structural reliability in graph orchestration, schema enforcement in judge outputs, "
            "and report/code cross-reference consistency."
        ),
    )

    markdown = _to_markdown(report)
    out_path = Path(state.get("report_output_path") or "audit/report_onself_generated/report.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    return {"final_report": report, "final_report_markdown": markdown}
