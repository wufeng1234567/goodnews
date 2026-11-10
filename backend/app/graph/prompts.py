"""Prompt builders for the three LLM-backed graph steps."""

from __future__ import annotations

import json

from app.llm.client import LLMMessage
from app.models.factcheck import Claim, Evidence, GraphVerificationResult


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n……（正文已截断）"


def build_claim_extraction_messages(
    *, title: str, text: str, max_claims: int, language: str
) -> list[LLMMessage]:
    system = f"""你是严谨的事实核查编辑。请从文章中抽取可由公开证据验证的原子主张。

规则：
1. 只抽取客观、可验证的事实陈述；观点、预测、修辞、价值判断不要抽。
2. 复合句拆成互不依赖的原子主张；每条主张必须能单独核查。
3. 不得补充原文没有的信息，不得把推断写成事实。
4. 实体名称保留原文写法，去重。
5. 最多输出 {max_claims} 条，按重要性排序；没有可核查主张时返回空数组。
6. 输出语言：{language}。
"""
    user = f"""文章标题：{title}

文章正文：
{_clip(text, 16_000)}
"""
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]


def build_graph_candidate_messages(
    *, claims: list[Claim], entity_catalog: list[str]
) -> list[LLMMessage]:
    catalog = "、".join(entity_catalog[:120]) or "（图谱暂无实体）"
    claims_json = json.dumps(
        [{"claim_id": claim.id, "text": claim.text} for claim in claims],
        ensure_ascii=False,
    )
    system = """你是知识图谱检索规划器，只负责把主张映射成图谱三元组，不做真假判断。

规则：
1. 每条主张最多输出 1 个候选三元组，字段为 subject、predicate、object。
2. subject 必须使用实体白名单中的规范名称；如果无法把主张主语映射到白名单，才不要输出。
3. object 使用主张原文中的宾语，允许它不在白名单中；“柏林”这类待验证对象恰恰需要保留。
4. predicate 必须使用规范英文 snake_case，可用值：
   located_in, headquartered_in, capital_of, ceo_of, founded_by,
   member_of, launched_by, discovered_by, born_in, has_nationality, part_of。
5. 不要根据常识补全图谱，不要把“可能”“据说”解析成确定关系。
"""
    user = f"""实体白名单：
{catalog}

待映射主张：
{claims_json}
"""
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]


def build_adjudication_messages(
    *,
    claims: list[Claim],
    evidence: list[Evidence],
    graph: GraphVerificationResult,
    language: str,
) -> list[LLMMessage]:
    evidence_payload = [
        {
            "id": item.id,
            "claim_ids": item.claim_ids,
            "title": item.title,
            "source": item.source_name,
            "published_at": item.published_at,
            "snippet": _clip(item.snippet, 500),
            "excerpt": _clip(item.content_excerpt, 1_200),
            "url": item.url,
        }
        for item in evidence[:12]
    ]
    graph_payload = {
        "status": graph.status.value,
        "matches": [match.model_dump(mode="json") for match in graph.matches],
        "notes": graph.notes,
    }
    claim_payload = [
        {
            "id": claim.id,
            "text": claim.text,
            "entities": claim.entities,
            "importance": claim.importance,
        }
        for claim in claims
    ]

    system = f"""你是 final fact-check adjudicator（最终事实核查裁决员）。请仅依据给出的检索证据和人工确认的知识图谱裁决，输出审慎结论。

裁决规则：
1. 不得使用模型内部世界知识补充证据；没有证据就承认证据不足。
2. verdict 只能是 true、false、partially_true、insufficient_evidence。
3. graph_verification.status=insufficient 时，禁止声称“图谱支持/证实”；可以在证据充分时基于证据裁决，但必须明确说明图谱未提供有效关系。
4. graph_verification.status=contradicted 时，不得给出 true；与图谱冲突的主张必须标注。
5. 如果没有任何检索证据，且图谱未给出 supported 关系，整体必须为 insufficient_evidence。
6. 每条 claim 必须出现在 claim_verdicts 中，并引用实际存在的 evidence_ids；不得编造 id。
7. confidence 与证据强度一致；单一匿名来源不得高于 0.7。
8. reasoning 用 {language} 写，说明证据如何支持或反驳主张，并指出局限。

你必须输出 JSON 对象，结构严格符合 schema：
{{
  "verdict": "true|false|partially_true|insufficient_evidence",
  "confidence": 0.0,
  "claim_verdicts": [
    {{"claim_id": "c1", "verdict": "true", "confidence": 0.0,
      "reasoning": "...", "evidence_ids": ["e1"]}}
  ],
  "evidence_assessments": [
    {{"evidence_id": "e1", "stance": "supports|refutes|neutral", "relevance": 0.0}}
  ],
  "reasoning": "..."
}}
"""
    user = f"""待裁决主张：
{json.dumps(claim_payload, ensure_ascii=False, indent=2)}

检索证据：
{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}

知识图谱校验：
{json.dumps(graph_payload, ensure_ascii=False, indent=2)}
"""
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]
