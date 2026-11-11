"""Export formats must contain content and nested comments."""

from __future__ import annotations

from app.models.social import (
    SocialAuthor,
    SocialComment,
    SocialContent,
    SocialContentType,
    SocialFetchResponse,
    SocialMetrics,
    SocialPlatform,
)
from app.services.social_export import build_markdown, build_txt, build_xlsx


def _result() -> SocialFetchResponse:
    content = SocialContent(
        platform=SocialPlatform.BILIBILI,
        content_id="BV1test",
        content_type=SocialContentType.VIDEO,
        url="https://www.bilibili.com/video/BV1test",
        title="导出测试视频",
        description="测试简介",
        author=SocialAuthor(name="测试作者"),
        metrics=SocialMetrics(view_count=100, like_count=10, comment_count=2),
    )
    comments = [
        SocialComment(
            id="c1",
            content_id="BV1test",
            text="主评论",
            author_name="用户甲",
            like_count=3,
            replies=[
                SocialComment(
                    id="c2",
                    content_id="BV1test",
                    parent_id="c1",
                    text="楼中楼回复",
                    author_name="用户乙",
                )
            ],
        )
    ]
    return SocialFetchResponse(
        platform=SocialPlatform.BILIBILI,
        content=content,
        comments=comments,
        total_comments_fetched=2,
        collection_method="public_api",
    )


def test_markdown_and_txt_include_nested_comment() -> None:
    result = _result()
    markdown = build_markdown(result)
    text = build_txt(result)
    assert "导出测试视频" in markdown.content.decode("utf-8")
    assert "楼中楼回复" in markdown.content.decode("utf-8")
    assert "楼中楼回复" in text.content.decode("utf-8")
    assert markdown.filename.endswith(".md")
    assert text.filename.endswith(".txt")


def test_xlsx_export_has_content_and_comments_sheets() -> None:
    exported = build_xlsx(_result())
    assert exported.content.startswith(b"PK")
    assert exported.filename.endswith(".xlsx")
    assert len(exported.content) > 3_000
