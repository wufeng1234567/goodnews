"""Export normalized social content/comments to Markdown, text or Excel."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from openpyxl import Workbook

from app.models.social import SocialComment, SocialFetchResponse

PLATFORM_LABELS = {
    "xiaohongshu": "小红书",
    "douyin": "抖音",
    "bilibili": "Bilibili",
}


@dataclass(frozen=True)
class ExportFile:
    content: bytes
    media_type: str
    filename: str


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", value).strip("_")
    return value[:80] or "social_comments"


def _metric_lines(result: SocialFetchResponse) -> list[str]:
    metrics = result.content.metrics
    labels = [
        ("播放/浏览", metrics.view_count),
        ("点赞", metrics.like_count),
        ("评论", metrics.comment_count),
        ("分享", metrics.share_count),
        ("收藏", metrics.collect_count),
        ("投币", metrics.coin_count),
        ("弹幕", metrics.danmaku_count),
    ]
    return [f"- {label}: {value}" for label, value in labels if value is not None]


def _walk_comments(comments: list[SocialComment], depth: int = 0):
    for comment in comments:
        yield comment, depth
        yield from _walk_comments(comment.replies, depth + 1)


def build_markdown(result: SocialFetchResponse) -> ExportFile:
    lines = [
        f"# {result.content.title}",
        "",
        f"- 平台：{PLATFORM_LABELS.get(result.platform.value, result.platform.value)}",
        f"- 作者：{result.content.author.name}",
        f"- 原链接：{result.content.url}",
        f"- 发布时间：{result.content.published_at or '未知'}",
        f"- 采集时间：{result.fetched_at.isoformat()}",
        f"- 评论条数（含回复）：{result.total_comments_fetched}",
        "",
        "## 热度数据",
        "",
        *_metric_lines(result),
        "",
        "## 内容简介",
        "",
        result.content.description or "（无）",
        "",
        "## 评论",
        "",
    ]
    for comment, depth in _walk_comments(result.comments):
        prefix = "> " * depth
        lines.append(
            f"{prefix}- **{comment.author_name}**（赞 {comment.like_count}，"
            f"回复 {comment.reply_count}）：{comment.text}"
        )
    lines.extend(
        [
            "",
            "---",
            "导出自 goodnews · 社媒采集",
            "",
        ]
    )
    return ExportFile(
        content="\n".join(lines).encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        filename=f"{_safe_filename(result.content.title)}.md",
    )


def build_txt(result: SocialFetchResponse) -> ExportFile:
    lines = [
        result.content.title,
        "=" * 60,
        f"平台: {PLATFORM_LABELS.get(result.platform.value, result.platform.value)}",
        f"作者: {result.content.author.name}",
        f"链接: {result.content.url}",
        f"发布: {result.content.published_at or '未知'}",
        f"采集: {result.fetched_at.isoformat()}",
        f"评论数(含回复): {result.total_comments_fetched}",
        "",
        "热度数据:",
        *_metric_lines(result),
        "",
        "内容简介:",
        result.content.description or "（无）",
        "",
        "评论:",
        "",
    ]
    for comment, depth in _walk_comments(result.comments):
        indent = "  " * depth
        lines.append(
            f"{indent}[{comment.author_name}] 赞{comment.like_count} 回复{comment.reply_count}"
        )
        lines.append(f"{indent}{comment.text}")
        lines.append("")
    lines.extend(["-" * 60, "导出自 goodnews · 社媒采集"])
    return ExportFile(
        content="\n".join(lines).encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        filename=f"{_safe_filename(result.content.title)}.txt",
    )


def build_xlsx(result: SocialFetchResponse) -> ExportFile:
    workbook = Workbook(write_only=True)
    summary = workbook.create_sheet("内容信息")
    summary.append(["字段", "值"])
    summary.append(["平台", PLATFORM_LABELS.get(result.platform.value, result.platform.value)])
    summary.append(["标题", result.content.title])
    summary.append(["作者", result.content.author.name])
    summary.append(["原链接", result.content.url])
    summary.append(
        [
            "发布时间",
            result.content.published_at.isoformat() if result.content.published_at else "",
        ]
    )
    summary.append(["采集时间", result.fetched_at.isoformat()])
    summary.append(["评论数（含回复）", result.total_comments_fetched])
    summary.append(["内容简介", result.content.description])
    for label, value in [(label.removeprefix("- ").split(":")[0], label.split(": ", 1)[-1]) for label in _metric_lines(result)]:
        summary.append([label, value])

    comments_sheet = workbook.create_sheet("评论")
    comments_sheet.append(
        ["序号", "层级", "父评论ID", "评论ID", "作者", "评论内容", "点赞", "回复数", "发布时间"]
    )
    for index, (comment, depth) in enumerate(_walk_comments(result.comments), start=1):
        comments_sheet.append(
            [
                index,
                depth,
                comment.parent_id or "",
                comment.id,
                comment.author_name,
                comment.text,
                comment.like_count,
                comment.reply_count,
                comment.created_at.isoformat() if comment.created_at else "",
            ]
        )
    buffer = BytesIO()
    workbook.save(buffer)
    return ExportFile(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{_safe_filename(result.content.title)}.xlsx",
    )


def export_result(result: SocialFetchResponse, format_name: str) -> ExportFile:
    builders = {
        "md": build_markdown,
        "markdown": build_markdown,
        "txt": build_txt,
        "text": build_txt,
        "xlsx": build_xlsx,
        "excel": build_xlsx,
    }
    builder = builders.get(format_name.lower())
    if builder is None:
        raise ValueError("支持的导出格式为 xlsx / md / txt")
    return builder(result)
