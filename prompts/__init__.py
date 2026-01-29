"""
Legacy prompts module for backwards compatibility.

Imports from the new verachat.prompts module.
"""

from verachat.prompts import (
    CLAUDE_MD_TEMPLATE,
    SUMMARY_SPEC_TEMPLATE,
    INITIAL_SUMMARY,
    PROCESS_MESSAGE_PROMPT,
    EXTRACT_CHUNKS_PROMPT,
    LINK_CHUNKS_PROMPT,
)

__all__ = [
    "CLAUDE_MD_TEMPLATE",
    "SUMMARY_SPEC_TEMPLATE",
    "INITIAL_SUMMARY",
    "PROCESS_MESSAGE_PROMPT",
    "EXTRACT_CHUNKS_PROMPT",
    "LINK_CHUNKS_PROMPT",
]
