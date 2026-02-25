# Architectural Overview

## System Goal
Automaton Auditor evaluates a target GitHub repository and an accompanying report using a multi-node LangGraph workflow designed for forensic evidence collection and governed decision-making.

## Core Topology

```text
START
  |---> RepoInvestigator ----\
  |---> DocAnalyst -----------> EvidenceAggregator ---> [conditional routes] ---> END
  |---> VisionInspector -----/
```

## Current Implemented Architecture
- Typed shared state with reducers in `src/state.py`
- Parallel detective fan-out in `src/graph.py`
- Evidence fan-in through `evidence_aggregator_node`
- Governed conditional edges:
  - error path to `error_collector_node`
  - low-evidence path to `insufficient_evidence_node`

## State Contracts
- `Evidence` (Pydantic): forensic artifact contract
- `JudicialOpinion` (Pydantic): judge output contract (for final phase)
- `AuditReport` (Pydantic): final report contract (for final phase)
- `AgentState` (TypedDict + reducers):
  - `evidences`: `operator.ior`
  - `opinions`: `operator.add`
  - `node_errors`: `operator.add`
  - `flags`: `operator.ior`

## Tooling Layer
- `src/tools/repo_tools.py`
  - sandboxed clone via `tempfile.TemporaryDirectory()`
  - git history extraction
  - AST graph/state structure analysis
  - URL validation + subprocess timeout/error handling
- `src/tools/doc_tools.py`
  - PDF ingestion and chunking
  - query helper for retrieval-like access
  - path-claim extraction and cross-reference helper

## Planned Final Extension

```text
START
  -> Detectives (parallel)
  -> EvidenceAggregator
  -> Judges (Prosecutor | Defense | TechLead in parallel)
  -> ChiefJustice (deterministic synthesis rules)
  -> END
```

Final phase adds judge persona nodes, deterministic synthesis rules, and markdown report serialization.

