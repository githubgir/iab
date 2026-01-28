# Analysis: Claude Code + GitHub as MVP Alternative

## What Was Built on the Branch

The `claude/implement-mvp-features-pfs2q` branch contains a full Python library (~30 files):

- **Core pipeline**: Chunker → Differ → Applier → Session
- **Storage backends**: Memory, SQLite
- **LLM clients**: Anthropic, OpenAI adapters
- **Models**: Pydantic types for chunks, diffs, versions
- **Configuration**: Extensive `summary_spec.md` format
- **Git-like features**: blame, version navigation, provenance
- **MCP server**: For integration
- **Tests**: Full test suite

## Your Alternative Proposal

```
For each message:
1. Store message → new file (e.g., messages/001.md)
2. Claude Code updates → summary.md (minimal diff)
3. git commit both files
4. Push to GitHub branch

Usage: Navigate commits using GitHub UI
```

## Feature Comparison

| Feature | Library Approach | Claude Code + GitHub |
|---------|-----------------|---------------------|
| Version control | Custom in SQLite | Git (native) |
| Diff viewing | Custom diff model | `git diff` / GitHub UI |
| Provenance tracking | chunk → diff → version links | Commit history |
| Blame | Custom `session.blame()` | `git blame` |
| History navigation | `get_summary_at_message()` | `git checkout <commit>` |
| Message storage | SQLite chunks table | Individual files |
| Minimal diffs | LLM-generated diff objects | Claude Code Edit tool |
| Configuration | 200-line summary_spec.md | CLAUDE.md or prompt |
| Programmatic API | Full Python API | gh CLI / GitHub API |

## What Claude Code + GitHub Gives You for Free

1. **Version control** - Every commit is a version
2. **Provenance** - Commit message links message → summary change
3. **Blame** - `git blame summary.md` shows which message changed each line
4. **Diff viewing** - GitHub shows beautiful diffs between any commits
5. **History browsing** - GitHub UI for navigating commits
6. **Branching** - Alternative summary branches (already in Git)
7. **Comparison** - Compare any two points in history
8. **Search** - Search across all messages with GitHub search
9. **Collaboration** - PRs, comments, reviews if needed
10. **Backup** - GitHub hosts everything

## What You Lose

| Missing Feature | Impact | Workaround |
|-----------------|--------|------------|
| Sub-message chunking | Low - one message per commit is usually fine | N/A |
| Relevance scoring | Low - Claude naturally filters when summarizing | Include in prompt |
| SQLite queries | Medium - no SQL-style queries | `git log --grep`, GitHub search |
| Programmatic API | High (if needed) | GitHub API, gh CLI |
| MCP server | Medium (if needed) | Could build thin wrapper |

## Workflow Example

```bash
# Setup (once)
mkdir chat-session && cd chat-session
git init
echo "# Summary" > summary.md
mkdir messages
git add . && git commit -m "Initial"

# For each message (in Claude Code):
# 1. User pastes message
# 2. Claude Code writes messages/001.md with the message
# 3. Claude Code updates summary.md (minimal diff)
# 4. Claude Code commits: "Process message 001: [brief description]"

# Usage:
git log --oneline           # See all message processing
git show abc123             # See what message 5 added to summary
git blame summary.md        # See which message added each line
git diff abc123..def456     # Compare summary at two points
```

## Verdict

**The Claude Code + GitHub approach covers ~95% of the use case with 0% custom code.**

### When to use Claude Code + GitHub:
- Personal use / single user
- Don't need programmatic API integration
- Want zero maintenance
- Value simplicity
- Fine with one commit per message

### When to use the library:
- Need to call from other Python code
- Need sub-message chunking
- Building a product around this
- Need custom relevance scoring
- Want SQLite for complex queries

## What the Library Really Adds

The main value of the library approach is:

1. **Reusable component** - Can be imported and called from code
2. **Structured data** - Pydantic models vs plain files
3. **Configurable behavior** - summary_spec.md is very flexible
4. **MCP integration** - Use from any MCP-compatible client

But for the core problem of "track summary evolution linked to conversation", Git already solves this elegantly.

## Programmatic Workflow via APIs

You can absolutely automate this with Claude API + GitHub API:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTOMATED PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │  New Message │
     │   (input)    │
     └──────┬───────┘
            │
            ▼
┌───────────────────────────────────────┐
│          GITHUB API                   │
│  GET /repos/{owner}/{repo}/contents/  │
│       summary.md (current state)      │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│          CLAUDE API                   │
│                                       │
│  POST /messages                       │
│  {                                    │
│    "messages": [{                     │
│      "role": "user",                  │
│      "content": "                     │
│        Current summary: {summary.md}  │
│        New message: {input}           │
│        Update the summary minimally.  │
│        Return only the new summary."  │
│    }]                                 │
│  }                                    │
│                                       │
│  Response: updated summary content    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│          GITHUB API                   │
│                                       │
│  1. Create blob for message file      │
│     POST /repos/{o}/{r}/git/blobs     │
│                                       │
│  2. Create blob for updated summary   │
│     POST /repos/{o}/{r}/git/blobs     │
│                                       │
│  3. Create tree with both files       │
│     POST /repos/{o}/{r}/git/trees     │
│                                       │
│  4. Create commit                     │
│     POST /repos/{o}/{r}/git/commits   │
│     message: "Process msg N: {desc}"  │
│                                       │
│  5. Update branch ref                 │
│     PATCH /repos/{o}/{r}/git/refs/    │
└───────────────────┬───────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │   Complete    │
            │  (loop next)  │
            └───────────────┘
```

### Reading/Querying (also via APIs)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUERY OPERATIONS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐     ┌─────────────────────────────────────┐
│  Get summary at commit N        │     │  Compare two versions               │
│                                 │     │                                     │
│  GET /repos/{o}/{r}/contents/   │     │  GET /repos/{o}/{r}/compare/        │
│      summary.md?ref={sha}       │     │      {sha1}...{sha2}                │
└─────────────────────────────────┘     └─────────────────────────────────────┘

┌─────────────────────────────────┐     ┌─────────────────────────────────────┐
│  List all commits (messages)    │     │  Blame (what changed each line)     │
│                                 │     │                                     │
│  GET /repos/{o}/{r}/commits     │     │  GET /repos/{o}/{r}/commits         │
│      ?path=summary.md           │     │      ?path=summary.md               │
│                                 │     │  (then correlate with line ranges)  │
└─────────────────────────────────┘     └─────────────────────────────────────┘

┌─────────────────────────────────┐     ┌─────────────────────────────────────┐
│  Get specific message           │     │  Search messages                    │
│                                 │     │                                     │
│  GET /repos/{o}/{r}/contents/   │     │  GET /search/code?q={term}          │
│      messages/{n}.md            │     │      +repo:{o}/{r}+path:messages/   │
└─────────────────────────────────┘     └─────────────────────────────────────┘
```

### Minimal Python Implementation

```python
import anthropic
from github import Github  # PyGithub

def process_message(repo, message: str, msg_number: int):
    # 1. Get current summary
    try:
        summary = repo.get_contents("summary.md").decoded_content.decode()
    except:
        summary = ""

    # 2. Call Claude to update
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"""Current summary:
{summary}

New message:
{message}

Update the summary with minimal changes. Return only the updated summary."""
        }]
    )
    new_summary = response.content[0].text

    # 3. Commit both files
    msg_path = f"messages/{msg_number:03d}.md"

    # Create/update message file
    repo.create_file(msg_path, f"Add message {msg_number}", message)

    # Update summary
    contents = repo.get_contents("summary.md")
    repo.update_file("summary.md", f"Update summary for msg {msg_number}",
                     new_summary, contents.sha)

# Usage
g = Github("token")
repo = g.get_repo("owner/repo")
process_message(repo, "User's new message here", 1)
```

### What This Gives You

| Feature | How |
|---------|-----|
| Version history | Git commits |
| Provenance | Commit messages link msg → change |
| Diff viewing | GitHub compare API |
| Blame | Commits API + line correlation |
| Search | GitHub search API |
| Programmatic access | Full API control |

**Lines of code needed: ~30** (vs ~2000 in the library)

### Sub-Message Chunking (Also Just a Prompt)

Even splitting one message into multiple semantic chunks is just a prompt:

```python
def process_message_with_chunking(repo, message: str, base_msg_number: int):
    client = anthropic.Anthropic()

    # Step 1: Ask Claude to identify chunks
    chunk_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"""Analyze this message and split it into distinct semantic chunks.
Each chunk should be a separate topic, decision, question, or requirement.

Message:
{message}

Return as JSON array: [{{"id": 1, "topic": "brief description", "content": "chunk text"}}, ...]"""
        }]
    )
    chunks = json.loads(chunk_response.content[0].text)

    # Step 2: Process each chunk separately
    for i, chunk in enumerate(chunks):
        summary = repo.get_contents("summary.md").decoded_content.decode()

        update_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"""Current summary:
{summary}

New chunk (topic: {chunk['topic']}):
{chunk['content']}

Update the summary minimally. Return only the updated summary."""
            }]
        )
        new_summary = update_response.content[0].text

        # Commit this chunk
        chunk_id = f"{base_msg_number:03d}_{i+1:02d}"
        repo.create_file(f"chunks/{chunk_id}.md",
                        f"Chunk {chunk_id}: {chunk['topic']}",
                        chunk['content'])

        contents = repo.get_contents("summary.md")
        repo.update_file("summary.md",
                        f"Summary update for chunk {chunk_id}: {chunk['topic']}",
                        new_summary, contents.sha)
```

**Result**: One message → multiple commits, each with its own chunk file and summary diff.

This gives you:
- Fine-grained provenance (which specific topic caused which change)
- Atomic commits per semantic unit
- Easy rollback of specific topics

**The library's chunker is ~200 lines. This is ~30 lines + a prompt.**

## The Speed/Extraction Tradeoff

Git is optimized for version control, not querying. At scale, you might need:

```
Git repo → Extract to SQLite → Fast queries
```

But then you're back to implementing:
- Navigation features
- Blame-style attribution
- Range queries
- Search across messages

This is essentially what the library does - it's a pre-built extraction + query layer.

**The question becomes**: How much data before Git queries become slow?
- Hundreds of messages: Git is fine
- Thousands: Might need extraction
- Tens of thousands: Definitely need SQLite

## Recommendation

**Start with Claude Code + GitHub.** Build the library only if:
- You find yourself needing programmatic access
- Multiple projects need this capability
- The simple approach hits limitations
- Scale requires faster queries than Git provides

The library is well-designed, but it's solving a problem that Git already solves at the infrastructure level. It becomes valuable when you outgrow Git's query performance or need programmatic integration.
