"""
Prompt templates for VeraChat.

These prompts instruct Claude Code to:
1. Extract semantic chunks from messages
2. Update the summary with surgical edits
3. Track which chunks caused which changes
"""

# Template for CLAUDE.md in new repos
CLAUDE_MD_TEMPLATE = """# VeraChat Project Instructions

This repository uses VeraChat to maintain a living summary of conversations.

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
"""

# Template for initial summary_spec.md
SUMMARY_SPEC_TEMPLATE = """# Summary Specification

## Purpose
[Describe what this summary is tracking - e.g., "Project decisions and action items"]

## Structure
Organize the summary with these sections:
- **Decisions**: Key choices made
- **Action Items**: Tasks assigned with owners
- **Open Questions**: Unresolved issues
- **Notes**: Other important information

## Rules
- Include decisions with their rationale when given
- Track deadlines and owners for action items
- Mark resolved questions by moving to Decisions
- Keep entries concise (1-2 lines each)
- Use bullet points for easy scanning

## Example Entry
- **Decision**: Use React for frontend (2025-01-15) - Team preferred ecosystem
"""

# Template for initial summary.md
INITIAL_SUMMARY = """# Summary

_No messages processed yet._

## Decisions

## Action Items

## Open Questions

## Notes
"""

# Prompt for processing a message with chunk extraction
PROCESS_MESSAGE_PROMPT = """Process this new message for VeraChat.

## Instructions

1. **Read context**:
   - Read `summary_spec.md` for summarization rules
   - Read current `summary.md`

2. **Save the message**:
   - Save to `{message_file}`

3. **Identify chunks** in the message:
   Analyze the message and identify distinct semantic chunks. Each chunk should be one of:
   - `decision`: A choice or conclusion reached
   - `action`: A task or action item
   - `info`: Important information or context
   - `question`: An open question or uncertainty

4. **Update summary.md**:
   - Make MINIMAL surgical edits (only change what's necessary)
   - Add/modify entries based on the chunks identified
   - Follow the structure in summary_spec.md

5. **Create chunk tracking file**:
   After updating the summary, create `.verachat/chunks/{message_id}.json` with this structure:
   ```json
   {{
     "message_id": "{message_id}",
     "commit_sha": "WILL_BE_FILLED",
     "timestamp": "{timestamp}",
     "message_content": "<the full message>",
     "message_chunks": [
       {{
         "id": "msg_{message_id}_c0",
         "message_id": "{message_id}",
         "chunk_index": 0,
         "chunk_type": "decision|action|info|question",
         "content": "<chunk text>",
         "span_start": <start char position>,
         "span_end": <end char position>
       }}
     ],
     "summary_changes": [
       {{
         "id": "sum_{message_id}_ch0",
         "commit_sha": "WILL_BE_FILLED",
         "section": "<section name>",
         "line_start": <line number>,
         "line_end": <line number>,
         "content": "<the text added/modified>",
         "action": "added|modified|removed"
       }}
     ],
     "links": [
       {{
         "message_chunk_id": "msg_{message_id}_c0",
         "summary_chunk_id": "sum_{message_id}_ch0",
         "commit_sha": "WILL_BE_FILLED",
         "confidence": 0.95
       }}
     ]
   }}
   ```

6. **Commit**:
   - Stage: `messages/{message_id}.md`, `summary.md`, `.verachat/chunks/{message_id}.json`
   - Commit message: "Process message {message_id}: <brief description>"

## Message to Process

```
{message}
```

Remember: Make minimal, surgical edits. Track every chunk and its link to summary changes.
"""

# Prompt for extracting chunks from an existing message (for rebuilding)
EXTRACT_CHUNKS_PROMPT = """Analyze this message and extract semantic chunks.

For each distinct topic/item in the message, identify:
- chunk_type: "decision", "action", "info", or "question"
- content: the relevant text
- span_start: character position where this chunk starts
- span_end: character position where this chunk ends

Return as JSON array:
```json
[
  {{
    "chunk_type": "decision",
    "content": "We decided to use React",
    "span_start": 0,
    "span_end": 24
  }}
]
```

Message:
```
{message}
```
"""

# Prompt for analyzing summary diff and linking to message chunks
LINK_CHUNKS_PROMPT = """Given these message chunks and summary diff, identify which message chunks caused which summary changes.

Message chunks:
{message_chunks}

Summary diff (lines added/modified):
{summary_diff}

Return links as JSON array:
```json
[
  {{
    "message_chunk_id": "msg_001_c0",
    "summary_chunk_id": "sum_001_ch0",
    "confidence": 0.95
  }}
]
```

Only link chunks that have a clear causal relationship.
"""
