"""Graph verification node implementation.

The LLM maps natural-language claims to candidate triples. The *verdict* of
this module comes exclusively from exact, manually seeded Neo4j relations.
"""

from __future__ import annotations

import logging
import re
import time

from app.graph.prompts import build_graph_candidate_messages
from app.knowledge_graph.repository import Neo4jRepository
from app.llm.client import LLMClientProtocol
from app.models.common import GraphMatchStatus, GraphVerificationStatus
from app.models.factcheck import (
    Claim,
    GraphMatch,
    GraphStatsResponse,
    GraphVerificationResult,
)
from app.models.llm import GraphCandidateOutput

logger = logging.getLogger(__name__)

# Single-valued predicates: a confirmed different object is a contradiction.
FUNCTIONAL_PREDICATES = {
    "located_in",
    "headquartered_in",
    "capital_of",
    "ceo_of",
    "born_in",
    "has_nationality",
}

PREDICATE_ALIASES = {
    "位于": "located_in",
    "坐落于": "located_in",
    "地点": "located_in",
    "总部位于": "headquartered_in",
    "总部在": "headquartered_in",
    "总部设于": "headquartered_in",
    "是首都": "capital_of",
    "首都是": "capital_of",
    "首席执行官": "ceo_of",
    "现任ceo": "ceo_of",
    "ceo": "ceo_of",
    "创立于": "founded_by",
    "由创立": "founded_by",
    "创始人": "founded_by",
    "成员": "member_of",
    "发射": "launched_by",
    "出生于": "born_in",
    "国籍": "has_nationality",
    "属于": "part_of",
}


def normalize_predicate(value: str) -> str:
    cleaned = re.sub(r"[\s\-]+", "_", value.strip().lower())
    return PREDICATE_ALIASES.get(cleaned, cleaned)


def _canonical(value: str) -> str:
    return re.sub(r"[\s\"'“”‘’·._-]+", "", value).lower()


class GraphVerifier:
    def __init__(self, repository: Neo4jRepository, llm: LLMClientProtocol) -> None:
        self._repository = repository
        self._llm = llm

    async def stats(self) -> GraphStatsResponse:
        if not self._repository.available:
            return GraphStatsResponse(
                entity_count=0,
                relation_count=0,
                available=False,
                note="Neo4j 未连接，图谱校验将返回 insufficient。",
            )
        try:
            entities, relations = await self._repository.stats()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Neo4j stats failed: %s", exc)
            return GraphStatsResponse(
                entity_count=0,
                relation_count=0,
                available=False,
                note="Neo4j 查询失败。",
            )
        note = "图谱为空，所有图谱校验都会返回 insufficient。" if relations == 0 else ""
        return GraphStatsResponse(
            entity_count=entities,
            relation_count=relations,
            available=True,
            note=note,
        )

    async def verify(self, claims: list[Claim], round_number: int) -> GraphVerificationResult:
        started = time.perf_counter()
        if not claims:
            return GraphVerificationResult(
                status=GraphVerificationStatus.INSUFFICIENT,
                notes=["没有可核查主张，图谱校验跳过。"],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                round=round_number,
            )

        try:
            entity_count, relation_count = await self._repository.stats()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Graph stats failed: %s", exc)
            entity_count = relation_count = 0

        if relation_count == 0:
            return GraphVerificationResult(
                status=GraphVerificationStatus.INSUFFICIENT,
                checked_claims=0,
                graph_entities=entity_count,
                graph_relations=0,
                notes=["知识图谱为空或关系未导入，不提供任何图谱推断。"],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                round=round_number,
            )

        catalog = await self._repository.entity_names()
        try:
            candidates: GraphCandidateOutput = await self._llm.chat_json(
                build_graph_candidate_messages(claims=claims, entity_catalog=catalog),
                GraphCandidateOutput,
                temperature=0,
                max_tokens=1_200,
            )
        except Exception as exc:  # noqa: BLE001 - graph is supplemental, never fatal
            logger.warning("Graph candidate extraction failed: %s", exc)
            return GraphVerificationResult(
                status=GraphVerificationStatus.INSUFFICIENT,
                checked_claims=0,
                graph_entities=entity_count,
                graph_relations=relation_count,
                notes=["图谱实体映射失败，按 insufficient 处理。"],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                round=round_number,
            )

        claim_ids = {claim.id for claim in claims}
        matches: list[GraphMatch] = []
        seen: set[tuple[str, str, str, str, str]] = set()
        for candidate in candidates.candidates[:10]:
            if candidate.claim_id not in claim_ids:
                continue
            predicate = normalize_predicate(candidate.predicate)
            try:
                relations = await self._repository.lookup_relations(
                    candidate.subject, predicate
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Neo4j lookup failed: %s", exc)
                continue

            if not relations:
                match = GraphMatch(
                    claim_id=candidate.claim_id,
                    subject=candidate.subject,
                    predicate=predicate,
                    claimed_object=candidate.object,
                    status=GraphMatchStatus.NO_DATA,
                    confidence=1.0,
                    note="图谱中没有该实体关系的确认记录。",
                )
            else:
                matching = [
                    relation
                    for relation in relations
                    if _canonical(str(relation["object"]))
                    == _canonical(candidate.object)
                ]
                if matching:
                    match = GraphMatch(
                        claim_id=candidate.claim_id,
                        subject=str(matching[0]["subject"]),
                        predicate=predicate,
                        claimed_object=candidate.object,
                        graph_object=str(matching[0]["object"]),
                        status=GraphMatchStatus.SUPPORTED,
                        confidence=float(matching[0].get("confidence", 1.0)),
                        note=str(matching[0].get("note") or "图谱存在确认关系。"),
                    )
                elif predicate in FUNCTIONAL_PREDICATES:
                    match = GraphMatch(
                        claim_id=candidate.claim_id,
                        subject=str(relations[0]["subject"]),
                        predicate=predicate,
                        claimed_object=candidate.object,
                        graph_object=str(relations[0]["object"]),
                        status=GraphMatchStatus.CONTRADICTED,
                        confidence=float(relations[0].get("confidence", 1.0)),
                        note=(
                            f"图谱确认对象为“{relations[0]['object']}”，"
                            f"与主张中的“{candidate.object}”冲突。"
                        ),
                    )
                else:
                    match = GraphMatch(
                        claim_id=candidate.claim_id,
                        subject=str(relations[0]["subject"]),
                        predicate=predicate,
                        claimed_object=candidate.object,
                        graph_object=str(relations[0]["object"]),
                        status=GraphMatchStatus.NO_DATA,
                        confidence=float(relations[0].get("confidence", 1.0)),
                        note="图谱有该谓词的其它多值关系，但不构成确定冲突。",
                    )

            key = (
                match.claim_id,
                match.subject,
                match.predicate,
                match.claimed_object,
                match.status.value,
            )
            if key not in seen:
                seen.add(key)
                matches.append(match)

        if any(item.status is GraphMatchStatus.CONTRADICTED for item in matches):
            status = GraphVerificationStatus.CONTRADICTED
        elif any(item.status is GraphMatchStatus.SUPPORTED for item in matches):
            status = GraphVerificationStatus.SUPPORTED
        else:
            status = GraphVerificationStatus.INSUFFICIENT

        notes: list[str] = []
        if status is GraphVerificationStatus.INSUFFICIENT:
            notes.append("图谱未找到可确认该主张的实体关系，不允许据此推断。")
        if not matches:
            notes.append("LLM 未能把主张映射到图谱白名单实体。")

        return GraphVerificationResult(
            status=status,
            matches=matches,
            checked_claims=len({match.claim_id for match in matches}),
            graph_entities=entity_count,
            graph_relations=relation_count,
            notes=notes,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            round=round_number,
        )
