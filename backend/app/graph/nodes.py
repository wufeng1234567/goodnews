"""LangGraph node implementations.

Every LLM-backed node calls ``llm_client.chat_json`` directly. There are no
LangChain chains or agents in this path; LangGraph is used strictly for state
orchestration.
"""

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from typing import Any

from app.core.config import Settings
from app.graph.guardrails import apply_adjudication_guardrails
from app.graph.ports import ArticleProvider, EvidenceProvider, GraphVerifier
from app.graph.prompts import (
    build_adjudication_messages,
    build_claim_extraction_messages,
)
from app.graph.state import FactCheckState
from app.llm.client import LLMClientProtocol
from app.models.article import ArticleContent
from app.models.common import GraphVerificationStatus, NodeStatus, Verdict
from app.models.factcheck import (
    Claim,
    Evidence,
    GraphVerificationResult,
    TraceStep,
    VerdictResult,
)
from app.models.llm import AdjudicationOutput, ClaimExtractionOutput


def _as_state(state: FactCheckState | Mapping[str, Any]) -> FactCheckState:
    """LangGraph passes the Pydantic state, but accepting dict keeps unit fakes easy."""
    if isinstance(state, FactCheckState):
        return state
    return FactCheckState.model_validate(state)


def _trace(
    state: FactCheckState,
    *,
    node: str,
    label: str,
    detail: str,
    started: float,
    status: NodeStatus = NodeStatus.COMPLETED,
) -> TraceStep:
    return TraceStep(
        node=node,
        label=label,
        status=status,
        detail=detail[:500],
        duration_ms=int((time.perf_counter() - started) * 1000),
        sequence=len(state.trace) + 1,
    )


def _claim_query(claim: Claim) -> str:
    # Search works best with the factual sentence itself, without question words.
    cleaned = re.sub(r"^(请问|据说|听说)", "", claim.text).strip()
    return cleaned[:150]


class FactCheckNodes:
    """Node container with injected dependencies (easy to test, no globals)."""

    def __init__(
        self,
        *,
        settings: Settings,
        llm: LLMClientProtocol,
        articles: ArticleProvider,
        evidence: EvidenceProvider,
        graph: GraphVerifier,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._articles = articles
        self._evidence = evidence
        self._graph = graph

    async def fetch_article(
        self, raw_state: FactCheckState | Mapping[str, Any]
    ) -> dict[str, Any]:
        state = _as_state(raw_state)
        started = time.perf_counter()
        article: ArticleContent = await self._articles.resolve(state.request)
        if article.word_count == 0:
            article = article.model_copy(update={"word_count": len(article.text)})
        trace = _trace(
            state,
            node="fetch_article",
            label="抓取与正文提取",
            detail=(
                f"来源：{article.source_name or '用户输入'}；"
                f"正文 {article.word_count} 字；提取方式：{article.fetched_with}"
            ),
            started=started,
        )
        return {"article": article, "trace": [*state.trace, trace]}

    async def extract_claims(
        self, raw_state: FactCheckState | Mapping[str, Any]
    ) -> dict[str, Any]:
        state = _as_state(raw_state)
        started = time.perf_counter()
        if state.article is None:
            raise ValueError("extract_claims requires article")

        output: ClaimExtractionOutput = await self._llm.chat_json(
            build_claim_extraction_messages(
                title=state.article.title,
                text=state.article.text,
                max_claims=self._settings.max_claims,
                language=state.request.language,
            ),
            ClaimExtractionOutput,
            temperature=0,
            max_tokens=1800,
        )

        claims: list[Claim] = []
        seen: set[str] = set()
        for draft in output.claims[: self._settings.max_claims]:
            normalized = re.sub(r"\s+", "", draft.text)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            claims.append(
                Claim(
                    id=f"c{len(claims) + 1}",
                    text=draft.text.strip(),
                    entities=[entity.strip() for entity in draft.entities if entity.strip()][:12],
                    importance=draft.importance,
                )
            )

        detail = (
            f"抽取 {len(claims)} 条可核查主张"
            if claims
            else "未发现可独立核查的客观主张"
        )
        trace = _trace(
            state,
            node="extract_claims",
            label="拆解可核查主张",
            detail=detail,
            started=started,
        )
        return {"claims": claims, "trace": [*state.trace, trace]}

    async def retrieve_evidence(
        self, raw_state: FactCheckState | Mapping[str, Any]
    ) -> dict[str, Any]:
        state = _as_state(raw_state)
        started = time.perf_counter()
        round_number = state.evidence_round + 1

        queries = [query for query in state.next_queries if query.strip()]
        if not queries:
            queries = [_claim_query(claim) for claim in state.claims[:4]]

        new_evidence: list[Evidence] = []
        if queries and state.claims:
            new_evidence = await self._evidence.retrieve(
                claims=state.claims,
                queries=queries,
                existing=state.evidence,
            )

        merged = {item.id: item for item in state.evidence}
        for item in new_evidence:
            merged.setdefault(item.id, item)
        all_evidence = list(merged.values())

        detail = (
            f"第 {round_number} 轮检索：新增 {len(new_evidence)} 条证据，"
            f"累计 {len(all_evidence)} 条"
        )
        trace = _trace(
            state,
            node="retrieve_evidence",
            label="检索交叉证据",
            detail=detail,
            started=started,
        )
        return {
            "evidence": all_evidence,
            "evidence_round": round_number,
            "next_queries": [],
            "trace": [*state.trace, trace],
        }

    async def graph_verify(
        self, raw_state: FactCheckState | Mapping[str, Any]
    ) -> dict[str, Any]:
        state = _as_state(raw_state)
        started = time.perf_counter()
        graph_result: GraphVerificationResult = await self._graph.verify(
            state.claims, state.evidence_round
        )

        all_claim_ids = {claim.id for claim in state.claims}
        covered_claim_ids = {
            claim_id for item in state.evidence for claim_id in item.claim_ids
        } & all_claim_ids
        coverage = len(covered_claim_ids) / len(all_claim_ids) if all_claim_ids else 1.0
        required_evidence = 1 if len(all_claim_ids) <= 1 else min(3, len(all_claim_ids))
        evidence_sufficient = (
            len(state.evidence) >= required_evidence and coverage >= 0.75
        )
        if graph_result.status is GraphVerificationStatus.CONTRADICTED:
            # A confirmed contradiction is enough to adjudicate; more search
            # cannot erase a manually verified graph fact.
            evidence_sufficient = True

        next_queries: list[str] = []
        can_retry = (
            not evidence_sufficient
            and state.evidence_round < state.max_evidence_rounds
            and bool(state.claims)
        )
        if can_retry:
            uncovered = [
                claim for claim in state.claims if claim.id not in covered_claim_ids
            ]
            candidates = uncovered or state.claims
            next_queries = [f"{_claim_query(claim)} 官方 回应" for claim in candidates[:3]]

        detail = (
            f"图谱状态：{graph_result.status.value}；"
            f"证据覆盖：{len(covered_claim_ids)}/{len(all_claim_ids)} 条主张"
        )
        if can_retry:
            detail += f"；准备第 {state.evidence_round + 2} 轮检索"
        trace = _trace(
            state,
            node="graph_verify",
            label="知识图谱校验",
            detail=detail,
            started=started,
        )
        return {
            "graph_verification": graph_result,
            "evidence_sufficient": evidence_sufficient,
            "next_queries": next_queries,
            "trace": [*state.trace, trace],
        }

    async def adjudicate(
        self, raw_state: FactCheckState | Mapping[str, Any]
    ) -> dict[str, Any]:
        state = _as_state(raw_state)
        started = time.perf_counter()
        if state.graph_verification is None:
            raise ValueError("adjudicate requires graph_verification")

        if not state.claims:
            empty_graph = state.graph_verification
            verdict_result = VerdictResult(
                verdict=Verdict.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                claims=[],
                evidence=state.evidence,
                graph_verification=empty_graph,
                reasoning="文章中没有抽取到可独立验证的事实主张，无法进行真假裁决。",
            )
        else:
            adjudication: AdjudicationOutput = await self._llm.chat_json(
                build_adjudication_messages(
                    claims=state.claims,
                    evidence=state.evidence,
                    graph=state.graph_verification,
                    language=state.request.language,
                ),
                AdjudicationOutput,
                temperature=0.1,
                max_tokens=2800,
            )
            adjudication, guard_notes = apply_adjudication_guardrails(
                adjudication,
                state.claims,
                state.evidence,
                state.graph_verification,
            )

            assessment_by_evidence = {
                item.evidence_id: item for item in adjudication.evidence_assessments
            }
            evidence = []
            for item in state.evidence:
                assessment = assessment_by_evidence.get(item.id)
                if assessment is None:
                    evidence.append(item)
                else:
                    evidence.append(
                        item.model_copy(
                            update={
                                "stance": assessment.stance,
                                "relevance": assessment.relevance,
                            }
                        )
                    )

            claim_verdict_by_id = {
                item.claim_id: item for item in adjudication.claim_verdicts
            }
            actual_evidence_ids = {item.id for item in evidence}
            claims: list[Claim] = []
            for claim in state.claims:
                claim_verdict = claim_verdict_by_id.get(claim.id)
                if claim_verdict is None:
                    claims.append(
                        claim.model_copy(
                            update={
                                "verdict": Verdict.INSUFFICIENT_EVIDENCE,
                                "confidence": 0.0,
                                "reasoning": "缺少独立判断，按证据不足处理。",
                                "evidence_ids": [],
                            }
                        )
                    )
                    continue
                claims.append(
                    claim.model_copy(
                        update={
                            "verdict": claim_verdict.verdict,
                            "confidence": claim_verdict.confidence,
                            "reasoning": claim_verdict.reasoning,
                            "evidence_ids": [
                                evidence_id
                                for evidence_id in claim_verdict.evidence_ids
                                if evidence_id in actual_evidence_ids
                            ],
                        }
                    )
                )

            reasoning = adjudication.reasoning.strip()
            if guard_notes:
                # Keep the LLM's reasoning visible, but make deterministic
                # adjustments explicit instead of silently rewriting it.
                reasoning = (
                    reasoning
                    + "\n\n系统安全约束："
                    + " ".join(guard_notes)
                )

            verdict_result = VerdictResult(
                verdict=adjudication.verdict,
                confidence=adjudication.confidence,
                claims=claims,
                evidence=evidence,
                graph_verification=state.graph_verification,
                reasoning=reasoning,
            )

        trace = _trace(
            state,
            node="adjudicate",
            label="形成最终裁决",
            detail=f"结论：{verdict_result.verdict.value}，置信度 {verdict_result.confidence:.0%}",
            started=started,
        )
        return {
            "verdict": verdict_result,
            "warnings": list(state.warnings),
            "trace": [*state.trace, trace],
        }
