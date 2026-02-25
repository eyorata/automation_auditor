# Automaton Auditor (Week 2 Interim)

This repository contains the interim implementation of a LangGraph-based forensic auditor swarm.

## Implemented interim scope

- Typed state schema in `src/state.py` using Pydantic and `TypedDict` with reducers.
- Forensic repo tools in `src/tools/repo_tools.py`:
  - sandboxed clone via `tempfile.TemporaryDirectory()`
  - git history extraction
  - AST-based graph and state analysis
  - URL validation, timeout-bounded subprocess execution, and auth-aware clone errors
- PDF tooling in `src/tools/doc_tools.py`:
  - PDF ingestion
  - chunked querying utility
  - report file-claim extraction
  - claimed-path cross-reference helper against repo inventory
- Detective nodes in `src/nodes/detectives.py`:
  - `repo_investigator_node`
  - `doc_analyst_node`
  - `vision_inspector_node` (scaffolded implementation)
  - `evidence_aggregator_node`
  - `error_collector_node`
  - `insufficient_evidence_node`
- Partial graph in `src/graph.py` with detective fan-out/fan-in.
  - conditional edges for error collection and insufficient evidence handling

## Setup

1. Install `uv` if needed.
2. Create and sync environment:

```bash
uv sync
```

3. Configure environment variables:

```bash
cp .env.example .env
```

## Run detective graph

```bash
uv run python -c "from src.graph import run_detective_graph; import json; result = run_detective_graph('https://github.com/owner/repo.git', 'reports/interim_report.pdf'); print(json.dumps(result, default=str, indent=2))"
```

## Cool Feature: Audit Snapshot Generator

Generate a timestamped JSON result and a readable markdown snapshot (includes Mermaid architecture and evidence summary):

```bash
uv run automation-auditor audit-snapshot --repo-url https://github.com/owner/repo.git --pdf-path reports/interim_report.pdf
```

Default output directory:
- `audit/generated/`

## Required artifacts

- Interim report PDF is committed at `reports/interim_report.pdf`.
- Rubric constitution is in `rubric.json`.
