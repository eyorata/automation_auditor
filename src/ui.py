import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

from src.graph import run_full_audit
from src.nodes.judges import describe_llm_runtime
from src.tracing import configure_tracing, trace_url_from_env


def _load_default_rubric() -> str:
    path = Path("rubric.json")
    if not path.exists():
        return json.dumps({"dimensions": []}, indent=2)
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return json.dumps({"dimensions": []}, indent=2)


def _ensure_report_path(output_dir: str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return out / f"ui_audit_report_{stamp}.md"


def main() -> None:
    load_dotenv(override=True)
    st.set_page_config(page_title="Automaton Auditor UI", layout="wide")
    st.title("Automaton Auditor")
    st.caption("Audit repositories with dynamic rubric control.")

    tracing = configure_tracing()
    llm_runtime = describe_llm_runtime()

    with st.sidebar:
        st.subheader("Tracing")
        st.write(f"Enabled: `{tracing.get('enabled')}`")
        st.write(f"Project: `{tracing.get('project')}`")
        st.write(f"Trace URL: `{tracing.get('trace_url') or 'not set'}`")
        st.subheader("LLM Runtime")
        st.write(f"Provider: `{llm_runtime.get('provider')}`")
        st.write(f"Model: `{llm_runtime.get('model') or '-'}`")
        st.write(f"Base URL: `{llm_runtime.get('base_url') or '-'}`")

    repo_url = st.text_input("Repository URL", value="https://github.com/eyorata/automation_auditor.git")
    pdf_file = st.file_uploader("Upload Report PDF", type=["pdf"])
    output_dir = st.text_input("Output Directory", value="audit/generated")

    st.subheader("Rubric")
    use_default = st.checkbox("Use repository rubric.json", value=True)
    rubric_text = st.text_area(
        "Rubric JSON (editable for multi-project judging)",
        value=_load_default_rubric(),
        height=320,
        disabled=use_default,
    )

    if st.button("Run Audit", type="primary"):
        if not repo_url.strip():
            st.error("Repository URL is required.")
            return
        if pdf_file is None:
            st.error("Please upload a PDF report.")
            return

        with tempfile.TemporaryDirectory(prefix="automaton_auditor_ui_") as tmp:
            tmp_dir = Path(tmp)
            pdf_path = tmp_dir / "uploaded_report.pdf"
            pdf_path.write_bytes(pdf_file.getvalue())

            rubric_path = Path("rubric.json")
            if not use_default:
                try:
                    parsed = json.loads(rubric_text)
                    rubric_path = tmp_dir / "rubric.dynamic.json"
                    rubric_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
                except json.JSONDecodeError as exc:
                    st.error(f"Invalid rubric JSON: {exc}")
                    return

            report_path = _ensure_report_path(output_dir)
            with st.spinner("Running full audit graph..."):
                result = run_full_audit(
                    repo_url=repo_url.strip(),
                    pdf_path=str(pdf_path),
                    rubric_path=str(rubric_path),
                    report_output_path=str(report_path),
                    trace_url=trace_url_from_env(),
                )

            final_report = result.get("final_report")
            st.success("Audit completed.")
            st.write(f"Markdown report: `{report_path.as_posix()}`")

            if final_report:
                if hasattr(final_report, "model_dump"):
                    report_data = final_report.model_dump()
                else:
                    report_data = final_report
                st.subheader("Executive Summary")
                st.write(report_data.get("executive_summary", ""))
                st.write(f"Overall Score: **{report_data.get('overall_score', 'n/a')}**")
                st.subheader("Criteria")
                st.json(report_data.get("criteria", []), expanded=False)
            else:
                st.warning("No final_report returned; inspect node errors below.")

            st.subheader("Node Errors")
            st.json(result.get("node_errors", []))
            st.subheader("Flags")
            st.json(result.get("flags", {}))

            try:
                md = report_path.read_text(encoding="utf-8")
                st.subheader("Rendered Markdown Report")
                st.markdown(md)
                st.download_button(
                    "Download Markdown Report",
                    data=md.encode("utf-8"),
                    file_name=report_path.name,
                    mime="text/markdown",
                )
            except Exception:
                pass


if __name__ == "__main__":
    main()
