import os
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback for minimal runtime environments
    def load_dotenv() -> bool:
        return False


def configure_tracing() -> dict:
    load_dotenv()
    os.environ.setdefault("LANGCHAIN_PROJECT", "automation-auditor")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    return {
        "enabled": os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true",
        "project": os.getenv("LANGCHAIN_PROJECT", "automation-auditor"),
        "trace_url": os.getenv("LANGSMITH_TRACE_URL", ""),
    }


def trace_url_from_env() -> Optional[str]:
    url = (os.getenv("LANGSMITH_TRACE_URL") or "").strip()
    return url or None
