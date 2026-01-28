# IDM - Incremental Document Management

A lightweight tool for maintaining living summary documents using Claude AI and GitHub as the backend.

## Overview

IDM tracks conversations, meetings, or any stream of messages by:
1. Storing each message as a separate file
2. Maintaining a continuously updated summary
3. Using Git commits for version control and provenance tracking

```
Message 1 ──┐
Message 2 ──┼──▶ Claude ──▶ summary.md (surgical edits)
Message 3 ──┘                    │
                                 ▼
                          Git commit (tracks what changed)
```

---

## Implementation Options

Three approaches were considered for implementing IDM:

### Option A: Anthropic API + GitHub

```
┌─────────┐    ┌──────────────┐    ┌─────────────────┐    ┌────────┐
│ Message │───▶│ Anthropic API│───▶│ Full new summary│───▶│ GitHub │
└─────────┘    │ (Claude)     │    │ (complete file) │    │ (diff) │
               └──────────────┘    └─────────────────┘    └────────┘
```

| Pros | Cons |
|------|------|
| Simple API integration | Claude returns full file, not diff |
| No CLI dependency | Git infers changes from full rewrite |
| Direct control | Potentially noisier diffs |
| Easier to host/deploy | Less surgical updates |

### Option B: Claude Code CLI/SDK + GitHub ✅ **Selected**

```
┌─────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌────────┐
│ Message │───▶│ Claude Code     │───▶│ Edit tool       │───▶│ GitHub │
└─────────┘    │ (linked to repo)│    │ (surgical diff) │    │ (clean)│
               └─────────────────┘    └─────────────────┘    └────────┘
```

| Pros | Cons |
|------|------|
| Claude Code's Edit tool makes surgical line-level changes | Requires Claude Code CLI installed |
| Cleaner, more meaningful diffs | Additional dependency |
| Built-in repo context awareness | Slightly more complex setup |
| Native commit behavior | |
| Understands file structure | |

### Option C: Full Custom Library

```
┌─────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Message │───▶│ Custom diff  │───▶│ Custom store │───▶│ Custom query │
└─────────┘    │ algorithm    │    │ (SQLite/etc) │    │ engine       │
               └──────────────┘    └──────────────┘    └──────────────┘
```

| Pros | Cons |
|------|------|
| Full control over everything | Significant development effort |
| Custom diff algorithms | Must implement versioning from scratch |
| Can optimize for speed (SQLite) | Must implement provenance tracking |
| No external dependencies | Must implement query capabilities |
| | Reinvents what Git already provides |

### Decision: Option B

**We are implementing Option B** because:

1. **Surgical diffs** - Claude Code's Edit tool modifies only the lines that need changing, not the full file
2. **Clean provenance** - Git diffs show exactly what each message changed
3. **Built-in context** - Claude Code understands the repo structure via CLAUDE.md
4. **Native commits** - Claude Code naturally commits after completing work
5. **Minimal code** - Leverages existing tools instead of rebuilding them

---

## Features

- **Zero infrastructure** - Uses GitHub for storage and versioning
- **Provenance tracking** - Every summary change links to its source message
- **Minimal diffs** - Claude updates only what's necessary
- **Git-native queries** - Use `git blame`, `git diff`, `git log` for analysis
- **Configurable** - Define your own summarization rules in `summary_spec.md`

## Installation

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Install Python dependencies
pip install PyGithub

# Authenticate Claude Code
claude auth login
```

Set environment variable for GitHub:
```bash
export GITHUB_TOKEN="your-github-token"
```

## Quick Start

```bash
# 1. Setup a new IDM project
python idm.py setup "my-notes" "Meeting notes tracker"

# 2. Edit summary_spec.md to define your summarization rules
cd my-notes
vim summary_spec.md

# 3. Process messages
python ../idm.py process "Meeting with team: decided to use React"
python ../idm.py process "Budget approved: $50k for Q2"

# 4. View what a message changed
python ../idm.py diff 1

# 5. Visualize history
python ../idm.py viz
```

## Commands

| Command | Description |
|---------|-------------|
| `idm.py setup <name> <desc>` | Create new IDM repository |
| `idm.py process <message>` | Process a new message |
| `idm.py diff <number>` | Show summary changes for a message |
| `idm.py viz [--last N]` | Visualize summary evolution |

## Project Structure

```
my-project/
├── CLAUDE.md           # Instructions for Claude Code
├── summary.md          # The living summary document
├── summary_spec.md     # Your summarization rules
└── messages/
    ├── 001.md          # First message
    ├── 002.md          # Second message
    └── ...
```

## Configuration

Edit `summary_spec.md` to control how summaries are generated:

```markdown
# Summary Specification

## Purpose
Track project decisions and action items.

## Structure
- **Decisions**: Key choices made
- **Action Items**: Tasks assigned
- **Open Questions**: Unresolved issues

## Rules
- Include decisions with owners
- Track deadlines when mentioned
- Exclude casual conversation
```

## Git-Native Queries

```bash
# What changed the summary?
git log --oneline -- summary.md

# Who/what added a specific line?
git blame summary.md

# Compare summary at two points
git diff abc123..def456 -- summary.md

# Find messages mentioning "budget"
grep -r "budget" messages/
```

## Documentation

- [Workflow MVP Spec](workflow-mvp-spec.md) - Detailed function specifications
- [Analysis](analysis-mvp-automation.md) - Comparison with library approach

## License

MIT
