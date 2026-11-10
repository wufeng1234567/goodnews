"""Structured outputs expected from the LLM.

These models are *internal*: they are validated at the LLM boundary and then
merged into public API models. Keeping them separate prevents the model from
inventing server-owned fields such as evidence ids or timestamps.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.common import EvidenceStance, Verdict


class ClaimDraft(BaseModel):
    text: str = Field(min_length=2, max_length=600)
    entities: list[str] = Field(default_factory=list)
    importance: Literal["high", "medium", "low"] = "medium"


class ClaimExtractionOutput(BaseModel):
    claims: list[ClaimDraft] = Field(default_factory=list)


class GraphClaimCandidate(BaseModel):
    claim_id: str
    subject: str
    predicate: str
    object: str
    rationale: str = ""


class GraphCandidateOutput(BaseModel):
    candidates: list[GraphClaimCandidate] = Field(default_factory=list)


class ClaimAdjudication(BaseModel):
    claim_id: str
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceAssessment(BaseModel):
    evidence_id: str
    stance: EvidenceStance
    relevance: float = Field(default=0.5, ge=0, le=1)


class AdjudicationOutput(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    claim_verdicts: list[ClaimAdjudication] = Field(default_factory=list)
    evidence_assessments: list[EvidenceAssessment] = Field(default_factory=list)
    reasoning: str
