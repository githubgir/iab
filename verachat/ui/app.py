"""
VeraChat PoC UI - Streamlit Application

A proof-of-concept UI demonstrating:
- Chat pane (left) with messages
- Summary pane (right) with version tracking
- Bidirectional highlighting between messages and summary
"""

import streamlit as st
from pathlib import Path
import json
import os
from typing import Optional

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from verachat.sqlite import VeraChatDB
from verachat.models import HighlightData


# Page config
st.set_page_config(
    page_title="VeraChat",
    page_icon="📝",
    layout="wide",
)

# Custom CSS for highlighting
st.markdown("""
<style>
    .highlight-message {
        background-color: #fff3cd;
        border-left: 3px solid #ffc107;
        padding: 10px;
        margin: 5px 0;
        border-radius: 4px;
    }
    .highlight-summary {
        background-color: #d4edda;
        border-left: 3px solid #28a745;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .message-bubble {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #e9ecef;
    }
    .message-bubble:hover {
        background-color: #e9ecef;
        cursor: pointer;
    }
    .message-bubble.selected {
        background-color: #fff3cd;
        border-color: #ffc107;
    }
    .summary-line {
        padding: 2px 0;
    }
    .summary-line:hover {
        background-color: #f0f0f0;
        cursor: pointer;
    }
    .summary-line.highlighted {
        background-color: #d4edda;
    }
    .chunk-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 5px;
    }
    .chunk-decision { background-color: #007bff; color: white; }
    .chunk-action { background-color: #28a745; color: white; }
    .chunk-info { background-color: #6c757d; color: white; }
    .chunk-question { background-color: #ffc107; color: black; }
    .diff-added { color: #22863a; background-color: #f0fff4; }
    .diff-removed { color: #cb2431; background-color: #ffeef0; }
</style>
""", unsafe_allow_html=True)


def load_db() -> Optional[VeraChatDB]:
    """Load the SQLite database."""
    db_path = st.session_state.get("db_path")
    if db_path and Path(db_path).exists():
        return VeraChatDB(db_path)
    return None


def render_message(message: dict, is_selected: bool = False, highlight_spans: list = None):
    """Render a single message with optional highlighting."""
    content = message["content"]
    msg_id = message["id"]

    # Apply highlighting to spans
    if highlight_spans:
        # Sort spans in reverse order to not mess up indices
        sorted_spans = sorted(highlight_spans, key=lambda x: x[0], reverse=True)
        for start, end in sorted_spans:
            content = (
                content[:start] +
                f'<mark style="background-color: #fff3cd;">{content[start:end]}</mark>' +
                content[end:]
            )

    css_class = "message-bubble selected" if is_selected else "message-bubble"

    st.markdown(f"""
    <div class="{css_class}" onclick="window.parent.postMessage({{type: 'select_message', id: '{msg_id}'}}, '*')">
        <small style="color: #6c757d;">Message {msg_id}</small>
        <div style="margin-top: 5px;">{content}</div>
    </div>
    """, unsafe_allow_html=True)


def render_summary_with_highlights(summary_lines: list, highlight_line_ranges: list = None):
    """Render summary with highlighted lines."""
    highlighted_lines = set()
    if highlight_line_ranges:
        for start, end in highlight_line_ranges:
            for i in range(start, end + 1):
                highlighted_lines.add(i)

    html_lines = []
    for i, line in enumerate(summary_lines, 1):
        css_class = "summary-line highlighted" if i in highlighted_lines else "summary-line"
        # Escape HTML but preserve markdown-ish formatting
        escaped_line = line.replace("<", "&lt;").replace(">", "&gt;")
        html_lines.append(f'<div class="{css_class}" data-line="{i}">{escaped_line}</div>')

    st.markdown("\n".join(html_lines), unsafe_allow_html=True)


def main():
    st.title("📝 VeraChat")
    st.caption("Chat Summarisation Versioning and Tracking")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # Database path
        db_path = st.text_input(
            "SQLite Database Path",
            value=st.session_state.get("db_path", ""),
            placeholder="/path/to/verachat.db",
        )
        if db_path:
            st.session_state["db_path"] = db_path

        # Repo path (for live processing)
        repo_path = st.text_input(
            "Repository Path (optional)",
            value=st.session_state.get("repo_path", ""),
            placeholder="/path/to/repo",
        )
        if repo_path:
            st.session_state["repo_path"] = repo_path

        st.divider()

        # Load database
        db = load_db()
        if db:
            st.success(f"✅ Database loaded")
            messages = db.get_all_messages()
            st.info(f"📊 {len(messages)} messages")
        else:
            st.warning("⚠️ No database loaded")
            st.caption("Export from a VeraChat repo first:")
            st.code("vc.export_to_sqlite('verachat.db')")

    # Main content - two columns
    if not load_db():
        st.info("👆 Configure a database path in the sidebar to get started.")

        # Demo mode with sample data
        st.header("Demo Mode")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💬 Chat")
            demo_messages = [
                {"id": "001", "content": "We decided to use React for the frontend. John will lead the implementation."},
                {"id": "002", "content": "Budget approved at $50k. Timeline is Q2 2025."},
                {"id": "003", "content": "Question: Should we use TypeScript or JavaScript?"},
            ]
            for msg in demo_messages:
                render_message(msg)

        with col2:
            st.subheader("📋 Summary")
            demo_summary = """# Summary

## Decisions
- Use React for frontend (John leading)

## Action Items
- [ ] John: Start frontend implementation

## Budget
- Approved: $50k
- Timeline: Q2 2025

## Open Questions
- TypeScript vs JavaScript?
"""
            st.markdown(demo_summary)

        return

    # Real mode with database
    db = load_db()
    messages = db.get_all_messages()

    # Initialize session state
    if "selected_message" not in st.session_state:
        st.session_state["selected_message"] = None
    if "selected_line" not in st.session_state:
        st.session_state["selected_line"] = None

    col1, col2 = st.columns(2)

    # Chat pane
    with col1:
        st.subheader("💬 Chat")

        # Message selector
        selected_msg_id = st.selectbox(
            "Select message to highlight",
            options=[None] + [m["id"] for m in messages],
            format_func=lambda x: "None" if x is None else f"Message {x}",
            key="msg_selector",
        )

        if selected_msg_id != st.session_state.get("selected_message"):
            st.session_state["selected_message"] = selected_msg_id
            st.session_state["selected_line"] = None

        # Get highlight data if message selected
        highlight_data = None
        if selected_msg_id:
            highlight_data = db.get_highlight_for_message(selected_msg_id)

        # Render messages
        for msg in messages:
            is_selected = msg["id"] == selected_msg_id
            spans = highlight_data.message_spans if (highlight_data and is_selected) else None
            render_message(msg, is_selected=is_selected, highlight_spans=spans)

    # Summary pane
    with col2:
        st.subheader("📋 Summary")

        # Version selector (placeholder - would need commit history)
        st.caption("Current version")

        # Load summary from repo if available
        repo_path = st.session_state.get("repo_path")
        summary_content = ""
        if repo_path:
            summary_path = Path(repo_path) / "summary.md"
            if summary_path.exists():
                summary_content = summary_path.read_text()

        if not summary_content:
            summary_content = "# Summary\n\n_No summary loaded. Set repo path in sidebar._"

        summary_lines = summary_content.split("\n")

        # Get highlight lines
        highlight_lines = []
        if highlight_data:
            highlight_lines = highlight_data.summary_lines

        # Line number input for reverse highlighting
        line_input = st.number_input(
            "Click line # to highlight source",
            min_value=0,
            max_value=len(summary_lines),
            value=0,
            key="line_input",
        )

        if line_input > 0:
            reverse_highlight = db.get_highlight_for_line(line_input)
            if reverse_highlight.message_id:
                st.info(f"Line {line_input} came from Message {reverse_highlight.message_id}")
                # Update selection
                st.session_state["selected_message"] = reverse_highlight.message_id

        # Render summary
        render_summary_with_highlights(summary_lines, highlight_lines)

        # Show chunk details if message selected
        if highlight_data and highlight_data.message_chunks:
            st.divider()
            st.caption("Chunks from selected message:")
            for mc in highlight_data.message_chunks:
                badge_class = f"chunk-{mc.chunk_type}"
                st.markdown(
                    f'<span class="chunk-badge {badge_class}">{mc.chunk_type}</span> {mc.content[:50]}...',
                    unsafe_allow_html=True,
                )

    # Footer
    st.divider()
    st.caption("VeraChat PoC - Bidirectional highlighting between chat and summary")


if __name__ == "__main__":
    main()
