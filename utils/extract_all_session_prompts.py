#!/usr/bin/env python3
"""
Extract and display all user prompts from Claude Code session files.

This script reads all session JSONL files from the Claude Code projects directory
and extracts the user prompts to help analyze patterns and effective working strategies.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path

def project_dir_to_claude_dir(project_path):
    """
    Convert a project directory path to the Claude session history directory name.

    Example:
        /Users/jfischer/code/my-research-assistant
        -> -Users-jfischer-code-my-research-assistant
    """
    abs_path = os.path.abspath(project_path)
    # Remove leading / and replace remaining / with -
    claude_dir_name = abs_path.replace('/', '-')
    return claude_dir_name

def extract_session_prompts(project_path, max_sessions=20):
    """Extract user prompts from Claude Code session files."""

    # Convert project path to Claude directory name
    project_name = project_dir_to_claude_dir(project_path)
    session_dir = Path.home() / '.claude' / 'projects' / project_name

    print(f"Project directory: {os.path.abspath(project_path)}")
    print(f"Claude session directory: {session_dir}\n")

    if not session_dir.exists():
        print(f"Session directory not found: {session_dir}")
        return

    sessions = sorted(session_dir.glob('*.jsonl'), key=os.path.getmtime, reverse=False)

    print(f"Found {len(sessions)} total sessions")
    print(f"Analyzing the {min(max_sessions, len(sessions))} earliest sessions\n")

    for i, session_file in enumerate(sessions[:max_sessions], 1):
        print(f"\n{'='*80}")
        print(f"SESSION {i}: {session_file.stem}")
        modified_time = datetime.fromtimestamp(os.path.getmtime(session_file)).isoformat()
        print(f"Modified: {modified_time}")
        print('='*80)

        user_messages = []
        with open(session_file) as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    if msg.get('type') == 'user':
                        content = msg.get('message', {}).get('content', '')
                        if isinstance(content, str) and content.strip():
                            user_messages.append(content)
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error processing line: {e}")
                    continue
         
        if user_messages:
            last_message = None
            for (i, msg) in enumerate(user_messages):
                print(f"\nPrompt #{i+1} ({len(user_messages[0])} chars):")
                print("-" * 80)
                # Show first 500 chars of first prompt
                prompt = user_messages[i][:500]
                if len(user_messages[i]) > 500:
                    prompt += "\n..."
                if prompt!=last_message:
                    print(prompt)
                else:
                    print("DUPLICATE...")
                print()
                last_message = prompt

            if len(user_messages) >= 1:
                print(f"\n[Session has {len(user_messages)} total user messages]")
        else:
            print("[No user messages found]")
        print()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extract and display user prompts from Claude Code session files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s /Users/jfischer/code/my-research-assistant
  %(prog)s ~/code/my-project --max-sessions 10
        """
    )
    parser.add_argument(
        'project_dir',
        help='Path to the project directory'
    )
    parser.add_argument(
        '--max-sessions',
        type=int,
        default=20,
        help='Maximum number of recent sessions to analyze (default: 20)'
    )

    args = parser.parse_args()
    extract_session_prompts(args.project_dir, max_sessions=args.max_sessions)
