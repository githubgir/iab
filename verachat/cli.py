#!/usr/bin/env python3
"""
VeraChat CLI - Command line interface for VeraChat.

Usage:
    verachat setup <name> <description> [--public]
    verachat process <message> [--repo PATH]
    verachat diff <message_number> [--repo PATH]
    verachat viz [--format FORMAT] [--last N] [--repo PATH]
    verachat export <db_path> [--repo PATH]
    verachat ui [--db PATH] [--repo PATH]
"""

import argparse
import sys
from pathlib import Path

from verachat.core import VeraChat


def cmd_setup(args):
    """Create a new VeraChat repository."""
    vc = VeraChat()
    result = vc.setup(args.name, args.description, private=not args.public)
    print(f"✅ Repository created!")
    print(f"   Path: {result['local_path']}")
    print(f"\n📝 Next step: {result['next_step']}")


def cmd_process(args):
    """Process a new message."""
    vc = VeraChat(repo_path=args.repo)
    result = vc.process(args.message)
    print(f"✅ Processed message {result.message_id}")
    print(f"   Commit: {result.commit_sha[:7]}")
    print(f"   Summary: +{result.lines_added} -{result.lines_removed} lines")
    if result.message_chunks:
        print(f"   Chunks: {len(result.message_chunks)}")
        for mc in result.message_chunks:
            print(f"     - [{mc.chunk_type}] {mc.content[:40]}...")


def cmd_diff(args):
    """Show diff for a specific message."""
    vc = VeraChat(repo_path=args.repo)
    message_id = f"{args.message_number:03d}"

    chunk_file = vc.get_chunk_file(message_id)
    if not chunk_file:
        print(f"❌ No chunk data found for message {message_id}")
        return

    print(f"Message {message_id} ({chunk_file.commit_sha[:7]})")
    print("=" * 50)

    print("\n📨 Message chunks:")
    for mc in chunk_file.message_chunks:
        print(f"  [{mc.chunk_type}] {mc.content}")

    print("\n📝 Summary changes:")
    for sc in chunk_file.summary_changes:
        action_symbol = "+" if sc.action == "added" else "-" if sc.action == "removed" else "~"
        print(f"  {action_symbol} L{sc.line_start}-{sc.line_end}: {sc.content}")

    print("\n🔗 Links:")
    for link in chunk_file.links:
        print(f"  {link.message_chunk_id} → {link.summary_chunk_id} ({link.confidence:.0%})")


def cmd_viz(args):
    """Visualize summary history."""
    vc = VeraChat(repo_path=args.repo)
    output = vc.visualize(output_format=args.format, last_n=args.last)
    print(output)


def cmd_export(args):
    """Export to SQLite database."""
    vc = VeraChat(repo_path=args.repo)
    vc.export_to_sqlite(args.db_path)
    print(f"✅ Exported to {args.db_path}")


def cmd_ui(args):
    """Launch the Streamlit UI."""
    import subprocess

    ui_path = Path(__file__).parent / "ui" / "app.py"

    cmd = ["streamlit", "run", str(ui_path)]

    # Pass config via environment or query params
    env = {}
    if args.db:
        env["VERACHAT_DB"] = args.db
    if args.repo:
        env["VERACHAT_REPO"] = args.repo

    print("🚀 Launching VeraChat UI...")
    subprocess.run(cmd, env={**env, **dict(__import__("os").environ)})


def main():
    parser = argparse.ArgumentParser(
        description="VeraChat - Chat Summarisation Versioning and Tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # setup
    setup_parser = subparsers.add_parser("setup", help="Create a new VeraChat repository")
    setup_parser.add_argument("name", help="Repository name")
    setup_parser.add_argument("description", help="Repository description")
    setup_parser.add_argument("--public", action="store_true", help="Make repo public")

    # process
    process_parser = subparsers.add_parser("process", help="Process a new message")
    process_parser.add_argument("message", help="The message to process")
    process_parser.add_argument("--repo", default=".", help="Repository path")

    # diff
    diff_parser = subparsers.add_parser("diff", help="Show diff for a message")
    diff_parser.add_argument("message_number", type=int, help="Message number")
    diff_parser.add_argument("--repo", default=".", help="Repository path")

    # viz
    viz_parser = subparsers.add_parser("viz", help="Visualize summary history")
    viz_parser.add_argument("--format", choices=["terminal", "html", "json"], default="terminal")
    viz_parser.add_argument("--last", type=int, help="Show only last N messages")
    viz_parser.add_argument("--repo", default=".", help="Repository path")

    # export
    export_parser = subparsers.add_parser("export", help="Export to SQLite")
    export_parser.add_argument("db_path", help="SQLite database path")
    export_parser.add_argument("--repo", default=".", help="Repository path")

    # ui
    ui_parser = subparsers.add_parser("ui", help="Launch the web UI")
    ui_parser.add_argument("--db", help="SQLite database path")
    ui_parser.add_argument("--repo", help="Repository path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "setup": cmd_setup,
        "process": cmd_process,
        "diff": cmd_diff,
        "viz": cmd_viz,
        "export": cmd_export,
        "ui": cmd_ui,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
