import os
from typing import Dict, List

from src.state import AgentState, JudicialOpinion


def _criteria(state: AgentState) -> List[Dict]:
    if state.get("rubric_dimensions"):
        return state["rubric_dimensions"]
    return [
        {"id": "git_forensic_analysis", "name": "Git Forensic Analysis"},
        {"id": "state_management_rigor", "name": "State Management Rigor"},
        {"id": "graph_orchestration", "name": "Graph Orchestration Architecture"},
        {"id": "safe_tool_engineering", "name": "Safe Tool Engineering"},
        {"id": "structured_output_enforcement", "name": "Structured Output Enforcement"},
        {"id": "judicial_nuance", "name": "Judicial Nuance and Dialectics"},
        {"id": "chief_justice_synthesis", "name": "Chief Justice Synthesis"},
        {"id": "theoretical_depth", "name": "Theoretical Depth"},
        {"id": "report_accuracy", "name": "Report Accuracy"},
        {"id": "swarm_visual", "name": "Architectural Diagram Analysis"},
    ]


def _evidence_snapshot(state: AgentState, limit: int = 16) -> str:
    rows: List[str] = []
    for bucket, items in state.get("evidences", {}).items():
        for item in items[:2]:
            rows.append(
                f"[{bucket}] goal={item.goal}; found={item.found}; location={item.location}; confidence={item.confidence}"
            )
            if len(rows) >= limit:
                return "\n".join(rows)
    return "\n".join(rows) if rows else "No evidence collected."


def _fallback_opinion(judge: str, criterion: Dict, state: AgentState) -> JudicialOpinion:
    has_errors = bool(state.get("flags", {}).get("has_node_errors", False))
    insufficient = bool(state.get("flags", {}).get("insufficient_evidence", False))
    base = 3
    if judge == "Prosecutor":
        score = 1 if has_errors else (2 if insufficient else base)
    elif judge == "Defense":
        score = 3 if insufficient else 4
    else:
        score = 2 if has_errors else (3 if insufficient else base)

    return JudicialOpinion(
        judge=judge,  # type: ignore[arg-type]
        criterion_id=criterion["id"],
        score=max(1, min(5, score)),
        argument=(
            f"{judge} fallback opinion generated without LLM call. "
            f"Flags considered: has_node_errors={has_errors}, insufficient_evidence={insufficient}."
        ),
        cited_evidence=list(state.get("evidences", {}).keys())[:4],
    )


def _judge_prompt(judge: str) -> str:
    if judge == "Prosecutor":
        return (
            "You are the Prosecutor judge. Be adversarial and conservative. "
            "Prioritize security and missing structure. Penalize unsupported claims."
        )
    if judge == "Defense":
        return (
            "You are the Defense judge. Reward implementation effort and architectural intent, "
            "while still grounding arguments in evidence."
        )
    return (
        "You are the TechLead judge. Prioritize maintainability, correctness, and practical operability. "
        "Balance risks with implementation reality."
    )


def _llm_provider() -> str | None:
    explicit = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if explicit in {"openai", "gemini"}:
        return explicit
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return None


def _call_llm_opinion(judge: str, criterion: Dict, state: AgentState) -> JudicialOpinion:
    from langchain_core.prompts import ChatPromptTemplate

    provider = _llm_provider()
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model, temperature=0.1)
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.1)
    else:
        raise RuntimeError("No supported LLM provider configured. Set OPENAI_API_KEY or GEMINI_API_KEY.")

    chain = ChatPromptTemplate.from_messages(
        [
            ("system", _judge_prompt(judge)),
            (
                "human",
                (
                    "Return exactly one JudicialOpinion for this criterion.\n"
                    "criterion_id: {criterion_id}\n"
                    "criterion_name: {criterion_name}\n"
                    "available_evidence:\n{evidence_snapshot}\n"
                    "Ensure cited_evidence uses evidence bucket keys."
                ),
            ),
        ]
    ) | llm.with_structured_output(JudicialOpinion)

    opinion = chain.invoke(
        {
            "criterion_id": criterion["id"],
            "criterion_name": criterion.get("name", criterion["id"]),
            "evidence_snapshot": _evidence_snapshot(state),
        }
    )
    opinion.judge = judge  # normalize persona source
    opinion.criterion_id = criterion["id"]
    return opinion


def _judge_node(state: AgentState, judge: str) -> Dict[str, object]:
    criteria = _criteria(state)
    outputs: List[JudicialOpinion] = []
    errors: List[str] = []
    can_call_llm = _llm_provider() is not None

    for criterion in criteria:
        try:
            opinion = _call_llm_opinion(judge, criterion, state) if can_call_llm else _fallback_opinion(
                judge, criterion, state
            )
            outputs.append(opinion)
        except Exception as exc:
            errors.append(f"{judge} failed on {criterion['id']}: {exc}")
            outputs.append(_fallback_opinion(judge, criterion, state))

    payload: Dict[str, object] = {"opinions": outputs}
    if errors:
        payload["node_errors"] = errors
        payload["flags"] = {"judge_output_invalid": True}
    return payload


def prosecutor_node(state: AgentState) -> Dict[str, object]:
    return _judge_node(state, "Prosecutor")


def defense_node(state: AgentState) -> Dict[str, object]:
    return _judge_node(state, "Defense")


def techlead_node(state: AgentState) -> Dict[str, object]:
    return _judge_node(state, "TechLead")


def retry_judge_node(state: AgentState) -> Dict[str, object]:
    # Deterministic fallback correction pass when structured outputs fail.
    if not state.get("flags", {}).get("judge_output_invalid", False):
        return {}
    corrected: List[JudicialOpinion] = []
    for criterion in _criteria(state):
        for judge in ("Prosecutor", "Defense", "TechLead"):
            corrected.append(_fallback_opinion(judge, criterion, state))
    return {"opinions": corrected, "flags": {"judge_output_invalid": False}}
