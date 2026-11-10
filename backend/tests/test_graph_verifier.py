"""Graph verification must only use exact Neo4j relations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.knowledge_graph.verifier import GraphVerifier
from app.llm.client import LLMMessage
from app.models.common import GraphVerificationStatus
from app.models.factcheck import Claim
from app.models.llm import GraphCandidateOutput, GraphClaimCandidate


class FakeRepository:
    available = True

    def __init__(self, relations: list[dict[str, Any]]) -> None:
        self._relations = relations
        self.llm_lookup_calls = 0

    async def stats(self) -> tuple[int, int]:
        return 2, 1

    async def entity_names(self) -> list[str]:
        return ["埃菲尔铁塔", "巴黎"]

    async def lookup_relations(self, subject: str, predicate: str) -> list[dict[str, Any]]:
        return self._relations


class FakeLLM:
    async def chat_json(
        self,
        messages: Sequence[LLMMessage],
        schema: type[Any],
        **kwargs: Any,
    ) -> Any:
        return GraphCandidateOutput(
            candidates=[
                GraphClaimCandidate(
                    claim_id="c1",
                    subject="埃菲尔铁塔",
                    predicate="located_in",
                    object="柏林",
                )
            ]
        )


class EmptyRepository(FakeRepository):
    def __init__(self) -> None:
        super().__init__([])
        self.stats_called = 0

    async def stats(self) -> tuple[int, int]:
        self.stats_called += 1
        return 0, 0


async def test_confirmed_relation_produces_contradiction() -> None:
    repository = FakeRepository(
        [
            {
                "subject": "埃菲尔铁塔",
                "predicate": "located_in",
                "object": "巴黎",
                "confidence": 1.0,
                "note": "manual",
            }
        ]
    )
    verifier = GraphVerifier(repository, FakeLLM())
    result = await verifier.verify(
        [Claim(id="c1", text="埃菲尔铁塔位于柏林。")], round_number=1
    )
    assert result.status is GraphVerificationStatus.CONTRADICTED
    assert result.matches[0].graph_object == "巴黎"


async def test_empty_graph_returns_insufficient_without_llm_mapping() -> None:
    repository = EmptyRepository()
    verifier = GraphVerifier(repository, FakeLLM())
    result = await verifier.verify(
        [Claim(id="c1", text="埃菲尔铁塔位于柏林。")], round_number=1
    )
    assert result.status is GraphVerificationStatus.INSUFFICIENT
    assert repository.llm_lookup_calls == 0
