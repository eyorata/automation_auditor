# Audit Snapshot

- Generated UTC: `2026-02-26T17:21:33.306431+00:00`
- Repo URL: `https://github.com/eyorata/automation_auditor.git`
- PDF Path: `reports/Interim Submission Report.pdf`
- Raw JSON: `audit/generated/audit_snapshot_20260226T172130Z.json`

## Architecture Diagram

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

## Runtime Summary

- Total Evidence Items: **9**
- Average Confidence: **0.906**
- Flags: `{'vision_inspector_failed': True, 'insufficient_evidence': False, 'has_node_errors': True}`
- Node Errors: `1`

## Evidence Counts By Bucket

- `error_collection`: 1
- `evidence_aggregation`: 1
- `git_forensic_analysis`: 1
- `graph_orchestration`: 1
- `pdf_report_analysis`: 2
- `repo_file_inventory`: 1
- `state_management_rigor`: 1
- `vision_inspector_error`: 1
