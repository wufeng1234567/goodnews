"""LangGraph flow test with injected fakes: proves bounded evidence retry."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.config import Settings
from app.graph.builder import build_factcheck_graph
from app.graph.nodes import FactCheckNodes
from app.graph.state import FactCheckState
from app.llm.client import LLMMessage
from app.models.article import ArticleContent
from app.models.common import GraphVerificationStatus, Verdict
from app.models.factcheck import (
    Claim,
    Evidence,
    FactCheckRequest,
    GraphVerificationResult,
)
from app.models.llm import (
    AdjudicationOutput,
    ClaimAdjudication,
    ClaimDraft,
    ClaimExtractionOutput,
    EvidenceAssessment,
)


class FakeArticles:
    async def resolve(self, request: FactCheckRequest) -> ArticleContent:
        return ArticleContent(
            title="测试文章",
            text="埃菲尔铁塔位于柏林。这是一条用于测试的陈述。",
            source_name="测试",
            word_count=20,
        )


class FakeEvidence:
    def __init__(self) -> None:
        self.calls = 0

    async def retrieve(
        self, claims: list[Claim], queries: list[str], existing: list[Evidence]
    ) -> list[Evidence]:
        self.calls += 1
        if self.calls == 1:
            return []
        return [
            Evidence(
                id="ev-1",
                claim_ids=["c1"],
                title="测试证据",
                url="https://example.com/evidence",
                snippet="埃菲尔铁塔位于巴黎。",
                content_excerpt="埃菲尔铁塔位于巴黎。",
                source_name="测试来源",
                query=queries[0] if queries else "",
            )
        ]


class FakeGraph:
    def __init__(self) -> None:
        self.calls = 0

    async def verify(self, claims: list[Claim], round_number: int) -> GraphVerificationResult:
        self.calls += 1
        return GraphVerificationResult(
            status=GraphVerificationStatus.INSUFFICIENT,
            graph_entities=41,
            graph_relations=30,
            round=round_number,
        )


class FakeLLM:
    async def chat_json(
        self,
        messages: Sequence[LLMMessage],
        schema: type[Any],
        **kwargs: Any,
    ) -> Any:
        if schema is ClaimExtractionOutput:
            return ClaimExtractionOutput(
                claims=[ClaimDraft(text="埃菲尔铁塔位于柏林。", entities=["埃菲尔铁塔", "柏林"])]
            )
        if schema is AdjudicationOutput:
            return AdjudicationOutput(
                verdict=Verdict.PARTIALLY_TRUE,
                confidence=0.6,
                claim_verdicts=[
                    ClaimAdjudication(
                        claim_id="c1",
                        verdict=Verdict.PARTIALLY_TRUE,
                        confidence=0.6,
                        reasoning="存在冲突",
                        evidence_ids=["ev-1"],
                    )
                ],
                evidence_assessments=[
                    EvidenceAssessment(
                        evidence_id="ev-1",
                        stance="refutes",
                        relevance=0.9,
                    )
                ],
                reasoning="证据与主张存在冲突。",
            )
        raise AssertionError(f"unexpected schema {schema}")


async def test_graph_retries_evidence_then_adjudicates() -> None:
    evidence = FakeEvidence()
    graph = FakeGraph()
    nodes = FactCheckNodes(
        settings=Settings(),
        llm=FakeLLM(),
        articles=FakeArticles(),
        evidence=evidence,
        graph=graph,
    )
    compiled = build_factcheck_graph(nodes)
    initial = FactCheckState(
        request=FactCheckRequest(input_type="text", content="埃菲尔铁塔位于柏林。"),
        max_evidence_rounds=2,
    )
    raw = await compiled.ainvoke(initial, config={"recursion_limit": 30})
    state = FactCheckState.model_validate(raw)

    assert evidence.calls == 2
    assert graph.calls == 2
    assert state.evidence_round == 2
    assert state.verdict is not None
    assert state.verdict.evidence[0].stance.value == "refutes"
    # fetch, extract, retrieve(1), graph(1), retrieve(2), graph(2), adjudicate
    assert len(state.trace) == 7
