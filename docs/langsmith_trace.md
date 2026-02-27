# LangSmith Trace

- Add these values in `.env`:
  - `LANGCHAIN_API_KEY=...`
  - `LANGCHAIN_TRACING_V2=true`
  - `LANGCHAIN_PROJECT=automation-auditor`
  - `LANGSMITH_TRACE_URL=...` (optional manual link field for submission docs)

- Run:
  - `uv run automation-auditor audit-snapshot --repo-url <repo> --pdf-path <pdf> --output-dir audit/generated`

- Expected trace coverage:
  - Detectives evidence collection
  - Parallel judges deliberation
  - Chief Justice deterministic synthesis

- Paste final link here before submission:
  - `ADD_YOUR_LANGSMITH_TRACE_URL_HERE`
