# Workflow MVP Spec: Claude Code + GitHub

This document specifies the full MVP workflow for incremental document management using Claude Code and GitHub as the backend.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IDM MVP ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────┐     ┌──────────────────────────────┐
│   User       │────▶│  IDM Functions   │────▶│  GitHub Repo                 │
│              │     │  (Python/CLI)    │     │  ├── summary.md              │
└──────────────┘     └────────┬─────────┘     │  ├── summary_spec.md         │
                              │               │  ├── messages/               │
                              ▼               │  │   ├── 001.md              │
                     ┌──────────────────┐     │  │   ├── 002.md              │
                     │  Claude API      │     │  │   └── ...                 │
                     │  (summarization) │     │  └── .claude/                │
                     └──────────────────┘     │      └── settings.json       │
                                              └──────────────────────────────┘
```

---

## Function 1: Setup (`idm_setup`)

Creates and links a GitHub repo with Claude Code project configuration.

### Input
```python
def idm_setup(
    repo_name: str,           # e.g., "my-project-notes"
    description: str,         # e.g., "Meeting notes and decisions tracker"
    github_token: str,        # GitHub personal access token
    private: bool = True      # Private repo by default
) -> dict:
```

### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              IDM_SETUP                                      │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────────┐
     │  Input params    │
     │  - repo_name     │
     │  - description   │
     └────────┬─────────┘
              │
              ▼
┌───────────────────────────────────────┐
│  1. CREATE GITHUB REPO                │
│                                       │
│  POST /user/repos                     │
│  {                                    │
│    "name": repo_name,                 │
│    "description": description,        │
│    "private": true,                   │
│    "auto_init": true                  │
│  }                                    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  2. CREATE INITIAL FILES              │
│                                       │
│  summary.md:                          │
│  "# Summary\n\n_No messages yet._"    │
│                                       │
│  summary_spec.md:                     │
│  (template - see below)               │
│                                       │
│  messages/.gitkeep:                   │
│  (empty, keeps folder in git)         │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  3. CREATE CLAUDE.md                  │
│                                       │
│  Project instructions for Claude Code │
│  - How to process messages            │
│  - Reference to summary_spec.md       │
│  - Commit message format              │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  4. COMMIT ALL FILES                  │
│                                       │
│  Commit message:                      │
│  "Initialize IDM project: {desc}"     │
└───────────────────┬───────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │  Return:       │
           │  - repo_url    │
           │  - clone_cmd   │
           │  - next_steps  │
           └────────────────┘
```

### Generated Files

**CLAUDE.md** (Claude Code project instructions):
```markdown
# IDM Project Instructions

This repository uses Incremental Document Management to maintain a living summary.

## Your Role

When given a new message to process:
1. Read `summary_spec.md` for summarization rules
2. Read current `summary.md`
3. Save the message to `messages/NNN.md` (zero-padded number)
4. Update `summary.md` with minimal changes based on the spec
5. Commit both files with message: "Process message NNN: [brief description]"

## Rules
- Make MINIMAL changes to summary.md (surgical edits only)
- Follow the structure defined in summary_spec.md
- Never remove information unless spec says to
- Each commit = one message processed
```

**summary_spec.md** (template):
```markdown
# Summary Specification

## Purpose
[User fills: What is this summary tracking?]

## Structure
[User fills: Required sections, format]

## Rules
- What to include
- What to exclude
- How to handle conflicts
- Maximum length constraints

## Example
[User fills: Example of good summary entry]
```

### Output
```python
{
    "repo_url": "https://github.com/user/my-project-notes",
    "clone_command": "git clone https://github.com/user/my-project-notes",
    "local_path": "/path/to/my-project-notes",
    "next_step": "Edit summary_spec.md to define your summarization rules, then commit."
}
```

---

## Function 2: Configure Spec (`idm_configure_spec`)

Interactive helper to create/update the summary_spec.md.

### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          IDM_CONFIGURE_SPEC                                 │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────────┐
     │  User provides   │
     │  spec content    │
     │  (or answers Qs) │
     └────────┬─────────┘
              │
              ▼
┌───────────────────────────────────────┐
│  Option A: Direct content             │
│                                       │
│  idm_configure_spec(                  │
│    repo_path="/path/to/repo",         │
│    spec_content="# Summary Spec..."   │
│  )                                    │
└───────────────────┬───────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│  Option B:      │   │  Write spec     │
│  Interactive    │   │  to file        │
│                 │   │                 │
│  Q: Purpose?    │   │  summary_spec.md│
│  Q: Sections?   │   │                 │
│  Q: Rules?      │   └────────┬────────┘
│  Q: Example?    │            │
└────────┬────────┘            │
         │                     │
         ▼                     ▼
┌───────────────────────────────────────┐
│  Commit:                              │
│  "Configure summary specification"    │
└───────────────────────────────────────┘
```

### Input
```python
def idm_configure_spec(
    repo_path: str,
    spec_content: str = None,      # Direct content
    interactive: bool = False       # If True, prompt user for each section
) -> dict:
```

---

## Function 3: Process Message (`idm_process`)

Takes a new message and updates the summary.

### Input
```python
def idm_process(
    repo_path: str,
    message: str,
    branch: str = "main"
) -> dict:
```

### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            IDM_PROCESS                                      │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────────┐
     │  New Message     │
     │  (input text)    │
     └────────┬─────────┘
              │
              ▼
┌───────────────────────────────────────┐
│  1. DETERMINE MESSAGE NUMBER          │
│                                       │
│  Count files in messages/ folder      │
│  Next number = count + 1              │
│  Format: 001, 002, ... 999            │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  2. READ CURRENT STATE                │
│                                       │
│  - summary.md (current summary)       │
│  - summary_spec.md (rules)            │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  3. CALL CLAUDE API                   │
│                                       │
│  Prompt:                              │
│  """                                  │
│  Summary spec:                        │
│  {summary_spec.md contents}           │
│                                       │
│  Current summary:                     │
│  {summary.md contents}                │
│                                       │
│  New message to process:              │
│  {message}                            │
│                                       │
│  Update the summary following the     │
│  spec. Make minimal changes. Return   │
│  only the updated summary.            │
│  """                                  │
│                                       │
│  Response: updated summary content    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  4. WRITE FILES                       │
│                                       │
│  messages/{NNN}.md = message content  │
│  summary.md = Claude's response       │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  5. COMMIT                            │
│                                       │
│  git add messages/{NNN}.md summary.md │
│  git commit -m "Process message NNN:  │
│    {brief description from Claude}"   │
└───────────────────┬───────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │  Return:       │
           │  - msg_number  │
           │  - commit_sha  │
           │  - diff_stats  │
           └────────────────┘
```

### Claude API Call Detail

```python
import anthropic

def call_claude_for_summary(spec: str, current_summary: str, message: str) -> str:
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": f"""You are updating a living summary document.

## Summary Specification
{spec}

## Current Summary
{current_summary}

## New Message to Process
{message}

## Instructions
1. Analyze the new message according to the specification
2. Update the summary with MINIMAL changes
3. Only add/modify what's necessary - preserve existing content
4. Return ONLY the updated summary, no explanations

Updated summary:"""
        }]
    )

    return response.content[0].text
```

### Output
```python
{
    "message_number": 42,
    "message_file": "messages/042.md",
    "commit_sha": "abc123f",
    "summary_diff": {
        "lines_added": 3,
        "lines_removed": 1,
        "lines_changed": 2
    }
}
```

---

## Function 4: Get Diff for Message (`idm_get_diff`)

Retrieves the summary.md changes for a specific message.

### Input
```python
def idm_get_diff(
    repo_path: str,
    message_number: int,
    context_lines: int = 3
) -> dict:
```

### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            IDM_GET_DIFF                                     │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────────┐
     │  Message number  │
     │  (e.g., 42)      │
     └────────┬─────────┘
              │
              ▼
┌───────────────────────────────────────┐
│  1. FIND COMMIT FOR MESSAGE           │
│                                       │
│  git log --oneline --all --grep=      │
│    "Process message 042"              │
│                                       │
│  OR: Find commit that added           │
│      messages/042.md                  │
│                                       │
│  git log --oneline --diff-filter=A    │
│    -- messages/042.md                 │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  2. GET DIFF FOR THAT COMMIT          │
│                                       │
│  git show {sha} -- summary.md         │
│                                       │
│  Or with context:                     │
│  git diff {sha}^..{sha} -- summary.md │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  3. PARSE DIFF OUTPUT                 │
│                                       │
│  Extract:                             │
│  - Lines added (+ prefix)             │
│  - Lines removed (- prefix)           │
│  - Context lines                      │
│  - Hunks with line numbers            │
└───────────────────┬───────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │  Return:       │
           │  - raw_diff    │
           │  - parsed      │
           │  - message     │
           │  - commit_info │
           └────────────────┘
```

### Implementation

```python
import subprocess

def idm_get_diff(repo_path: str, message_number: int, context_lines: int = 3) -> dict:
    msg_file = f"messages/{message_number:03d}.md"

    # Find the commit that added this message
    result = subprocess.run(
        ["git", "log", "--oneline", "--diff-filter=A", "--", msg_file],
        cwd=repo_path,
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        raise ValueError(f"No commit found for message {message_number}")

    commit_sha = result.stdout.strip().split()[0]

    # Get the diff for summary.md in that commit
    diff_result = subprocess.run(
        ["git", "show", f"-U{context_lines}", commit_sha, "--", "summary.md"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )

    # Get the message content
    msg_result = subprocess.run(
        ["git", "show", f"{commit_sha}:{msg_file}"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )

    # Get commit info
    info_result = subprocess.run(
        ["git", "log", "-1", "--format=%H%n%s%n%ai", commit_sha],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    sha, subject, date = info_result.stdout.strip().split('\n')

    return {
        "message_number": message_number,
        "message_content": msg_result.stdout,
        "commit": {
            "sha": sha,
            "subject": subject,
            "date": date
        },
        "diff": {
            "raw": diff_result.stdout,
            "stats": parse_diff_stats(diff_result.stdout)
        }
    }

def parse_diff_stats(diff_text: str) -> dict:
    lines = diff_text.split('\n')
    added = sum(1 for l in lines if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in lines if l.startswith('-') and not l.startswith('---'))
    return {"added": added, "removed": removed}
```

### Output
```python
{
    "message_number": 42,
    "message_content": "Original message text...",
    "commit": {
        "sha": "abc123def456",
        "subject": "Process message 042: Add Q3 budget decision",
        "date": "2025-01-23 10:30:00 +0000"
    },
    "diff": {
        "raw": "diff --git a/summary.md...",
        "stats": {"added": 5, "removed": 2}
    }
}
```

---

## Function 5: Visualize History (`idm_visualize`)

Generates a visual representation of the summary evolution.

### Input
```python
def idm_visualize(
    repo_path: str,
    output_format: str = "terminal",  # "terminal", "html", "json"
    last_n: int = None                 # Limit to last N messages
) -> str:
```

### Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IDM_VISUALIZE                                     │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────────┐
     │  Options         │
     │  - format        │
     │  - last_n        │
     └────────┬─────────┘
              │
              ▼
┌───────────────────────────────────────┐
│  1. GET ALL MESSAGE COMMITS           │
│                                       │
│  git log --oneline -- messages/       │
│                                       │
│  Extracts:                            │
│  - Commit SHA                         │
│  - Message number                     │
│  - Description                        │
│  - Timestamp                          │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  2. GET DIFF STATS FOR EACH           │
│                                       │
│  For each commit:                     │
│  git show --stat {sha} -- summary.md  │
│                                       │
│  Extracts: +N -M lines changed        │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│  3. RENDER OUTPUT                     │
│                                       │
│  Terminal: ASCII chart                │
│  HTML: Interactive timeline           │
│  JSON: Raw data for custom viz        │
└───────────────────┬───────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │  Return:       │
           │  formatted     │
           │  output        │
           └────────────────┘
```

### Terminal Output Example

```
IDM History: my-project-notes (15 messages)
============================================

MSG  DATE        CHANGES   DESCRIPTION
───  ──────────  ────────  ─────────────────────────────────
001  2025-01-20  +12 -0    Initial project scope
002  2025-01-20  +5  -2    Clarify timeline requirements
003  2025-01-21  +8  -1    Add team responsibilities
004  2025-01-21  +3  -0    Budget constraints noted
005  2025-01-22  +15 -4    Major scope revision
     ████████████████░░░░  (largest change)
006  2025-01-22  +2  -0    Minor clarification
007  2025-01-23  +6  -3    Update milestones
...

Summary Growth Over Time:
─────────────────────────
001 ██
002 ██▌
003 ███▌
004 ███▌
005 █████
006 █████
007 █████▌

Total: 15 messages, 247 lines in summary.md
```

### Implementation

```python
def idm_visualize(repo_path: str, output_format: str = "terminal", last_n: int = None) -> str:
    # Get all message-processing commits
    result = subprocess.run(
        ["git", "log", "--oneline", "--format=%H|%s|%ai", "--", "messages/"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )

    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        sha, subject, date = line.split('|')

        # Get diff stats for this commit
        stat_result = subprocess.run(
            ["git", "show", "--stat", "--format=", sha, "--", "summary.md"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        # Parse stats (e.g., "1 file changed, 5 insertions(+), 2 deletions(-)")
        stats = parse_stat_line(stat_result.stdout)

        # Extract message number from subject
        msg_num = extract_message_number(subject)

        commits.append({
            "sha": sha,
            "message_number": msg_num,
            "subject": subject,
            "date": date[:10],
            "added": stats.get("added", 0),
            "removed": stats.get("removed", 0)
        })

    commits.reverse()  # Chronological order

    if last_n:
        commits = commits[-last_n:]

    if output_format == "terminal":
        return render_terminal(commits)
    elif output_format == "html":
        return render_html(commits)
    elif output_format == "json":
        return json.dumps(commits, indent=2)

def render_terminal(commits: list) -> str:
    lines = []
    lines.append(f"IDM History ({len(commits)} messages)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"{'MSG':<4} {'DATE':<12} {'CHANGES':<10} DESCRIPTION")
    lines.append("─" * 60)

    max_change = max(c["added"] + c["removed"] for c in commits) if commits else 1

    for c in commits:
        change_str = f"+{c['added']:<3} -{c['removed']:<3}"
        desc = c["subject"].split(": ", 1)[-1][:30]

        lines.append(f"{c['message_number']:03d}  {c['date']}  {change_str}  {desc}")

        # Show bar for large changes
        total_change = c["added"] + c["removed"]
        if total_change > max_change * 0.5:
            bar_len = int(20 * total_change / max_change)
            lines.append(f"     {'█' * bar_len}{'░' * (20 - bar_len)}  (large change)")

    return "\n".join(lines)
```

---

## Complete Python Module

```python
# idm.py - Incremental Document Management via Claude + GitHub

import os
import json
import subprocess
from pathlib import Path
import anthropic
from github import Github

class IDM:
    def __init__(self, github_token: str = None, anthropic_key: str = None):
        self.github = Github(github_token or os.environ.get("GITHUB_TOKEN"))
        self.claude = anthropic.Anthropic(api_key=anthropic_key)

    def setup(self, repo_name: str, description: str, private: bool = True) -> dict:
        """Create and initialize a new IDM repository."""
        # Implementation from Function 1
        ...

    def configure_spec(self, repo_path: str, spec_content: str) -> dict:
        """Set up the summary specification."""
        # Implementation from Function 2
        ...

    def process(self, repo_path: str, message: str, branch: str = "main") -> dict:
        """Process a new message and update the summary."""
        # Implementation from Function 3
        ...

    def get_diff(self, repo_path: str, message_number: int) -> dict:
        """Get the summary diff for a specific message."""
        # Implementation from Function 4
        ...

    def visualize(self, repo_path: str, format: str = "terminal") -> str:
        """Visualize the summary evolution history."""
        # Implementation from Function 5
        ...

# CLI interface
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Incremental Document Management")
    subparsers = parser.add_subparsers(dest="command")

    # idm setup my-notes "Project meeting notes"
    setup_p = subparsers.add_parser("setup")
    setup_p.add_argument("name")
    setup_p.add_argument("description")

    # idm process "New message content here"
    process_p = subparsers.add_parser("process")
    process_p.add_argument("message")

    # idm diff 42
    diff_p = subparsers.add_parser("diff")
    diff_p.add_argument("message_number", type=int)

    # idm viz --format=terminal --last=10
    viz_p = subparsers.add_parser("viz")
    viz_p.add_argument("--format", default="terminal")
    viz_p.add_argument("--last", type=int)

    args = parser.parse_args()
    idm = IDM()

    if args.command == "setup":
        print(idm.setup(args.name, args.description))
    elif args.command == "process":
        print(idm.process(".", args.message))
    elif args.command == "diff":
        print(idm.get_diff(".", args.message_number))
    elif args.command == "viz":
        print(idm.visualize(".", args.format, args.last))
```

---

## Usage Example

```bash
# 1. Setup
idm setup "q1-planning" "Q1 2025 planning discussions"

# 2. Configure spec (edit the file, then commit)
cd q1-planning
vim summary_spec.md  # Define your rules
git add summary_spec.md && git commit -m "Configure summary spec"

# 3. Process messages
idm process "Meeting with Sarah: agreed on $50k budget for the new feature"
idm process "Email from Bob: timeline moved to March 15"
idm process "Slack thread: team prefers React over Vue for frontend"

# 4. View what a specific message changed
idm diff 2
# Shows: +1 line adding "Timeline: March 15" to summary

# 5. Visualize history
idm viz --last=10
```

---

## GitHub Actions Integration (Optional)

For fully automated processing, add a GitHub Action:

```yaml
# .github/workflows/process-message.yml
name: Process IDM Message

on:
  issues:
    types: [opened]
  issue_comment:
    types: [created]

jobs:
  process:
    if: contains(github.event.issue.labels.*.name, 'idm-message')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Process message
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          pip install anthropic
          python idm.py process "${{ github.event.issue.body || github.event.comment.body }}"

      - name: Commit changes
        run: |
          git config user.name "IDM Bot"
          git config user.email "idm@example.com"
          git add .
          git commit -m "Process message from issue #${{ github.event.issue.number }}"
          git push
```

This allows you to create GitHub issues labeled `idm-message` and have them automatically processed into the summary.
