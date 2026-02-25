import re
from pathlib import Path
from typing import List

from pypdf import PdfReader

from src.state import Evidence


def ingest_pdf(path: str, chunk_size: int = 1600, overlap: int = 200) -> List[str]:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks: List[str] = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(text), step):
        chunks.append(text[i : i + chunk_size])
    return chunks


def query_chunks(chunks: List[str], question: str, top_k: int = 3) -> List[str]:
    keywords = [k.lower() for k in re.findall(r"[A-Za-z]{4,}", question)]
    scored = []
    for chunk in chunks:
        lower = chunk.lower()
        score = sum(lower.count(k) for k in keywords)
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for s, c in scored[:top_k] if s > 0] or chunks[:top_k]


def extract_claimed_paths(text: str) -> List[str]:
    seen = set()
    paths: List[str] = []
    for match in re.finditer(r"(src/[A-Za-z0-9_./-]+\.py|reports/[A-Za-z0-9_./-]+\.pdf)", text):
        p = match.group(1)
        if p not in seen:
            seen.add(p)
            paths.append(p)
    return paths


def collect_doc_evidence(pdf_path: str) -> List[Evidence]:
    chunks = ingest_pdf(pdf_path)
    joined = " ".join(chunks)
    claimed_paths = extract_claimed_paths(joined)

    depth_terms = ["dialectical synthesis", "fan-in", "fan-out", "metacognition", "state synchronization"]
    term_hits = {term: (term in joined.lower()) for term in depth_terms}

    return [
        Evidence(
            goal="Check theoretical depth terms in report",
            found=any(term_hits.values()),
            content=str(term_hits),
            location=pdf_path,
            rationale="Scanned report text for required conceptual vocabulary.",
            confidence=0.75,
        ),
        Evidence(
            goal="Extract file path claims for repo cross-reference",
            found=len(claimed_paths) > 0,
            content="\n".join(claimed_paths),
            location=pdf_path,
            rationale="File paths in report are needed to detect hallucinated references.",
            confidence=0.8,
        ),
    ]

