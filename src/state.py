import operator
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Evidence(BaseModel):
    goal: str = Field()
    found: bool = Field(description="Whether the artifact exists.")
    content: Optional[str] = Field(default=None)
    location: str = Field(description="File path, commit hash, or scope.")
    rationale: str = Field(description="Forensic rationale for this evidence.")
    confidence: float = Field(ge=0.0, le=1.0)


class JudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(ge=1, le=5)
    argument: str
    cited_evidence: List[str]


class CriterionResult(BaseModel):
    dimension_id: str
    dimension_name: str
    final_score: int = Field(ge=1, le=5)
    judge_opinions: List[JudicialOpinion]
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Required when score variance exceeds 2.",
    )
    remediation: str = Field(description="Specific file-level remediation steps.")


class AuditReport(BaseModel):
    repo_url: str
    executive_summary: str
    overall_score: float = Field(ge=1.0, le=5.0)
    criteria: List[CriterionResult]
    remediation_plan: str


class AgentState(TypedDict):
    repo_url: str
    pdf_path: str
    rubric_dimensions: List[Dict]
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior]
    opinions: Annotated[List[JudicialOpinion], operator.add]
    node_errors: Annotated[List[str], operator.add]
    flags: Annotated[Dict[str, bool], operator.ior]
    final_report: Optional[AuditReport]
