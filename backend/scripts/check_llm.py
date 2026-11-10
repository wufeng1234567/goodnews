"""Minimal DeepSeek/OpenAI-compatible JSON-mode verification.

Run from backend/:
    .venv\\Scripts\\python -m scripts.check_llm
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from app.core.config import get_settings
from app.llm.client import LLMClient, LLMMessage


class LLMSmokeOutput(BaseModel):
    ok: bool
    message: str


async def main() -> int:
    client = LLMClient(get_settings())
    try:
        result = await client.chat_json(
            [
                LLMMessage(
                    role="user",
                    content="只回复 JSON：ok 为 true，message 为 goodnews llm ready。",
                )
            ],
            LLMSmokeOutput,
            max_tokens=120,
        )
        print(result.model_dump_json(indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should print a clear failure
        print(f"LLM check failed: {exc}")
        return 1
    finally:
        await client.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
