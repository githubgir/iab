#!/usr/bin/env python3
"""
IDM - Incremental Document Management (Option B: Claude Code CLI)

Uses Claude Code CLI for surgical edits to summary documents.
Claude Code's Edit tool makes minimal line-level changes rather than rewriting files.
"""

import os
import re
import json
import subprocess
import argparse
from pathlib import Path
from typing import Optional

from github import Github

from prompts import (
    CLAUDE_MD_TEMPLATE,
    SUMMARY_SPEC_TEMPLATE,
    INITIAL_SUMMARY,
)


class IDM:
    """Incremental Document Management via Claude Code CLI + GitHub."""

    def __init__(self, github_token: Optional[str] = None):
        self.github = Github(github_token or os.environ.get("GITHUB_TOKEN"))

    def setup(
        self,
        repo_name: str,
        description: str,
        private: bool = True,
        local_path: Optional[str] = None,
    ) -> dict:
        """
        Create and initialize a new IDM repository.

        Args:
            repo_name: Name for the new repository
            description: Repository description
            private: Whether to create a private repo (default: True)
            local_path: Where to clone locally (default: current dir / repo_name)

        Returns:
            dict with repo_url, clone_command, local_path, next_step
        """
        user = self.github.get_user()

        # Create the repo
        repo = user.create_repo(
            name=repo_name,
            description=description,
            private=private,
            auto_init=True,
        )

        # Create initial files
        repo.create_file(
            path="CLAUDE.md",
            message="Add Claude Code project instructions",
            content=CLAUDE_MD_TEMPLATE,
        )

        repo.create_file(
            path="summary_spec.md",
            message="Add summary specification template",
            content=SUMMARY_SPEC_TEMPLATE,
        )

        repo.create_file(
            path="summary.md",
            message="Initialize summary document",
            content=INITIAL_SUMMARY,
        )

        repo.create_file(
            path="messages/.gitkeep",
            message="Create messages directory",
            content="",
        )

        # Clone locally
        local_path = local_path or repo_name
        clone_url = repo.clone_url

        subprocess.run(["git", "clone", clone_url, local_path], check=True)

        return {
            "repo_url": repo.html_url,
            "clone_command": f"git clone {clone_url}",
            "local_path": str(Path(local_path).absolute()),
            "next_step": "Edit summary_spec.md to define your summarization rules, then commit.",
        }

    def configure_spec(self, repo_path: str, spec_content: str) -> dict:
        """
        Update the summary specification.

        Args:
            repo_path: Path to the local repository
            spec_content: Content for summary_spec.md

        Returns:
            dict with status and commit_sha
        """
        spec_path = Path(repo_path) / "summary_spec.md"
        spec_path.write_text(spec_content)

        subprocess.run(
            ["git", "add", "summary_spec.md"],
            cwd=repo_path,
            check=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Configure summary specification"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        return {
            "status": "configured",
            "commit_sha": sha_result.stdout.strip(),
        }

    def process(
        self,
        repo_path: str,
        message: str,
        branch: str = "main",
    ) -> dict:
        """
        Process a new message using Claude Code CLI.

        Claude Code will:
        1. Read the summary_spec.md and current summary.md
        2. Use its Edit tool to make surgical changes to summary.md
        3. Save the message to messages/NNN.md
        4. Commit both files

        Args:
            repo_path: Path to the local repository
            message: The message to process
            branch: Git branch to work on (default: main)

        Returns:
            dict with message_number, message_file, commit_sha, summary_diff
        """
        repo_path = Path(repo_path).absolute()

        # Ensure we're on the right branch
        subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True)
        subprocess.run(["git", "pull", "origin", branch], cwd=repo_path, check=False)

        # Determine next message number
        messages_dir = repo_path / "messages"
        existing = list(messages_dir.glob("*.md"))
        existing = [f for f in existing if f.name != ".gitkeep"]
        msg_number = len(existing) + 1
        msg_file = f"messages/{msg_number:03d}.md"

        # Build the prompt for Claude Code
        prompt = f"""Process this new message for the IDM summary.

Instructions:
1. Read summary_spec.md to understand the summarization rules
2. Read the current summary.md
3. Save this message to {msg_file}
4. Update summary.md with MINIMAL changes based on the spec - use surgical edits, only change what's necessary
5. Commit both files with message: "Process message {msg_number:03d}: <brief description>"

New message to process:
---
{message}
---

Remember: Make minimal, surgical edits to summary.md. Only add/modify what's necessary."""

        # Invoke Claude Code CLI
        # --print outputs response to stdout
        # --allowedTools restricts to safe file operations
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
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {result.stderr}")

        # Get commit SHA (Claude Code should have committed)
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        commit_sha = sha_result.stdout.strip()

        # Get diff stats
        diff_stats = self._get_diff_stats(repo_path, commit_sha)

        return {
            "message_number": msg_number,
            "message_file": msg_file,
            "commit_sha": commit_sha,
            "summary_diff": diff_stats,
            "claude_output": result.stdout,
        }

    def process_chunked(
        self,
        repo_path: str,
        message: str,
        branch: str = "main",
    ) -> dict:
        """
        Process a message by splitting into semantic chunks.

        Claude Code will identify distinct topics and process each separately.

        Args:
            repo_path: Path to the local repository
            message: The message to process
            branch: Git branch to work on (default: main)

        Returns:
            dict with chunks processed information
        """
        repo_path = Path(repo_path).absolute()

        # Ensure we're on the right branch
        subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True)
        subprocess.run(["git", "pull", "origin", branch], cwd=repo_path, check=False)

        # Determine base message number
        messages_dir = repo_path / "messages"
        existing = list(messages_dir.glob("*.md"))
        existing = [f for f in existing if f.name != ".gitkeep"]
        base_number = len(existing) + 1

        # Build the prompt for Claude Code to chunk and process
        prompt = f"""Process this message by splitting it into semantic chunks.

Instructions:
1. Read summary_spec.md to understand the summarization rules
2. Identify distinct topics/decisions/items in the message below
3. For EACH chunk:
   a. Save it to messages/{base_number:03d}_XX.md (where XX is 01, 02, etc.)
   b. Update summary.md with MINIMAL surgical edits for that chunk
   c. Commit with message: "Process chunk {base_number:03d}_XX: <topic>"
4. Make separate commits for each chunk

Message to process:
---
{message}
---

Remember: Make minimal, surgical edits to summary.md for each chunk."""

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
            timeout=600,  # 10 minute timeout for chunked processing
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {result.stderr}")

        # Count how many chunk files were created
        new_files = list(messages_dir.glob(f"{base_number:03d}_*.md"))

        return {
            "base_message_number": base_number,
            "chunks_processed": len(new_files),
            "chunk_files": [f.name for f in sorted(new_files)],
            "claude_output": result.stdout,
        }

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

    def get_diff(
        self,
        repo_path: str,
        message_number: int,
        context_lines: int = 3,
    ) -> dict:
        """
        Get the summary diff for a specific message.

        Args:
            repo_path: Path to the local repository
            message_number: The message number to get diff for
            context_lines: Lines of context in diff (default: 3)

        Returns:
            dict with message_number, message_content, commit info, and diff
        """
        repo_path = Path(repo_path)

        # Try both regular and chunked file patterns
        msg_file = f"messages/{message_number:03d}.md"
        chunk_pattern = f"messages/{message_number:03d}_*.md"

        # Find the commit that added this message
        result = subprocess.run(
            ["git", "log", "--oneline", "--diff-filter=A", "--", msg_file],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if not result.stdout.strip():
            # Try chunk pattern
            chunk_files = list(repo_path.glob(chunk_pattern))
            if chunk_files:
                msg_file = str(chunk_files[0].relative_to(repo_path))
                result = subprocess.run(
                    ["git", "log", "--oneline", "--diff-filter=A", "--", msg_file],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )

        if not result.stdout.strip():
            raise ValueError(f"No commit found for message {message_number}")

        commit_sha = result.stdout.strip().split()[0]

        # Get the diff for summary.md in that commit
        diff_result = subprocess.run(
            ["git", "show", f"-U{context_lines}", commit_sha, "--", "summary.md"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        # Get the message content
        msg_result = subprocess.run(
            ["git", "show", f"{commit_sha}:{msg_file}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        # Get commit info
        info_result = subprocess.run(
            ["git", "log", "-1", "--format=%H%n%s%n%ai", commit_sha],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        sha, subject, date = info_result.stdout.strip().split("\n")

        # Parse diff stats
        diff_lines = diff_result.stdout.split("\n")
        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        return {
            "message_number": message_number,
            "message_content": msg_result.stdout,
            "commit": {
                "sha": sha,
                "subject": subject,
                "date": date,
            },
            "diff": {
                "raw": diff_result.stdout,
                "stats": {"added": added, "removed": removed},
            },
        }

    def visualize(
        self,
        repo_path: str,
        output_format: str = "terminal",
        last_n: Optional[int] = None,
    ) -> str:
        """
        Visualize the summary evolution history.

        Args:
            repo_path: Path to the local repository
            output_format: "terminal", "html", or "json"
            last_n: Limit to last N messages (default: all)

        Returns:
            Formatted visualization string
        """
        repo_path = Path(repo_path)

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
            stat_result = subprocess.run(
                ["git", "show", "--stat", "--format=", sha, "--", "summary.md"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            added = 0
            removed = 0
            match = re.search(r"(\d+) insertion", stat_result.stdout)
            if match:
                added = int(match.group(1))
            match = re.search(r"(\d+) deletion", stat_result.stdout)
            if match:
                removed = int(match.group(1))

            msg_num = self._extract_message_number(subject)

            commits.append({
                "sha": sha[:7],
                "message_number": msg_num,
                "subject": subject,
                "date": date[:10],
                "added": added,
                "removed": removed,
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
        lines.append(f"IDM History ({len(commits)} messages)")
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
        html.append("<title>IDM History</title>")
        html.append("<style>")
        html.append("body { font-family: monospace; padding: 20px; }")
        html.append("table { border-collapse: collapse; width: 100%; }")
        html.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        html.append("th { background-color: #f4f4f4; }")
        html.append(".added { color: green; }")
        html.append(".removed { color: red; }")
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")
        html.append(f"<h1>IDM History ({len(commits)} messages)</h1>")
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


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="IDM - Incremental Document Management (Claude Code CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup command
    setup_parser = subparsers.add_parser("setup", help="Create a new IDM repository")
    setup_parser.add_argument("name", help="Repository name")
    setup_parser.add_argument("description", help="Repository description")
    setup_parser.add_argument("--public", action="store_true", help="Make repo public")

    # process command
    process_parser = subparsers.add_parser("process", help="Process a new message")
    process_parser.add_argument("message", help="The message to process")
    process_parser.add_argument("--chunked", action="store_true", help="Split into semantic chunks")
    process_parser.add_argument("--repo", default=".", help="Repository path (default: .)")

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Show summary diff for a message")
    diff_parser.add_argument("message_number", type=int, help="Message number")
    diff_parser.add_argument("--repo", default=".", help="Repository path (default: .)")
    diff_parser.add_argument("--context", "-C", type=int, default=3, help="Context lines")

    # viz command
    viz_parser = subparsers.add_parser("viz", help="Visualize summary history")
    viz_parser.add_argument("--format", choices=["terminal", "html", "json"], default="terminal")
    viz_parser.add_argument("--last", type=int, help="Show only last N messages")
    viz_parser.add_argument("--repo", default=".", help="Repository path (default: .)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    idm = IDM()

    if args.command == "setup":
        result = idm.setup(args.name, args.description, private=not args.public)
        print(f"Repository created: {result['repo_url']}")
        print(f"Cloned to: {result['local_path']}")
        print(f"\nNext step: {result['next_step']}")

    elif args.command == "process":
        if args.chunked:
            result = idm.process_chunked(args.repo, args.message)
            print(f"Processed {result['chunks_processed']} chunks")
            for f in result["chunk_files"]:
                print(f"  - {f}")
        else:
            result = idm.process(args.repo, args.message)
            print(f"Processed message {result['message_number']}")
            print(f"Commit: {result['commit_sha'][:7]}")
            print(f"Summary: +{result['summary_diff']['lines_added']} -{result['summary_diff']['lines_removed']}")

    elif args.command == "diff":
        result = idm.get_diff(args.repo, args.message_number, args.context)
        print(f"Message {result['message_number']} ({result['commit']['date'][:10]})")
        print(f"Commit: {result['commit']['sha'][:7]} - {result['commit']['subject']}")
        print()
        print("Summary diff:")
        print(result["diff"]["raw"])

    elif args.command == "viz":
        output = idm.visualize(args.repo, args.format, args.last)
        print(output)


if __name__ == "__main__":
    main()
