"""Manually curated MVP graph.

This is intentionally small (tens of entities, not a knowledge base). Its job
is to prove that a confirmed graph relation can veto an LLM over-inference.
Every relation below is a demo-quality, manually reviewed statement; dates and
leadership roles can change and should be re-verified before production use.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SeedEntity(BaseModel):
    name: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""


class SeedRelation(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: float = Field(default=1.0, ge=0, le=1)
    note: str = "MVP 手工确认关系"
    source: str = "manual_seed"


ENTITIES: list[SeedEntity] = [
    SeedEntity(name="埃菲尔铁塔", entity_type="landmark", aliases=["巴黎铁塔"], description="法国巴黎地标"),
    SeedEntity(name="巴黎", entity_type="city", aliases=["Paris"]),
    SeedEntity(name="法国", entity_type="country", aliases=["法兰西"]),
    SeedEntity(name="欧洲", entity_type="continent"),
    SeedEntity(name="长城", entity_type="landmark", aliases=["万里长城"]),
    SeedEntity(name="中国", entity_type="country", aliases=["中华人民共和国", "China"]),
    SeedEntity(name="北京", entity_type="city", aliases=["北京市"]),
    SeedEntity(name="亚洲", entity_type="continent"),
    SeedEntity(name="东京", entity_type="city"),
    SeedEntity(name="日本", entity_type="country"),
    SeedEntity(name="纽约", entity_type="city"),
    SeedEntity(name="美国", entity_type="country", aliases=["United States", "USA"]),
    SeedEntity(name="苹果公司", entity_type="company", aliases=["Apple", "苹果"]),
    SeedEntity(name="史蒂夫·乔布斯", entity_type="person", aliases=["乔布斯", "Steve Jobs"]),
    SeedEntity(name="蒂姆·库克", entity_type="person", aliases=["库克", "Tim Cook"]),
    SeedEntity(name="微软公司", entity_type="company", aliases=["Microsoft", "微软"]),
    SeedEntity(name="比尔·盖茨", entity_type="person", aliases=["Bill Gates"]),
    SeedEntity(name="萨提亚·纳德拉", entity_type="person", aliases=["Satya Nadella"]),
    SeedEntity(name="DeepSeek", entity_type="company", aliases=["深度求索"]),
    SeedEntity(name="杭州", entity_type="city"),
    SeedEntity(name="浙江大学", entity_type="university", aliases=["浙大"]),
    SeedEntity(name="特斯拉", entity_type="company", aliases=["Tesla"]),
    SeedEntity(name="埃隆·马斯克", entity_type="person", aliases=["马斯克", "Elon Musk"]),
    SeedEntity(name="马丁·艾伯哈德", entity_type="person", aliases=["Martin Eberhard"]),
    SeedEntity(name="谷歌公司", entity_type="company", aliases=["Google", "谷歌"]),
    SeedEntity(name="桑达尔·皮查伊", entity_type="person", aliases=["劈柴", "Sundar Pichai"]),
    SeedEntity(name="拉里·佩奇", entity_type="person", aliases=["Larry Page"]),
    SeedEntity(name="谢尔盖·布林", entity_type="person", aliases=["Sergey Brin"]),
    SeedEntity(name="阿里巴巴集团", entity_type="company", aliases=["阿里巴巴", "Alibaba"]),
    SeedEntity(name="马云", entity_type="person", aliases=["Jack Ma"]),
    SeedEntity(name="腾讯公司", entity_type="company", aliases=["腾讯", "Tencent"]),
    SeedEntity(name="深圳", entity_type="city"),
    SeedEntity(name="世界卫生组织", entity_type="organization", aliases=["WHO"]),
    SeedEntity(name="日内瓦", entity_type="city"),
    SeedEntity(name="联合国", entity_type="organization", aliases=["UN"]),
    SeedEntity(name="珠穆朗玛峰", entity_type="landmark", aliases=["珠峰"]),
    SeedEntity(name="尼泊尔", entity_type="country"),
    SeedEntity(name="亚马逊公司", entity_type="company", aliases=["Amazon", "亚马逊"]),
    SeedEntity(name="杰夫·贝索斯", entity_type="person", aliases=["贝索斯", "Jeff Bezos"]),
    SeedEntity(name="嫦娥五号", entity_type="spacecraft", aliases=["Chang'e 5"]),
    SeedEntity(name="中国国家航天局", entity_type="organization", aliases=["CNSA"]),
]

RELATIONS: list[SeedRelation] = [
    SeedRelation(subject="埃菲尔铁塔", predicate="located_in", object="巴黎"),
    SeedRelation(subject="巴黎", predicate="capital_of", object="法国"),
    SeedRelation(subject="法国", predicate="part_of", object="欧洲"),
    SeedRelation(subject="长城", predicate="located_in", object="中国"),
    SeedRelation(subject="中国", predicate="part_of", object="亚洲"),
    SeedRelation(subject="北京", predicate="capital_of", object="中国"),
    SeedRelation(subject="东京", predicate="capital_of", object="日本"),
    SeedRelation(subject="纽约", predicate="located_in", object="美国"),
    SeedRelation(subject="苹果公司", predicate="founded_by", object="史蒂夫·乔布斯"),
    SeedRelation(subject="苹果公司", predicate="ceo_of", object="蒂姆·库克"),
    SeedRelation(subject="微软公司", predicate="founded_by", object="比尔·盖茨"),
    SeedRelation(subject="微软公司", predicate="ceo_of", object="萨提亚·纳德拉"),
    SeedRelation(subject="DeepSeek", predicate="headquartered_in", object="杭州"),
    SeedRelation(subject="浙江大学", predicate="located_in", object="杭州"),
    SeedRelation(subject="杭州", predicate="located_in", object="中国"),
    SeedRelation(subject="特斯拉", predicate="ceo_of", object="埃隆·马斯克"),
    SeedRelation(subject="特斯拉", predicate="founded_by", object="马丁·艾伯哈德"),
    SeedRelation(subject="谷歌公司", predicate="ceo_of", object="桑达尔·皮查伊"),
    SeedRelation(subject="谷歌公司", predicate="founded_by", object="拉里·佩奇"),
    SeedRelation(subject="谷歌公司", predicate="founded_by", object="谢尔盖·布林"),
    SeedRelation(subject="阿里巴巴集团", predicate="founded_by", object="马云"),
    SeedRelation(subject="阿里巴巴集团", predicate="headquartered_in", object="杭州"),
    SeedRelation(subject="腾讯公司", predicate="headquartered_in", object="深圳"),
    SeedRelation(subject="深圳", predicate="located_in", object="中国"),
    SeedRelation(subject="世界卫生组织", predicate="headquartered_in", object="日内瓦"),
    SeedRelation(subject="联合国", predicate="headquartered_in", object="纽约"),
    SeedRelation(subject="珠穆朗玛峰", predicate="located_in", object="中国"),
    SeedRelation(subject="珠穆朗玛峰", predicate="located_in", object="尼泊尔"),
    SeedRelation(subject="亚马逊公司", predicate="founded_by", object="杰夫·贝索斯"),
    SeedRelation(subject="嫦娥五号", predicate="launched_by", object="中国国家航天局"),
]
