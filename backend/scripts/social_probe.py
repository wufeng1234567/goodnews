"""Reproducible social-comment collection probes.

Examples (run from backend/):
  .venv\\Scripts\\python.exe -m scripts.social_probe --platform bilibili --url ... --max 1000
  .venv\\Scripts\\python.exe -m scripts.social_probe --platform douyin --url ... --max 100
  .venv\\Scripts\\python.exe -m scripts.social_probe --platform xiaohongshu --url ... --max 100 --headful
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

from app.core.config import Settings
from app.models.social import SocialFetchRequest
from app.platforms.bilibili import BilibiliAdapter
from app.platforms.douyin import DouyinAdapter
from app.platforms.xiaohongshu import XiaohongshuAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe social comment collection")
    parser.add_argument("--platform", choices=["bilibili", "douyin", "xiaohongshu"], required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--max", type=int, default=100, help="0 means the configured full cap")
    parser.add_argument("--no-replies", action="store_true")
    parser.add_argument("--headful", action="store_true", help="Use a visible Edge window (recommended for XHS)")
    return parser


async def run_probe(args: argparse.Namespace) -> dict:
    settings = Settings(social_browser_headless=not args.headful)
    adapter = {
        "bilibili": BilibiliAdapter,
        "douyin": DouyinAdapter,
        "xiaohongshu": XiaohongshuAdapter,
    }[args.platform](settings)
    started = time.perf_counter()
    result = await adapter.fetch(
        SocialFetchRequest(
            url=args.url,
            max_comments=args.max,
            include_replies=not args.no_replies,
        )
    )
    return {
        "platform": result.platform.value,
        "title": result.content.title,
        "declared_comments": result.content.metrics.comment_count,
        "fetched_comments": result.total_comments_fetched,
        "top_level_comments": len(result.comments),
        "has_more": result.has_more,
        "collection_method": result.collection_method,
        "auth_mode": result.auth_mode,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "warnings": result.warnings,
    }


def main() -> None:
    args = build_parser().parse_args()
    result = asyncio.run(run_probe(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
