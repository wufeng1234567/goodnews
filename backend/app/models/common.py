"""Shared enums used by API models, LangGraph state and the frontend contract."""

from __future__ import annotations

from enum import Enum


class InputType(str, Enum):
    AUTO = "auto"
    URL = "url"
    TEXT = "text"


class Verdict(str, Enum):
    TRUE = "true"
    FALSE = "false"
    PARTIALLY_TRUE = "partially_true"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class GraphVerificationStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


class GraphMatchStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NO_DATA = "no_data"


class EvidenceStance(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    NEUTRAL = "neutral"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
