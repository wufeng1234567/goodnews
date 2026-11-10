"""Unit tests for the JSON parsing boundary (no network)."""

from app.llm.client import _parse_json_object


def test_parse_plain_json() -> None:
    assert _parse_json_object('{"ok": true}') == {"ok": True}


def test_parse_fenced_json() -> None:
    assert _parse_json_object('```json\n{"claims": []}\n```') == {"claims": []}


def test_parse_json_with_prefix() -> None:
    assert _parse_json_object('result: {"value": 3}') == {"value": 3}
