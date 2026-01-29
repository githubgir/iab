"""
Data models for VeraChat chunk tracking and bidirectional linking.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple
from datetime import datetime
import json


@dataclass
class MessageChunk:
    """A semantic chunk extracted from a message."""

    id: str                          # e.g., "msg_001_c1"
    message_id: str                  # e.g., "001"
    chunk_index: int                 # Order within message (0, 1, 2...)
    chunk_type: str                  # "decision", "action", "info", "question"
    content: str                     # The chunk text
    span_start: int                  # Character position in original message
    span_end: int                    # Character position in original message

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MessageChunk":
        return cls(**data)


@dataclass
class SummaryChunk:
    """A chunk of the summary that was added/modified."""

    id: str                          # e.g., "sum_001_ch1"
    commit_sha: str                  # Which commit created this
    section: str                     # e.g., "Decisions", "Action Items"
    line_start: int                  # Line number in summary.md
    line_end: int                    # Line number in summary.md
    content: str                     # The actual text
    action: str                      # "added", "modified", "removed"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryChunk":
        return cls(**data)


@dataclass
class ChunkLink:
    """Bidirectional link between a message chunk and summary chunk."""

    message_chunk_id: str            # References MessageChunk.id
    summary_chunk_id: str            # References SummaryChunk.id
    commit_sha: str                  # When this link was created
    confidence: float = 1.0          # How confident we are in this link (0-1)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChunkLink":
        return cls(**data)


@dataclass
class ProcessResult:
    """Result of processing a message through VeraChat."""

    message_id: str                  # e.g., "001"
    message_file: str                # e.g., "messages/001.md"
    commit_sha: str                  # Git commit SHA
    timestamp: datetime              # When processed

    message_chunks: List[MessageChunk] = field(default_factory=list)
    summary_chunks: List[SummaryChunk] = field(default_factory=list)
    links: List[ChunkLink] = field(default_factory=list)

    # Diff statistics
    lines_added: int = 0
    lines_removed: int = 0

    # Claude's raw output (for debugging)
    claude_output: str = ""

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "message_file": self.message_file,
            "commit_sha": self.commit_sha,
            "timestamp": self.timestamp.isoformat(),
            "message_chunks": [c.to_dict() for c in self.message_chunks],
            "summary_chunks": [c.to_dict() for c in self.summary_chunks],
            "links": [l.to_dict() for l in self.links],
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessResult":
        return cls(
            message_id=data["message_id"],
            message_file=data["message_file"],
            commit_sha=data["commit_sha"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_chunks=[MessageChunk.from_dict(c) for c in data.get("message_chunks", [])],
            summary_chunks=[SummaryChunk.from_dict(c) for c in data.get("summary_chunks", [])],
            links=[ChunkLink.from_dict(l) for l in data.get("links", [])],
            lines_added=data.get("lines_added", 0),
            lines_removed=data.get("lines_removed", 0),
        )


@dataclass
class HighlightData:
    """Data for UI highlighting - used by both directions."""

    # Message highlights (character spans)
    message_spans: List[Tuple[int, int]] = field(default_factory=list)

    # Summary highlights (line ranges)
    summary_lines: List[Tuple[int, int]] = field(default_factory=list)

    # The chunks involved
    message_chunks: List[MessageChunk] = field(default_factory=list)
    summary_chunks: List[SummaryChunk] = field(default_factory=list)

    # Source info
    message_id: Optional[str] = None
    commit_sha: Optional[str] = None


@dataclass
class ChunkFile:
    """
    The JSON file stored in .verachat/chunks/NNN.json
    Contains all chunk data for a single message.
    """

    message_id: str
    commit_sha: str
    timestamp: str
    message_content: str

    message_chunks: List[MessageChunk] = field(default_factory=list)
    summary_changes: List[SummaryChunk] = field(default_factory=list)
    links: List[ChunkLink] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "commit_sha": self.commit_sha,
            "timestamp": self.timestamp,
            "message_content": self.message_content,
            "message_chunks": [c.to_dict() for c in self.message_chunks],
            "summary_changes": [c.to_dict() for c in self.summary_changes],
            "links": [l.to_dict() for l in self.links],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ChunkFile":
        return cls(
            message_id=data["message_id"],
            commit_sha=data["commit_sha"],
            timestamp=data["timestamp"],
            message_content=data.get("message_content", ""),
            message_chunks=[MessageChunk.from_dict(c) for c in data.get("message_chunks", [])],
            summary_changes=[SummaryChunk.from_dict(c) for c in data.get("summary_changes", [])],
            links=[ChunkLink.from_dict(l) for l in data.get("links", [])],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ChunkFile":
        return cls.from_dict(json.loads(json_str))
