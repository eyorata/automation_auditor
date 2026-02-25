# Design Notes

## Decision 1: Typed Models Over Free Dicts
- Chosen: Pydantic `BaseModel` + TypedDict state.
- Why: strict schemas reduce malformed outputs and state ambiguity.
- Tradeoff: slightly more boilerplate for significantly better reliability.

## Decision 2: AST Verification Over Regex
- Chosen: parse Python AST for graph/state checks.
- Why: structural checks are resilient to formatting and alias changes.
- Tradeoff: more implementation effort than string matching.

## Decision 3: Sandboxed Repository Analysis
- Chosen: clone target repos into temporary directories and inspect only.
- Why: lowers risk from unknown repositories and avoids workspace pollution.
- Tradeoff: each run performs fresh clone work.

## Decision 4: Conditional Error Governance
- Chosen: non-happy paths are explicit graph routes.
- Why: no silent node failures; errors become traceable evidence.
- Implemented routes:
  - `repo/doc` node exceptions -> `node_errors` + error evidence
  - aggregator checks flags -> `error_collector` or `insufficient_evidence`

## Current Gaps
- Judicial nodes are not implemented yet.
- Chief Justice deterministic synthesis not implemented yet.
- End-to-end markdown report generation is not active yet.

## Near-Term Plan
1. Implement `src/nodes/judges.py` with distinct personas and structured outputs.
2. Implement `src/nodes/justice.py` with deterministic rule hierarchy.
3. Expand graph with judicial fan-out/fan-in and conditional retries.
4. Add generated audit markdown artifacts to `audit/` paths.

## Risk Notes
- External API variability: mitigate with validation and retry bounds.
- Evidence insufficiency: explicit flag path already added.
- Persona convergence risk: enforce prompt divergence and dissent capture in final phase.

