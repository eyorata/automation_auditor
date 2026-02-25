# Interim Submission Report

## Automaton Auditor - Digital Courtroom
Constitutional Multi-Agent Governance System

## 1. Project Overview
Automaton Auditor is an autonomous governance system for auditing a target GitHub repository and its associated PDF report using a structured LangGraph workflow.

The interim milestone prioritizes:
- Forensic evidence quality
- Typed state safety under parallel execution
- Sandboxed repository inspection
- Explicit non-happy-path governance

Current enforced capabilities:
- Parallel detective fan-out (`RepoInvestigator`, `DocAnalyst`, `VisionInspector` scaffold)
- Evidence fan-in through an aggregator node
- Typed contracts using Pydantic + reducer-safe `AgentState`
- Sandboxed clone and structural inspection tooling
- Conditional routing for node failure and low-evidence conditions

Core invariant (interim scope):
`START -> Detectives (parallel) -> EvidenceAggregator -> [ErrorCollector | InsufficientEvidence | END]`

## 2. Comparison and Improvement Notes
Compared with the earlier placeholder-style report and the stronger reference format, this report is upgraded in three ways:

1. Claim-to-code traceability: all major claims map to existing files/functions.
2. Scope correctness: implemented behavior is separated from final-phase plans.
3. Governance clarity: error paths and evidence-quality controls are explicit.

## 3. Architecture Decision Rationale

### A. Typed State with Pydantic + TypedDict + Reducers
Decision:
- Use Pydantic `BaseModel` contracts for domain objects.
- Use `TypedDict` for shared graph state with `Annotated` reducers.

Why:
- Prevents malformed payloads from silently propagating.
- Preserves correctness when parallel branches write to state.
- Increases reproducibility and audit traceability.

Implementation:
- `evidences`: `operator.ior`
- `opinions`: `operator.add`
- `node_errors`: `operator.add`
- `flags`: `operator.ior`

Trade-off:
- Slight verbosity versus free dicts, in exchange for much stronger reliability.

### B. AST Parsing Over Regex
Decision:
- Use Python AST to verify structure in graph and state files.

Why:
- Regex is brittle to formatting, aliasing, and multiline patterns.
- AST inspects semantics and wiring, not just text presence.

Implementation examples:
- Detect `StateGraph` builder assignment.
- Extract `add_edge` / `add_conditional_edges` patterns.
- Verify typed schema classes and reducer markers.

Trade-off:
- Small parsing overhead; acceptable for higher forensic confidence.

### C. Sandboxed Repository Cloning
Decision:
- Clone into `tempfile.TemporaryDirectory()` and inspect only.
- Use `subprocess.run` with return-code checks and timeout.
- Disallow unsafe execution patterns (`os.system` not used).

Why:
- Target repositories are untrusted input.
- Isolation prevents workspace pollution and reduces execution risk.

Trade-off:
- Fresh clone per run costs time but improves safety and determinism.

## 4. StateGraph Architecture (Interim Implemented)

Implemented nodes:
- `RepoInvestigator`
- `DocAnalyst`
- `VisionInspector` (implementation scaffold; execution optional)
- `EvidenceAggregator`
- `ErrorCollector`
- `InsufficientEvidence`

Flow diagram:
```text
START
  |---> RepoInvestigator ----\
  |---> DocAnalyst -----------> EvidenceAggregator ---> [conditional] ---> END
  |---> VisionInspector -----/                  |
                                                +--> ErrorCollector ---> END
                                                +--> InsufficientEvidence -> END
```

Data contracts on transitions:
- Detectives -> Aggregator: `Dict[str, List[Evidence]]`
- Aggregator -> conditional routes: flags + aggregated evidence
- Planned final (not yet implemented): Judges -> ChiefJustice -> `AuditReport`

## 5. Error Handling and Governance Controls
Implemented controls:
- Detective exceptions are captured as structured `Evidence`.
- Node failures are accumulated in `node_errors`.
- Aggregator sets flags:
  - `has_node_errors`
  - `insufficient_evidence`
- Conditional routing ensures graceful completion with governed non-happy paths.

Benefits:
- No silent failures
- Better debugging/auditability
- More deterministic behavior under partial failure

## 6. Forensic Tooling Snapshot
- `src/tools/repo_tools.py`
  - GitHub URL guardrails
  - sandboxed clone
  - git history extraction
  - AST graph/state analysis
  - timeout-aware subprocess execution
- `src/tools/doc_tools.py`
  - PDF ingestion + chunking
  - chunk query helper
  - claimed-path extraction
  - cross-reference helper against repo inventory evidence
- `src/nodes/detectives.py`
  - exception-safe detective nodes with structured evidence outputs

## 7. Known Gaps (Interim Accurate)
Not implemented yet:
- `src/nodes/judges.py` judicial persona layer
- `src/nodes/justice.py` deterministic chief-justice synthesis
- End-to-end markdown final audit report generation

## 8. Forward Plan (Toward Final Milestone)
1. Implement judge nodes (Prosecutor, Defense, TechLead) with structured `JudicialOpinion`.
2. Add retry path for malformed outputs and bounds/citation validation.
3. Implement deterministic synthesis rules:
   - Security override
   - Fact supremacy
   - Functionality weighting
   - Dissent requirement
   - Variance re-evaluation
4. Expand graph with judicial fan-out/fan-in and retry/error edges.
5. Serialize final `AuditReport` to markdown artifacts under `audit/`.

## 9. Risk Register
| Risk | Mitigation |
|---|---|
| Node failure during evidence collection | Catch exceptions, emit error evidence, route to `ErrorCollector`. |
| Insufficient evidence but high-confidence narrative | Evidence count checks and `InsufficientEvidence` route. |
| Hallucinated report path claims | Cross-reference claimed paths against repo inventory evidence. |
| Structural false positives | AST-first checks rather than regex-only matching. |

## 10. Conclusion
This interim submission is technically sound for the detective phase: typed, parallel, and safety-conscious. The architecture now documents not only the happy path but also governed failure handling, while clearly separating completed features from final-phase courtroom synthesis work.

