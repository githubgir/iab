"""
VeraChat - Chat Summarisation Versioning and Tracking

A reusable library for maintaining living summary documents with
bidirectional linking between messages and summary sections.
"""

from verachat.core import VeraChat
from verachat.models import (
    MessageChunk,
    SummaryChunk,
    ChunkLink,
    ProcessResult,
    HighlightData,
)

__version__ = "0.1.0"
__all__ = [
    "VeraChat",
    "MessageChunk",
    "SummaryChunk",
    "ChunkLink",
    "ProcessResult",
    "HighlightData",
]
