"""
VeraChat Core - Chat Summarisation Versioning and Tracking

Uses Claude Code CLI for surgical edits to summary documents.
Stores chunk data in GitHub for version control, exports to SQLite for fast queries.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from verachat.models import (
    MessageChunk,
    SummaryChunk,
    ChunkLink,
    ProcessResult,
    HighlightData,
    ChunkFile,
)
from verachat.prompts import (
    CLAUDE_MD_TEMPLATE,
    SUMMARY_SPEC_TEMPLATE,
    INITIAL_SUMMARY,
    PROCESS_MESSAGE_PROMPT,
)


class VeraChat:
    """
    Chat Summarisation Versioning and Tracking.

    Uses Claude Code CLI + GitHub for processing and storage.
    Exports to SQLite for fast UI queries.
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        github_token: Optional[str] = None,
    ):
        """
        Initialize VeraChat.

        Args:
            repo_path: Path to existing repo (for processing/querying)
            github_token: GitHub token (for setup, optional if using gh CLI auth)
        """
        self.repo_path = Path(repo_path) if repo_path else None
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

    def setup(
        self,
        repo_name: str,
        description: str,
        private: bool = True,
        local_path: Optional[str] = None,
    ) -> dict:
        """
        Create and initialize a new VeraChat repository.

        Args:
            repo_name: Name for the new repository
            description: Repository description
            private: Whether to create a private repo (default: True)
            local_path: Where to clone locally (default: current dir / repo_name)

        Returns:
            dict with repo_url, local_path, next_step
        """
        local_path = Path(local_path or repo_name)

        # Create repo using gh CLI
        visibility = "--private" if private else "--public"
        subprocess.run(
            ["gh", "repo", "create", repo_name, visibility, "--description", description, "--clone"],
            check=True,
        )

        # Create initial files
        repo_dir = local_path

        # CLAUDE.md
        (repo_dir / "CLAUDE.md").write_text(CLAUDE_MD_TEMPLATE)

        # summary_spec.md
        (repo_dir / "summary_spec.md").write_text(SUMMARY_SPEC_TEMPLATE)

        # summary.md
        (repo_dir / "summary.md").write_text(INITIAL_SUMMARY)

        # messages directory
        (repo_dir / "messages").mkdir(exist_ok=True)
        (repo_dir / "messages" / ".gitkeep").touch()

        # .verachat directory for chunk tracking
        (repo_dir / ".verachat").mkdir(exist_ok=True)
        (repo_dir / ".verachat" / "chunks").mkdir(exist_ok=True)
        (repo_dir / ".verachat" / "chunks" / ".gitkeep").touch()

        # Commit initial files
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Initialize VeraChat project: {description}"],
            cwd=repo_dir,
            check=True,
        )
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo_dir, check=True)

        self.repo_path = repo_dir

        return {
            "repo_name": repo_name,
            "local_path": str(repo_dir.absolute()),
            "next_step": "Edit summary_spec.md to define your summarization rules, then commit.",
        }

    def process(
        self,
        message: str,
        metadata: Optional[dict] = None,
    ) -> ProcessResult:
        """
        Process a new message using Claude Code CLI.

        Claude Code will:
        1. Read the summary_spec.md and current summary.md
        2. Extract semantic chunks from the message
        3. Use its Edit tool to make surgical changes to summary.md
        4. Save message and chunk tracking data
        5. Commit all files

        Args:
            message: The message to process
            metadata: Optional metadata (msg_id, timestamp, etc.)

        Returns:
            ProcessResult with chunks, links, and diff info
        """
        if not self.repo_path:
            raise ValueError("No repo_path set. Call setup() or provide repo_path.")

        repo_path = Path(self.repo_path).absolute()

        # Ensure .verachat/chunks exists
        chunks_dir = repo_path / ".verachat" / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        # Determine next message number
        messages_dir = repo_path / "messages"
        existing = [f for f in messages_dir.glob("*.md") if f.name != ".gitkeep"]
        msg_number = len(existing) + 1
        message_id = f"{msg_number:03d}"
        message_file = f"messages/{message_id}.md"

        timestamp = datetime.utcnow().isoformat() + "Z"

        # Build the prompt for Claude Code
        prompt = PROCESS_MESSAGE_PROMPT.format(
            message_file=message_file,
            message_id=message_id,
            timestamp=timestamp,
            message=message,
        )

        # Invoke Claude Code CLI
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--dangerously-skip-permissions",
                "--allowedTools", "Read,Edit,Write,Bash",
                prompt,
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {result.stderr}")

        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        commit_sha = sha_result.stdout.strip()

        # Update chunk file with actual commit SHA
        chunk_file_path = chunks_dir / f"{message_id}.json"
        if chunk_file_path.exists():
            chunk_data = json.loads(chunk_file_path.read_text())
            chunk_data["commit_sha"] = commit_sha
            for sc in chunk_data.get("summary_changes", []):
                sc["commit_sha"] = commit_sha
            for link in chunk_data.get("links", []):
                link["commit_sha"] = commit_sha
            chunk_file_path.write_text(json.dumps(chunk_data, indent=2))

            # Amend commit to include updated chunk file
            subprocess.run(["git", "add", str(chunk_file_path)], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "commit", "--amend", "--no-edit"],
                cwd=repo_path,
                capture_output=True,
            )

            # Get updated SHA
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            commit_sha = sha_result.stdout.strip()

            # Parse chunk file into result
            chunk_file = ChunkFile.from_dict(chunk_data)
        else:
            chunk_file = ChunkFile(
                message_id=message_id,
                commit_sha=commit_sha,
                timestamp=timestamp,
                message_content=message,
            )

        # Get diff stats
        diff_stats = self._get_diff_stats(repo_path, commit_sha)

        return ProcessResult(
            message_id=message_id,
            message_file=message_file,
            commit_sha=commit_sha,
            timestamp=datetime.utcnow(),
            message_chunks=chunk_file.message_chunks,
            summary_chunks=chunk_file.summary_changes,
            links=chunk_file.links,
            lines_added=diff_stats.get("lines_added", 0),
            lines_removed=diff_stats.get("lines_removed", 0),
            claude_output=result.stdout,
        )

    def _get_diff_stats(self, repo_path: Path, commit_sha: str) -> dict:
        """Get diff statistics for a commit's summary.md changes."""
        result = subprocess.run(
            ["git", "show", "--stat", "--format=", commit_sha, "--", "summary.md"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        stats = {"lines_added": 0, "lines_removed": 0}

        match = re.search(r"(\d+) insertion", result.stdout)
        if match:
            stats["lines_added"] = int(match.group(1))

        match = re.search(r"(\d+) deletion", result.stdout)
        if match:
            stats["lines_removed"] = int(match.group(1))

        return stats

    def get_chunk_file(self, message_id: str) -> Optional[ChunkFile]:
        """Load chunk data for a specific message."""
        if not self.repo_path:
            raise ValueError("No repo_path set.")

        chunk_path = Path(self.repo_path) / ".verachat" / "chunks" / f"{message_id}.json"
        if not chunk_path.exists():
            return None

        return ChunkFile.from_json(chunk_path.read_text())

    def get_all_chunk_files(self) -> List[ChunkFile]:
        """Load all chunk files from the repository."""
        if not self.repo_path:
            raise ValueError("No repo_path set.")

        chunks_dir = Path(self.repo_path) / ".verachat" / "chunks"
        if not chunks_dir.exists():
            return []

        chunk_files = []
        for path in sorted(chunks_dir.glob("*.json")):
            try:
                chunk_files.append(ChunkFile.from_json(path.read_text()))
            except (json.JSONDecodeError, KeyError):
                continue

        return chunk_files

    def get_links_for_message(self, message_id: str) -> List[ChunkLink]:
        """Get all chunk links for a specific message."""
        chunk_file = self.get_chunk_file(message_id)
        if not chunk_file:
            return []
        return chunk_file.links

    def get_highlight_for_message(self, message_id: str) -> HighlightData:
        """
        Get highlight data for a message (message → summary direction).

        Returns spans to highlight in the message and lines to highlight in summary.
        """
        chunk_file = self.get_chunk_file(message_id)
        if not chunk_file:
            return HighlightData()

        message_spans = [
            (mc.span_start, mc.span_end) for mc in chunk_file.message_chunks
        ]
        summary_lines = [
            (sc.line_start, sc.line_end) for sc in chunk_file.summary_changes
        ]

        return HighlightData(
            message_spans=message_spans,
            summary_lines=summary_lines,
            message_chunks=chunk_file.message_chunks,
            summary_chunks=chunk_file.summary_changes,
            message_id=message_id,
            commit_sha=chunk_file.commit_sha,
        )

    def get_highlight_for_line(self, line_number: int) -> HighlightData:
        """
        Get highlight data for a summary line (summary → message direction).

        Returns the message chunks that caused this line to be added/modified.
        """
        highlight = HighlightData()

        for chunk_file in self.get_all_chunk_files():
            for sc in chunk_file.summary_changes:
                if sc.line_start <= line_number <= sc.line_end:
                    # Find linked message chunks
                    for link in chunk_file.links:
                        if link.summary_chunk_id == sc.id:
                            # Find the message chunk
                            for mc in chunk_file.message_chunks:
                                if mc.id == link.message_chunk_id:
                                    highlight.message_chunks.append(mc)
                                    highlight.message_spans.append(
                                        (mc.span_start, mc.span_end)
                                    )

                    highlight.summary_chunks.append(sc)
                    highlight.summary_lines.append((sc.line_start, sc.line_end))
                    highlight.message_id = chunk_file.message_id
                    highlight.commit_sha = chunk_file.commit_sha

        return highlight

    def get_summary_at_version(self, commit_sha: str) -> str:
        """Get the summary.md content at a specific commit."""
        if not self.repo_path:
            raise ValueError("No repo_path set.")

        result = subprocess.run(
            ["git", "show", f"{commit_sha}:summary.md"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise ValueError(f"Could not get summary at {commit_sha}")

        return result.stdout

    def get_message_content(self, message_id: str) -> str:
        """Get the content of a specific message."""
        if not self.repo_path:
            raise ValueError("No repo_path set.")

        msg_path = Path(self.repo_path) / "messages" / f"{message_id}.md"
        if not msg_path.exists():
            raise ValueError(f"Message {message_id} not found")

        return msg_path.read_text()

    def get_all_messages(self) -> List[dict]:
        """Get all messages with their IDs and content."""
        if not self.repo_path:
            raise ValueError("No repo_path set.")

        messages = []
        messages_dir = Path(self.repo_path) / "messages"

        for path in sorted(messages_dir.glob("*.md")):
            if path.name == ".gitkeep":
                continue
            message_id = path.stem
            messages.append({
                "id": message_id,
                "content": path.read_text(),
            })

        return messages

    def export_to_sqlite(self, db_path: str) -> None:
        """
        Export all chunk data to SQLite for fast queries.

        See sqlite.py for the export implementation.
        """
        from verachat.sqlite import export_to_sqlite
        export_to_sqlite(self, db_path)

    def visualize(
        self,
        output_format: str = "terminal",
        last_n: Optional[int] = None,
    ) -> str:
        """
        Visualize the summary evolution history.

        Args:
            output_format: "terminal", "html", or "json"
            last_n: Limit to last N messages (default: all)

        Returns:
            Formatted visualization string
        """
        if not self.repo_path:
            raise ValueError("No repo_path set.")

        repo_path = Path(self.repo_path)

        # Get all message-processing commits
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%H|%s|%ai", "--", "messages/"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) != 3:
                continue

            sha, subject, date = parts

            # Get diff stats for this commit
            stats = self._get_diff_stats(repo_path, sha)

            # Extract message number from subject
            msg_num = self._extract_message_number(subject)

            commits.append({
                "sha": sha[:7],
                "message_number": msg_num,
                "subject": subject,
                "date": date[:10],
                "added": stats.get("lines_added", 0),
                "removed": stats.get("lines_removed", 0),
            })

        commits.reverse()

        if last_n:
            commits = commits[-last_n:]

        if output_format == "terminal":
            return self._render_terminal(commits, repo_path)
        elif output_format == "html":
            return self._render_html(commits)
        elif output_format == "json":
            return json.dumps(commits, indent=2)
        else:
            raise ValueError(f"Unknown format: {output_format}")

    def _extract_message_number(self, subject: str) -> str:
        """Extract message number from commit subject."""
        match = re.search(r"(?:message|chunk)\s+(\d+(?:_\d+)?)", subject, re.IGNORECASE)
        if match:
            return match.group(1)
        return "?"

    def _render_terminal(self, commits: list, repo_path: Path) -> str:
        """Render terminal visualization."""
        if not commits:
            return "No messages processed yet."

        lines = []
        lines.append(f"VeraChat History ({len(commits)} messages)")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"{'MSG':<8} {'DATE':<12} {'CHANGES':<12} DESCRIPTION")
        lines.append("-" * 70)

        max_change = max((c["added"] + c["removed"]) for c in commits) if commits else 1
        max_change = max(max_change, 1)

        for c in commits:
            change_str = f"+{c['added']:<4} -{c['removed']:<4}"
            desc = c["subject"].split(": ", 1)[-1][:35] if ": " in c["subject"] else c["subject"][:35]

            lines.append(f"{c['message_number']:<8} {c['date']}  {change_str}  {desc}")

            total_change = c["added"] + c["removed"]
            if total_change > max_change * 0.5:
                bar_len = int(20 * total_change / max_change)
                lines.append(f"         {'█' * bar_len}{'░' * (20 - bar_len)}  (large change)")

        lines.append("")
        lines.append("-" * 70)

        summary_path = repo_path / "summary.md"
        if summary_path.exists():
            summary_lines = len(summary_path.read_text().split("\n"))
            lines.append(f"Total: {len(commits)} messages, {summary_lines} lines in summary.md")

        return "\n".join(lines)

    def _render_html(self, commits: list) -> str:
        """Render HTML visualization."""
        html = ["<!DOCTYPE html>", "<html>", "<head>"]
        html.append("<title>VeraChat History</title>")
        html.append("<style>")
        html.append("body { font-family: system-ui, sans-serif; padding: 20px; max-width: 900px; margin: 0 auto; }")
        html.append("table { border-collapse: collapse; width: 100%; }")
        html.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        html.append("th { background-color: #f4f4f4; }")
        html.append(".added { color: #22863a; }")
        html.append(".removed { color: #cb2431; }")
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")
        html.append(f"<h1>VeraChat History ({len(commits)} messages)</h1>")
        html.append("<table>")
        html.append("<tr><th>Msg</th><th>Date</th><th>Changes</th><th>Description</th></tr>")

        for c in commits:
            desc = c["subject"].split(": ", 1)[-1] if ": " in c["subject"] else c["subject"]
            html.append("<tr>")
            html.append(f"<td>{c['message_number']}</td>")
            html.append(f"<td>{c['date']}</td>")
            html.append(f"<td><span class='added'>+{c['added']}</span> <span class='removed'>-{c['removed']}</span></td>")
            html.append(f"<td>{desc}</td>")
            html.append("</tr>")

        html.append("</table>")
        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)
