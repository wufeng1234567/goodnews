"""Deterministic guardrails applied after the adjudication LLM returns.

The LLM is useful for synthesis, but it must not be allowed to:
* declare a claim true with zero evidence;
* override a manually confirmed graph contradiction;
* imply that an empty/insufficient graph verified anything.

These checks are code, not prompt-only, so they are easy to test and reason about.
"""

from __future__ import annotations

from app.models.common import GraphMatchStatus, GraphVerificationStatus, Verdict
from app.models.factcheck import Claim, Evidence, GraphVerificationResult
from app.models.llm import AdjudicationOutput


def apply_adjudication_guardrails(
    adjudication: AdjudicationOutput,
    claims: list[Claim],
    evidence: list[Evidence],
    graph: GraphVerificationResult,
) -> tuple[AdjudicationOutput, list[str]]:
    """Return a constrained adjudication plus human-readable adjustment notes."""
    output = adjudication.model_copy(deep=True)
    notes: list[str] = []

    if not claims:
        output.verdict = Verdict.INSUFFICIENT_EVIDENCE
        output.confidence = min(output.confidence, 0.2)
        notes.append("未抽取到可核查主张，整体降级为证据不足。")
        return output, notes

    evidence_claim_ids: set[str] = set()
    for item in evidence:
        evidence_claim_ids.update(item.claim_ids)

    graph_supported_ids = {
        match.claim_id
        for match in graph.matches
        if match.status is GraphMatchStatus.SUPPORTED
    }
    graph_contradicted_ids = {
        match.claim_id
        for match in graph.matches
        if match.status is GraphMatchStatus.CONTRADICTED
    }
    all_claim_ids = {claim.id for claim in claims}
    unsupported_ids = all_claim_ids - evidence_claim_ids - graph_supported_ids

    # Rule 1: with no web evidence, only a confirmed graph relation can carry
    # the verdict. A contradiction is itself graph evidence and must proceed to
    # Rule 2 rather than being prematurely downgraded to insufficient.
    if not evidence and graph.status is GraphVerificationStatus.INSUFFICIENT:
        output.verdict = Verdict.INSUFFICIENT_EVIDENCE
        output.confidence = min(output.confidence, 0.25)
        notes.append("没有检索到可用证据，图谱也未给出有效关系，结论降级为证据不足。")

    # Rule 2: a graph contradiction can never produce an overall TRUE verdict.
    if graph_contradicted_ids and output.verdict is Verdict.TRUE:
        surviving_true_claims = [
            item
            for item in output.claim_verdicts
            if item.claim_id not in graph_contradicted_ids
            and item.claim_id in graph_supported_ids.union(evidence_claim_ids)
            and item.verdict is Verdict.TRUE
        ]
        output.verdict = (
            Verdict.PARTIALLY_TRUE if surviving_true_claims else Verdict.FALSE
        )
        output.confidence = min(output.confidence, 0.75)
        notes.append("知识图谱中存在与主张冲突的人工确认关系，已拦截整体 true 结论。")

    # Rule 3: unresolved claims are not enough for an overall TRUE verdict.
    if output.verdict is Verdict.TRUE and unsupported_ids:
        output.verdict = Verdict.PARTIALLY_TRUE
        output.confidence = min(output.confidence, 0.6)
        notes.append("部分主张没有检索证据或图谱支持，整体不能判定为完全真实。")

    # Rule 4: an insufficient graph cannot be presented as graph-backed proof.
    if graph.status is GraphVerificationStatus.INSUFFICIENT:
        output.confidence = min(output.confidence, 0.7)
        notes.append("知识图谱未提供有效关系；本结论仅依据检索证据，不包含图谱推断。")

    # Rule 5: ensure every claim has an explicit per-claim result.
    existing_claim_ids = {item.claim_id for item in output.claim_verdicts}
    for claim in claims:
        if claim.id not in existing_claim_ids:
            from app.models.llm import ClaimAdjudication

            output.claim_verdicts.append(
                ClaimAdjudication(
                    claim_id=claim.id,
                    verdict=Verdict.INSUFFICIENT_EVIDENCE,
                    confidence=0.0,
                    reasoning="模型未返回该主张的独立判断，按证据不足处理。",
                    evidence_ids=[],
                )
            )
            notes.append(f"主张 {claim.id} 缺少独立判断，已按证据不足处理。")

    output.confidence = round(max(0.0, min(output.confidence, 1.0)), 3)
    return output, notes
