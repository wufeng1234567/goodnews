"""The graph must be able to veto an over-confident LLM verdict."""

from app.graph.guardrails import apply_adjudication_guardrails
from app.models.common import GraphMatchStatus, GraphVerificationStatus, Verdict
from app.models.factcheck import Claim, GraphMatch, GraphVerificationResult
from app.models.llm import AdjudicationOutput, ClaimAdjudication


def _claim() -> Claim:
    return Claim(id="c1", text="埃菲尔铁塔位于柏林。")


def _adjudication(verdict: Verdict = Verdict.TRUE) -> AdjudicationOutput:
    return AdjudicationOutput(
        verdict=verdict,
        confidence=0.95,
        claim_verdicts=[
            ClaimAdjudication(
                claim_id="c1",
                verdict=verdict,
                confidence=0.95,
                reasoning="test",
                evidence_ids=[],
            )
        ],
        reasoning="test reasoning",
    )


def test_graph_contradiction_blocks_true() -> None:
    graph = GraphVerificationResult(
        status=GraphVerificationStatus.CONTRADICTED,
        matches=[
            GraphMatch(
                claim_id="c1",
                subject="埃菲尔铁塔",
                predicate="located_in",
                claimed_object="柏林",
                graph_object="巴黎",
                status=GraphMatchStatus.CONTRADICTED,
            )
        ],
        graph_entities=41,
        graph_relations=30,
    )
    output, notes = apply_adjudication_guardrails(_adjudication(), [_claim()], [], graph)
    assert output.verdict is not Verdict.TRUE
    assert output.verdict is Verdict.FALSE
    assert notes


def test_no_evidence_and_empty_graph_becomes_insufficient() -> None:
    graph = GraphVerificationResult(
        status=GraphVerificationStatus.INSUFFICIENT,
        graph_entities=0,
        graph_relations=0,
    )
    output, _ = apply_adjudication_guardrails(_adjudication(), [_claim()], [], graph)
    assert output.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert output.confidence <= 0.25


def test_missing_claim_assessment_is_added() -> None:
    graph = GraphVerificationResult(status=GraphVerificationStatus.INSUFFICIENT)
    output = AdjudicationOutput(
        verdict=Verdict.INSUFFICIENT_EVIDENCE,
        confidence=0.3,
        claim_verdicts=[],
        reasoning="no data",
    )
    constrained, _ = apply_adjudication_guardrails(output, [_claim()], [], graph)
    assert len(constrained.claim_verdicts) == 1
    assert constrained.claim_verdicts[0].claim_id == "c1"
