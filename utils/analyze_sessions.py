#!/usr/bin/env python3
"""
Analyze Claude Code session patterns to identify effective workflows and improvement opportunities.

This script provides deeper analysis than extract_claude_session_prompts.py:
- Categorizes sessions by type (feature implementation, bug fix, design review, etc.)
- Measures session efficiency (prompts per outcome)
- Identifies common patterns and anti-patterns
- Generates structured output suitable for LLM analysis
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from collections import defaultdict
import re


def project_dir_to_claude_dir(project_path):
    """Convert a project directory path to the Claude session history directory name."""
    abs_path = os.path.abspath(project_path)
    claude_dir_name = abs_path.replace('/', '-')
    return claude_dir_name


def categorize_prompt(prompt_text):
    """
    Categorize a prompt based on its content.

    Returns: (category, subcategory, keywords)
    """
    text_lower = prompt_text.lower()

    # Design patterns
    if 'review' in text_lower and 'design' in text_lower:
        return 'design', 'review', ['design review', 'clarity', 'edge cases']
    if 'implement' in text_lower and 'design' in text_lower:
        return 'design', 'implement', ['design-implementer', 'agent']
    if 'update' in text_lower and 'design' in text_lower:
        return 'design', 'update', ['clarification', 'design update']

    # Bug patterns
    if any(word in text_lower for word in ['error', 'bug', 'fail', 'broken', 'issue']):
        has_error_output = '```' in prompt_text or 'traceback' in text_lower
        if has_error_output:
            return 'bug', 'with-context', ['error output', 'debugging']
        else:
            return 'bug', 'vague', ['no error output']

    # Agent patterns
    if 'design-implementer' in text_lower or 'qa-engineer' in text_lower or 'doc-maintainer' in text_lower:
        return 'agent', 'delegation', ['agent delegation']

    # Testing patterns
    if 'test' in text_lower and ('fail' in text_lower or 'error' in text_lower):
        return 'testing', 'fix-failures', ['test failures']
    if 'test' in text_lower and 'add' in text_lower:
        return 'testing', 'add-tests', ['test addition']

    # Documentation patterns
    if 'update' in text_lower and ('claude.md' in text_lower or 'readme' in text_lower or 'documentation' in text_lower):
        return 'documentation', 'update', ['doc update']

    # Implementation patterns (without design)
    if any(word in text_lower for word in ['implement', 'add', 'create']) and 'design' not in text_lower:
        return 'implementation', 'direct', ['direct implementation']

    # Questions/clarifications
    if prompt_text.strip().endswith('?'):
        return 'question', 'clarification', ['question']

    # Confirmation/approval
    if len(prompt_text) < 50 and any(word in text_lower for word in ['yes', 'ok', 'proceed', 'continue', 'approve']):
        return 'response', 'approval', ['approval']

    return 'other', 'unknown', []


def analyze_session(session_file):
    """
    Analyze a single session file.

    Returns dict with session metadata and analysis.
    """
    user_messages = []
    assistant_messages = []

    with open(session_file) as f:
        for line in f:
            try:
                msg = json.loads(line)
                msg_type = msg.get('type')

                if msg_type == 'user':
                    content = msg.get('message', {}).get('content', '')
                    if isinstance(content, str) and content.strip():
                        user_messages.append(content)
                elif msg_type == 'assistant':
                    content = msg.get('message', {}).get('content', '')
                    if isinstance(content, str):
                        assistant_messages.append(content)
            except (json.JSONDecodeError, Exception):
                continue

    # Categorize prompts
    prompt_categories = []
    for msg in user_messages:
        cat, subcat, keywords = categorize_prompt(msg)
        prompt_categories.append({
            'category': cat,
            'subcategory': subcat,
            'keywords': keywords,
            'length': len(msg)
        })

    # Determine session type based on prompt pattern
    session_type = determine_session_type(prompt_categories, user_messages)

    # Calculate metrics
    total_prompts = len(user_messages)
    avg_prompt_length = sum(len(m) for m in user_messages) / max(total_prompts, 1)

    return {
        'file': session_file.name,
        'modified': datetime.fromtimestamp(os.path.getmtime(session_file)),
        'total_prompts': total_prompts,
        'total_responses': len(assistant_messages),
        'avg_prompt_length': int(avg_prompt_length),
        'session_type': session_type,
        'prompt_categories': prompt_categories,
        'first_prompt': user_messages[0][:200] + '...' if user_messages and len(user_messages[0]) > 200 else user_messages[0] if user_messages else '',
        'prompts': user_messages  # Keep for detailed analysis
    }


def determine_session_type(prompt_categories, user_messages):
    """Determine overall session type based on prompt patterns."""
    if not prompt_categories:
        return 'empty'

    # Count category occurrences
    category_counts = defaultdict(int)
    for pc in prompt_categories:
        category_counts[pc['category']] += 1

    total = len(prompt_categories)

    # Agent-based workflow
    if category_counts.get('agent', 0) > 0:
        return 'agent-workflow'

    # Design workflow (review → update → implement)
    if category_counts.get('design', 0) >= 2:
        return 'design-workflow'

    # Bug fix session
    if category_counts.get('bug', 0) / total > 0.5:
        if any(pc['subcategory'] == 'with-context' for pc in prompt_categories):
            return 'bug-fix-good'
        else:
            return 'bug-fix-poor'

    # Testing session
    if category_counts.get('testing', 0) / total > 0.5:
        return 'testing-focus'

    # Documentation session
    if category_counts.get('documentation', 0) / total > 0.5:
        return 'documentation-update'

    # Long clarification sessions (lots of questions/responses)
    if (category_counts.get('question', 0) + category_counts.get('response', 0)) / total > 0.6:
        return 'clarification-heavy'

    return 'mixed'


def generate_summary_report(sessions, output_format='text'):
    """Generate a summary report of all sessions."""

    if output_format == 'json':
        return json.dumps({
            'total_sessions': len(sessions),
            'sessions': sessions
        }, indent=2, default=str)

    # Text report
    lines = []
    lines.append("=" * 80)
    lines.append("SESSION ANALYSIS SUMMARY")
    lines.append("=" * 80)
    lines.append("")

    # Overall stats
    total_sessions = len(sessions)
    total_prompts = sum(s['total_prompts'] for s in sessions)
    avg_prompts_per_session = total_prompts / max(total_sessions, 1)

    lines.append(f"Total sessions analyzed: {total_sessions}")
    lines.append(f"Total prompts: {total_prompts}")
    lines.append(f"Average prompts per session: {avg_prompts_per_session:.1f}")
    lines.append("")

    # Session type distribution
    session_types = defaultdict(int)
    for s in sessions:
        session_types[s['session_type']] += 1

    lines.append("SESSION TYPE DISTRIBUTION:")
    for stype, count in sorted(session_types.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_sessions) * 100
        lines.append(f"  {stype:25s}: {count:3d} sessions ({pct:5.1f}%)")
    lines.append("")

    # Efficiency analysis
    lines.append("EFFICIENCY ANALYSIS:")
    lines.append("")

    # Group by type and show stats
    type_groups = defaultdict(list)
    for s in sessions:
        type_groups[s['session_type']].append(s['total_prompts'])

    for stype in sorted(type_groups.keys()):
        prompts = type_groups[stype]
        avg = sum(prompts) / len(prompts)
        min_p = min(prompts)
        max_p = max(prompts)
        lines.append(f"  {stype}:")
        lines.append(f"    Average: {avg:.1f} prompts, Range: {min_p}-{max_p}")

    lines.append("")

    # Pattern identification
    lines.append("IDENTIFIED PATTERNS:")
    lines.append("")

    # Most efficient sessions (fewest prompts)
    efficient = sorted([s for s in sessions if s['total_prompts'] > 0],
                      key=lambda x: x['total_prompts'])[:5]
    lines.append("  Most efficient sessions (fewest prompts):")
    for s in efficient:
        lines.append(f"    {s['total_prompts']:2d} prompts - {s['session_type']:20s} - {s['modified'].strftime('%Y-%m-%d')}")
    lines.append("")

    # Longest sessions
    long = sorted(sessions, key=lambda x: x['total_prompts'], reverse=True)[:5]
    lines.append("  Longest sessions (most prompts):")
    for s in long:
        lines.append(f"    {s['total_prompts']:2d} prompts - {s['session_type']:20s} - {s['modified'].strftime('%Y-%m-%d')}")
    lines.append("")

    # Detailed session list
    lines.append("=" * 80)
    lines.append("DETAILED SESSION LIST")
    lines.append("=" * 80)
    lines.append("")

    for i, s in enumerate(sessions, 1):
        lines.append(f"Session {i}: {s['modified'].strftime('%Y-%m-%d')}")
        lines.append(f"  Type: {s['session_type']}")
        lines.append(f"  Prompts: {s['total_prompts']}")
        lines.append(f"  First prompt: {s['first_prompt'][:100]}...")
        lines.append("")

    return "\n".join(lines)


def generate_insights_report(sessions):
    """Generate insights and recommendations based on session analysis."""
    lines = []
    lines.append("=" * 80)
    lines.append("INSIGHTS AND RECOMMENDATIONS")
    lines.append("=" * 80)
    lines.append("")

    # Calculate metrics for recommendations
    agent_sessions = [s for s in sessions if s['session_type'] == 'agent-workflow']
    design_sessions = [s for s in sessions if s['session_type'] == 'design-workflow']
    bug_good = [s for s in sessions if s['session_type'] == 'bug-fix-good']
    bug_poor = [s for s in sessions if s['session_type'] == 'bug-fix-poor']
    clarification_heavy = [s for s in sessions if s['session_type'] == 'clarification-heavy']

    # 1. Agent usage effectiveness
    if agent_sessions:
        avg_agent_prompts = sum(s['total_prompts'] for s in agent_sessions) / len(agent_sessions)
        lines.append(f"1. AGENT USAGE (n={len(agent_sessions)}):")
        lines.append(f"   Average session length: {avg_agent_prompts:.1f} prompts")
        lines.append(f"   ✅ This is very efficient compared to manual implementation")
        lines.append(f"   Recommendation: Continue using agents for feature implementation")
        lines.append("")

    # 2. Design workflow effectiveness
    if design_sessions:
        avg_design_prompts = sum(s['total_prompts'] for s in design_sessions) / len(design_sessions)
        lines.append(f"2. DESIGN WORKFLOW (n={len(design_sessions)}):")
        lines.append(f"   Average session length: {avg_design_prompts:.1f} prompts")
        if avg_design_prompts > 15:
            lines.append(f"   ⚠️  Design sessions are quite long")
            lines.append(f"   Recommendation: Use Design Quality Checklist before requesting review")
        else:
            lines.append(f"   ✅ Design workflow is working well")
        lines.append("")

    # 3. Bug fixing effectiveness
    if bug_good or bug_poor:
        lines.append(f"3. BUG FIXING:")
        if bug_good:
            avg_good = sum(s['total_prompts'] for s in bug_good) / len(bug_good)
            lines.append(f"   With full error context (n={len(bug_good)}): {avg_good:.1f} prompts avg")
            lines.append(f"   ✅ Very efficient!")
        if bug_poor:
            avg_poor = sum(s['total_prompts'] for s in bug_poor) / len(bug_poor)
            lines.append(f"   Without error context (n={len(bug_poor)}): {avg_poor:.1f} prompts avg")
            lines.append(f"   ⚠️  Missing error context increases session length")
        if bug_good and bug_poor:
            efficiency_gain = (avg_poor - avg_good) / avg_poor * 100
            lines.append(f"   Impact: Providing full error output reduces prompts by {efficiency_gain:.0f}%")
        lines.append(f"   Recommendation: Always use Bug Report Template")
        lines.append("")

    # 4. Clarification-heavy sessions
    if clarification_heavy:
        avg_clarification = sum(s['total_prompts'] for s in clarification_heavy) / len(clarification_heavy)
        lines.append(f"4. CLARIFICATION-HEAVY SESSIONS (n={len(clarification_heavy)}):")
        lines.append(f"   Average session length: {avg_clarification:.1f} prompts")
        lines.append(f"   ⚠️  These sessions are inefficient (lots of back-and-forth)")
        lines.append(f"   Likely cause: Under-specified designs or missing context")
        lines.append(f"   Recommendation:")
        lines.append(f"   - Use Design Quality Checklist before review")
        lines.append(f"   - Provide complete context in initial prompts")
        lines.append(f"   - Consider breaking complex tasks into smaller pieces")
        lines.append("")

    # 5. Overall recommendations
    lines.append("5. TOP RECOMMENDATIONS:")
    lines.append("")

    # Find most vs least efficient patterns
    type_efficiency = {}
    for session_type in set(s['session_type'] for s in sessions):
        type_sessions = [s for s in sessions if s['session_type'] == session_type]
        if len(type_sessions) >= 2:  # Need at least 2 samples
            avg = sum(s['total_prompts'] for s in type_sessions) / len(type_sessions)
            type_efficiency[session_type] = (avg, len(type_sessions))

    if type_efficiency:
        sorted_efficiency = sorted(type_efficiency.items(), key=lambda x: x[1][0])

        lines.append("   Most efficient patterns:")
        for stype, (avg, count) in sorted_efficiency[:3]:
            lines.append(f"   ✅ {stype}: {avg:.1f} prompts avg (n={count})")

        lines.append("")
        lines.append("   Least efficient patterns:")
        for stype, (avg, count) in sorted_efficiency[-3:]:
            lines.append(f"   ⚠️  {stype}: {avg:.1f} prompts avg (n={count})")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Claude Code session patterns for workflow improvement.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s /Users/joe/code/my-research-assistant
  %(prog)s ~/code/my-project --max-sessions 30 --format json
  %(prog)s ~/code/my-project --insights-only
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
        help='Maximum number of sessions to analyze (default: 20, from oldest)'
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--insights-only',
        action='store_true',
        help='Show only insights and recommendations, not full summary'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Write output to file instead of stdout'
    )

    args = parser.parse_args()

    # Get session directory
    project_name = project_dir_to_claude_dir(args.project_dir)
    session_dir = Path.home() / '.claude' / 'projects' / project_name

    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}")
        return 1

    # Analyze sessions
    session_files = sorted(session_dir.glob('*.jsonl'), key=os.path.getmtime)

    print(f"Analyzing {min(args.max_sessions, len(session_files))} of {len(session_files)} total sessions...")
    print()

    sessions = []
    for session_file in session_files[:args.max_sessions]:
        analysis = analyze_session(session_file)
        sessions.append(analysis)

    # Generate reports
    output_lines = []

    if not args.insights_only:
        summary = generate_summary_report(sessions, args.format)
        output_lines.append(summary)
        output_lines.append("\n")

    if args.format == 'text':
        insights = generate_insights_report(sessions)
        output_lines.append(insights)

    output = "\n".join(output_lines)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Analysis written to: {args.output}")
    else:
        print(output)

    return 0


if __name__ == '__main__':
    exit(main())
