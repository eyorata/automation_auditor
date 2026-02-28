# Automaton Auditor - Digital Courtroom (Final Delivery)

LangGraph-based autonomous governance system for auditing a target GitHub repository plus an accompanying PDF report.

## What This Repository Implements

- Typed governance state and contracts in `src/state.py`
- Forensic repo analysis tools in `src/tools/repo_tools.py`
- PDF ingestion, claim extraction, and image extraction in `src/tools/doc_tools.py`
- Detective nodes in `src/nodes/detectives.py`
- Judicial layer in `src/nodes/judges.py` using `.with_structured_output(JudicialOpinion)`
- Deterministic synthesis in `src/nodes/justice.py`
- Complete orchestrated graph in `src/graph.py`
- CLI runner in `src/cli.py`

## Architecture

```mermaid
flowchart TD
    S([START])
    RI[RepoInvestigator]
    DA[DocAnalyst]
    VI[VisionInspector]
    EA[EvidenceAggregator]
    JD[JudgeDispatch]
    P[Prosecutor]
    D[Defense]
    T[TechLead]
    JA[JudgeAggregator]
    RJ[RetryJudge]
    CJ[ChiefJustice]
    EC[ErrorCollector]
    IE[InsufficientEvidence]
    E([END])

    S --> RI
    S --> DA
    S --> VI
    RI --> EA
    DA --> EA
    VI --> EA
    EA -->|node error| EC
    EA -->|insufficient evidence| IE
    EA -->|ready| JD
    JD --> P
    JD --> D
    JD --> T
    P --> JA
    D --> JA
    T --> JA
    JA -->|invalid output| RJ
    JA -->|valid output| CJ
    RJ --> CJ
    EC --> RJ
    IE --> RJ
    CJ --> E
```

## Setup

1. Install dependencies with uv:

```bash
uv sync
```

2. Configure environment:

```bash
cp .env.example .env
```

3. Set at least:
- local model (recommended for offline use):
  - `LLM_PROVIDER=local`
  - `LLM_URL=http://127.0.0.1:1234/v1`
  - `LLM_MODEL=qwen2.5-7b-instruct`
  - optional: `LLM_API_KEY=lm-studio`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`
- one judge provider key:
  - `OPENAI_API_KEY` (with `OPENAI_MODEL`)
  - or `GEMINI_API_KEY` (with `GEMINI_MODEL`)
- provider selector (local-only runtime): `LLM_PROVIDER=local`
- enforce local-only fail-fast behavior: `LLM_STRICT_LOCAL=true`
- `LANGCHAIN_API_KEY` and `LANGCHAIN_TRACING_V2=true` for LangSmith tracing

## Run

Run a full audit and produce output artifacts:

```bash
uv run automation-auditor audit-snapshot \
  --repo-url https://github.com/owner/repo.git \
  --pdf-path reports/final_report.pdf \
  --output-dir audit/generated
```

Outputs:
- Timestamped JSON run result
- Snapshot markdown
- Rendered audit report markdown (serialization of `AuditReport`)

## Web UI (Dynamic Rubrics)

Launch the UI:

```bash
uv run streamlit run src/ui.py
```

What the UI supports:
- Input target repository URL
- Upload report PDF
- Edit rubric JSON dynamically (or use `rubric.json`)
- Run full audit graph and view final results
- Download rendered markdown report

## Required Delivery Artifacts

- Final PDF report: `reports/final_report.pdf`
- Generated markdown reports:
  - `audit/report_onself_generated/`
  - `audit/report_onpeer_generated/`
  - `audit/report_bypeer_received/`
- Rubric constitution: `rubric.json`
- Dependency lock: `uv.lock`

## LangSmith Trace

- Set:
  - `LANGCHAIN_API_KEY`
  - `LANGCHAIN_TRACING_V2=true`
  - `LANGCHAIN_PROJECT=automation-auditor`
- Optional: set `LANGSMITH_TRACE_URL` to store the share link in generated snapshot metadata.
- After running `audit-snapshot`, include your trace link in submission notes and `docs/langsmith_trace.md`.
