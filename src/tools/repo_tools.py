import ast
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

from src.state import Evidence


def _run(cmd: List[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        capture_output=True,
        timeout=45,
    )


def clone_repo(repo_url: str, destination: Path) -> Path:
    if not re.match(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$", repo_url):
        raise ValueError("Unsupported repo URL format. Expected a GitHub HTTPS URL.")
    destination.mkdir(parents=True, exist_ok=True)
    repo_path = destination / "target_repo"
    result = _run(["git", "clone", "--depth", "100", repo_url, str(repo_path)])
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "Authentication failed" in stderr or "Repository not found" in stderr:
            raise RuntimeError(f"git clone auth/repo error: {stderr}")
        raise RuntimeError(f"git clone failed: {stderr}")
    return repo_path


def extract_git_history(path: str) -> List[Dict[str, str]]:
    repo_path = Path(path)
    result = _run(
        ["git", "log", "--pretty=format:%H|%aI|%s", "--reverse"],
        cwd=repo_path,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git log failed: {result.stderr.strip()}")

    commits: List[Dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("|", maxsplit=2)
        if len(parts) != 3:
            continue
        commits.append(
            {"hash": parts[0].strip(), "timestamp": parts[1].strip(), "message": parts[2].strip()}
        )
    return commits


def _find_builder_variable(tree: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            fn_name = getattr(call.func, "id", None) or getattr(call.func, "attr", None)
            if fn_name == "StateGraph" and node.targets and isinstance(node.targets[0], ast.Name):
                return node.targets[0].id
    return None


def analyze_graph_structure(path: str) -> Dict[str, object]:
    graph_file = Path(path) / "src" / "graph.py"
    if not graph_file.exists():
        return {"found_graph_file": False, "error": "src/graph.py not found"}

    source = graph_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    builder_name = _find_builder_variable(tree)

    add_edge_calls: List[List[str]] = []
    add_conditional_calls: List[str] = []
    if builder_name:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = getattr(node.func.value, "id", None)
                if owner != builder_name:
                    continue
                if node.func.attr == "add_edge" and len(node.args) >= 2:
                    src = ast.unparse(node.args[0]).strip("\"'")
                    dst = ast.unparse(node.args[1]).strip("\"'")
                    add_edge_calls.append([src, dst])
                if node.func.attr == "add_conditional_edges":
                    add_conditional_calls.append(ast.unparse(node))

    out_degree: Dict[str, int] = {}
    for src, _ in add_edge_calls:
        out_degree[src] = out_degree.get(src, 0) + 1

    return {
        "found_graph_file": True,
        "builder_name": builder_name,
        "edges": add_edge_calls,
        "conditional_edges_count": len(add_conditional_calls),
        "fan_out_nodes": [n for n, degree in out_degree.items() if degree > 1],
        "has_parallel_pattern": any(degree > 1 for degree in out_degree.values()),
    }


def analyze_state_structure(path: str) -> Dict[str, object]:
    state_file = Path(path) / "src" / "state.py"
    if not state_file.exists():
        return {"found_state_file": False, "error": "src/state.py not found"}

    source = state_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    base_models: List[str] = []
    typed_dicts: List[str] = []
    reducers_detected = {"operator.add": "operator.add" in source, "operator.ior": "operator.ior" in source}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = [getattr(base, "id", getattr(base, "attr", "")) for base in node.bases]
            if "BaseModel" in base_names:
                base_models.append(node.name)
            if "TypedDict" in base_names:
                typed_dicts.append(node.name)

    return {
        "found_state_file": True,
        "base_models": base_models,
        "typed_dicts": typed_dicts,
        "reducers_detected": reducers_detected,
    }


def list_repo_files(path: str) -> List[str]:
    root = Path(path)
    return [str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()]


def collect_repo_evidence(repo_url: str) -> Dict[str, List[Evidence]]:
    with tempfile.TemporaryDirectory(prefix="automaton_auditor_") as tmp:
        repo_path = clone_repo(repo_url=repo_url, destination=Path(tmp))

        commits = extract_git_history(str(repo_path))
        graph = analyze_graph_structure(str(repo_path))
        state = analyze_state_structure(str(repo_path))
        files = list_repo_files(str(repo_path))

        return {
            "git_forensic_analysis": [
                Evidence(
                    goal="Assess iterative git progression",
                    found=len(commits) > 0,
                    content=json.dumps(commits[:15], indent=2),
                    location=".git/log",
                    rationale="Collected commit hash, timestamp, and message in reverse order.",
                    confidence=0.9,
                )
            ],
            "graph_orchestration": [
                Evidence(
                    goal="Verify fan-out/fan-in graph structure",
                    found=bool(graph.get("found_graph_file")),
                    content=json.dumps(graph, indent=2),
                    location="src/graph.py",
                    rationale="AST analysis of StateGraph builder edge topology.",
                    confidence=0.85,
                )
            ],
            "state_management_rigor": [
                Evidence(
                    goal="Verify typed state with reducers",
                    found=bool(state.get("found_state_file")),
                    content=json.dumps(state, indent=2),
                    location="src/state.py",
                    rationale="AST scan of BaseModel/TypedDict definitions and reducer usage.",
                    confidence=0.9,
                )
            ],
            "repo_file_inventory": [
                Evidence(
                    goal="Enumerate repository files for cross-reference",
                    found=True,
                    content=json.dumps(files, indent=2),
                    location="/",
                    rationale="File inventory supports report path verification.",
                    confidence=1.0,
                )
            ],
        }


def classify_confidence_tier(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.65:
        return "medium"
    return "low"
