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
    if explicit and explicit != "local":
        # Hard guard: only local is supported.
        return None
    if os.getenv("LLM_URL") and os.getenv("LLM_MODEL"):
        return "local"
    return None


def _strict_local_only() -> bool:
    return (os.getenv("LLM_STRICT_LOCAL", "true").strip().lower() not in {"0", "false", "no"})


def describe_llm_runtime() -> Dict[str, str]:
    provider = _llm_provider() or "fallback"
    if provider == "local":
        return {
            "provider": "local",
            "model": os.getenv("LLM_MODEL", ""),
            "base_url": os.getenv("LLM_URL", ""),
        }
    return {
        "provider": "fallback",
        "model": "",
        "base_url": "",
        "strict_local_only": str(_strict_local_only()).lower(),
    }


def _call_llm_opinion(judge: str, criterion: Dict, state: AgentState) -> JudicialOpinion:
    from langchain_core.prompts import ChatPromptTemplate

    provider = _llm_provider()
    if provider == "local":
        from langchain_openai import ChatOpenAI

        llm_url = os.getenv("LLM_URL", "http://127.0.0.1:1234/v1")
        llm_model = os.getenv("LLM_MODEL", "qwen2.5-7b-instruct")
        llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "800"))
        llm = ChatOpenAI(
            base_url=llm_url,
            api_key=os.getenv("LLM_API_KEY", "lm-studio"),
            model=llm_model,
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
        )
    else:
        raise RuntimeError(
            "Local LLM required. Set LLM_URL and LLM_MODEL (and optionally LLM_API_KEY)."
        )

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


def _normalize_opinion(raw: object, judge: str, criterion_id: str) -> JudicialOpinion:
    # Some model backends return wrapper objects that contain parsed output.
    if isinstance(raw, JudicialOpinion):
        opinion = raw
    elif isinstance(raw, dict):
        opinion = JudicialOpinion.model_validate(raw)
    elif hasattr(raw, "parsed"):
        parsed = getattr(raw, "parsed")
        if isinstance(parsed, JudicialOpinion):
            opinion = parsed
        elif isinstance(parsed, dict):
            opinion = JudicialOpinion.model_validate(parsed)
        else:
            raise TypeError(f"Unsupported parsed payload type: {type(parsed)!r}")
    else:
        raise TypeError(f"Unsupported judge output type: {type(raw)!r}")

    opinion.judge = judge  # normalize source persona
    opinion.criterion_id = criterion_id
    return opinion


def _judge_node(state: AgentState, judge: str) -> Dict[str, object]:
    criteria = _criteria(state)
    outputs: List[JudicialOpinion] = []
    errors: List[str] = []
    can_call_llm = _llm_provider() == "local"

    if not can_call_llm and _strict_local_only():
        return {
            "node_errors": [
                (
                    "Local-only mode is enabled, but local LLM is not configured. "
                    "Set LLM_PROVIDER=local with LLM_URL and LLM_MODEL."
                )
            ],
            "flags": {"has_node_errors": True, "judge_output_invalid": True},
        }

    for criterion in criteria:
        try:
            if can_call_llm:
                raw = _call_llm_opinion(judge, criterion, state)
                opinion = _normalize_opinion(raw, judge=judge, criterion_id=criterion["id"])
            else:
                opinion = _fallback_opinion(judge, criterion, state)
            outputs.append(opinion)
        except Exception as exc:
            errors.append(f"{judge} failed on {criterion['id']}: {exc}")
            if _strict_local_only():
                return {
                    "node_errors": errors,
                    "flags": {"has_node_errors": True, "judge_output_invalid": True},
                }
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
