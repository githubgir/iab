"""
SQLite export and query layer for VeraChat.

Provides fast queries for UI highlighting and navigation.
Can be rebuilt from Git history at any time.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from verachat.core import VeraChat

from verachat.models import (
    MessageChunk,
    SummaryChunk,
    ChunkLink,
    HighlightData,
)


SCHEMA = """
-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    commit_sha TEXT,
    timestamp TEXT,
    content TEXT
);

-- Message chunks
CREATE TABLE IF NOT EXISTS message_chunks (
    id TEXT PRIMARY KEY,
    message_id TEXT REFERENCES messages(id),
    chunk_index INTEGER,
    chunk_type TEXT,
    span_start INTEGER,
    span_end INTEGER,
    content TEXT
);

-- Summary chunks (snapshots at each commit)
CREATE TABLE IF NOT EXISTS summary_chunks (
    id TEXT PRIMARY KEY,
    commit_sha TEXT,
    section TEXT,
    line_start INTEGER,
    line_end INTEGER,
    content TEXT,
    action TEXT
);

-- Bidirectional links
CREATE TABLE IF NOT EXISTS chunk_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_chunk_id TEXT REFERENCES message_chunks(id),
    summary_chunk_id TEXT REFERENCES summary_chunks(id),
    commit_sha TEXT,
    confidence REAL
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_message_chunks_message ON message_chunks(message_id);
CREATE INDEX IF NOT EXISTS idx_summary_chunks_lines ON summary_chunks(line_start, line_end);
CREATE INDEX IF NOT EXISTS idx_links_message ON chunk_links(message_chunk_id);
CREATE INDEX IF NOT EXISTS idx_links_summary ON chunk_links(summary_chunk_id);
CREATE INDEX IF NOT EXISTS idx_messages_commit ON messages(commit_sha);
"""


def export_to_sqlite(vc: "VeraChat", db_path: str) -> None:
    """
    Export all chunk data from a VeraChat repo to SQLite.

    Args:
        vc: VeraChat instance with repo_path set
        db_path: Path to SQLite database file
    """
    db_path = Path(db_path)

    # Create/connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(SCHEMA)

    # Clear existing data (full rebuild)
    cursor.execute("DELETE FROM chunk_links")
    cursor.execute("DELETE FROM summary_chunks")
    cursor.execute("DELETE FROM message_chunks")
    cursor.execute("DELETE FROM messages")

    # Export all chunk files
    for chunk_file in vc.get_all_chunk_files():
        # Insert message
        cursor.execute(
            "INSERT OR REPLACE INTO messages (id, commit_sha, timestamp, content) VALUES (?, ?, ?, ?)",
            (chunk_file.message_id, chunk_file.commit_sha, chunk_file.timestamp, chunk_file.message_content),
        )

        # Insert message chunks
        for mc in chunk_file.message_chunks:
            cursor.execute(
                """INSERT OR REPLACE INTO message_chunks
                   (id, message_id, chunk_index, chunk_type, span_start, span_end, content)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (mc.id, mc.message_id, mc.chunk_index, mc.chunk_type, mc.span_start, mc.span_end, mc.content),
            )

        # Insert summary chunks
        for sc in chunk_file.summary_changes:
            cursor.execute(
                """INSERT OR REPLACE INTO summary_chunks
                   (id, commit_sha, section, line_start, line_end, content, action)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sc.id, sc.commit_sha, sc.section, sc.line_start, sc.line_end, sc.content, sc.action),
            )

        # Insert links
        for link in chunk_file.links:
            cursor.execute(
                """INSERT INTO chunk_links
                   (message_chunk_id, summary_chunk_id, commit_sha, confidence)
                   VALUES (?, ?, ?, ?)""",
                (link.message_chunk_id, link.summary_chunk_id, link.commit_sha, link.confidence),
            )

    conn.commit()
    conn.close()


class VeraChatDB:
    """
    SQLite query interface for VeraChat.

    Provides fast lookups for UI highlighting.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_all_messages(self) -> List[dict]:
        """Get all messages ordered by ID."""
        cursor = self.conn.execute(
            "SELECT id, commit_sha, timestamp, content FROM messages ORDER BY id"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_message(self, message_id: str) -> Optional[dict]:
        """Get a single message by ID."""
        cursor = self.conn.execute(
            "SELECT id, commit_sha, timestamp, content FROM messages WHERE id = ?",
            (message_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_message_chunks(self, message_id: str) -> List[MessageChunk]:
        """Get all chunks for a message."""
        cursor = self.conn.execute(
            """SELECT id, message_id, chunk_index, chunk_type, span_start, span_end, content
               FROM message_chunks WHERE message_id = ? ORDER BY chunk_index""",
            (message_id,),
        )
        return [
            MessageChunk(
                id=row["id"],
                message_id=row["message_id"],
                chunk_index=row["chunk_index"],
                chunk_type=row["chunk_type"],
                span_start=row["span_start"],
                span_end=row["span_end"],
                content=row["content"],
            )
            for row in cursor.fetchall()
        ]

    def get_summary_chunks_for_message(self, message_id: str) -> List[SummaryChunk]:
        """Get summary chunks created by a specific message."""
        cursor = self.conn.execute(
            """SELECT sc.id, sc.commit_sha, sc.section, sc.line_start, sc.line_end, sc.content, sc.action
               FROM summary_chunks sc
               JOIN messages m ON sc.commit_sha = m.commit_sha
               WHERE m.id = ?""",
            (message_id,),
        )
        return [
            SummaryChunk(
                id=row["id"],
                commit_sha=row["commit_sha"],
                section=row["section"],
                line_start=row["line_start"],
                line_end=row["line_end"],
                content=row["content"],
                action=row["action"],
            )
            for row in cursor.fetchall()
        ]

    def get_links_for_message(self, message_id: str) -> List[ChunkLink]:
        """Get all chunk links for a message."""
        cursor = self.conn.execute(
            """SELECT cl.message_chunk_id, cl.summary_chunk_id, cl.commit_sha, cl.confidence
               FROM chunk_links cl
               JOIN message_chunks mc ON cl.message_chunk_id = mc.id
               WHERE mc.message_id = ?""",
            (message_id,),
        )
        return [
            ChunkLink(
                message_chunk_id=row["message_chunk_id"],
                summary_chunk_id=row["summary_chunk_id"],
                commit_sha=row["commit_sha"],
                confidence=row["confidence"],
            )
            for row in cursor.fetchall()
        ]

    def get_links_for_line(self, line_number: int) -> List[Tuple[ChunkLink, str]]:
        """
        Get chunk links for a summary line number.

        Returns list of (ChunkLink, message_id) tuples.
        """
        cursor = self.conn.execute(
            """SELECT cl.message_chunk_id, cl.summary_chunk_id, cl.commit_sha, cl.confidence, mc.message_id
               FROM chunk_links cl
               JOIN summary_chunks sc ON cl.summary_chunk_id = sc.id
               JOIN message_chunks mc ON cl.message_chunk_id = mc.id
               WHERE sc.line_start <= ? AND sc.line_end >= ?""",
            (line_number, line_number),
        )
        return [
            (
                ChunkLink(
                    message_chunk_id=row["message_chunk_id"],
                    summary_chunk_id=row["summary_chunk_id"],
                    commit_sha=row["commit_sha"],
                    confidence=row["confidence"],
                ),
                row["message_id"],
            )
            for row in cursor.fetchall()
        ]

    def get_highlight_for_message(self, message_id: str) -> HighlightData:
        """
        Get highlight data for a message (message → summary direction).

        Fast SQLite-based lookup for UI.
        """
        message_chunks = self.get_message_chunks(message_id)
        summary_chunks = self.get_summary_chunks_for_message(message_id)

        message = self.get_message(message_id)

        return HighlightData(
            message_spans=[(mc.span_start, mc.span_end) for mc in message_chunks],
            summary_lines=[(sc.line_start, sc.line_end) for sc in summary_chunks],
            message_chunks=message_chunks,
            summary_chunks=summary_chunks,
            message_id=message_id,
            commit_sha=message["commit_sha"] if message else None,
        )

    def get_highlight_for_line(self, line_number: int) -> HighlightData:
        """
        Get highlight data for a summary line (summary → message direction).

        Fast SQLite-based lookup for UI.
        """
        links_with_messages = self.get_links_for_line(line_number)

        if not links_with_messages:
            return HighlightData()

        # Collect all related chunks
        message_chunks = []
        summary_chunks = []
        message_ids = set()

        for link, message_id in links_with_messages:
            message_ids.add(message_id)

            # Get the message chunk
            cursor = self.conn.execute(
                """SELECT id, message_id, chunk_index, chunk_type, span_start, span_end, content
                   FROM message_chunks WHERE id = ?""",
                (link.message_chunk_id,),
            )
            row = cursor.fetchone()
            if row:
                message_chunks.append(
                    MessageChunk(
                        id=row["id"],
                        message_id=row["message_id"],
                        chunk_index=row["chunk_index"],
                        chunk_type=row["chunk_type"],
                        span_start=row["span_start"],
                        span_end=row["span_end"],
                        content=row["content"],
                    )
                )

            # Get the summary chunk
            cursor = self.conn.execute(
                """SELECT id, commit_sha, section, line_start, line_end, content, action
                   FROM summary_chunks WHERE id = ?""",
                (link.summary_chunk_id,),
            )
            row = cursor.fetchone()
            if row:
                summary_chunks.append(
                    SummaryChunk(
                        id=row["id"],
                        commit_sha=row["commit_sha"],
                        section=row["section"],
                        line_start=row["line_start"],
                        line_end=row["line_end"],
                        content=row["content"],
                        action=row["action"],
                    )
                )

        return HighlightData(
            message_spans=[(mc.span_start, mc.span_end) for mc in message_chunks],
            summary_lines=[(sc.line_start, sc.line_end) for sc in summary_chunks],
            message_chunks=message_chunks,
            summary_chunks=summary_chunks,
            message_id=list(message_ids)[0] if message_ids else None,
        )

    def get_summary_evolution(self) -> List[dict]:
        """
        Get summary evolution data for visualization.

        Returns list of {message_id, commit_sha, timestamp, lines_added, lines_removed}
        """
        cursor = self.conn.execute(
            """SELECT m.id as message_id, m.commit_sha, m.timestamp,
                      COUNT(CASE WHEN sc.action = 'added' THEN 1 END) as lines_added,
                      COUNT(CASE WHEN sc.action = 'removed' THEN 1 END) as lines_removed
               FROM messages m
               LEFT JOIN summary_chunks sc ON m.commit_sha = sc.commit_sha
               GROUP BY m.id
               ORDER BY m.id"""
        )
        return [dict(row) for row in cursor.fetchall()]
