# Development Workflow

This document describes the recommended workflow for implementing new features and fixing bugs in the my-research-assistant project using Claude Code's agent system.

## Table of Contents

- [Quick Start: When to Use Which Approach](#quick-start-when-to-use-which-approach)
- [Overview](#overview)
- [Common Session Patterns](#common-session-patterns)
- [The Three-Agent System](#the-three-agent-system)
- [Design-First Workflow](#design-first-workflow)
- [Implementation Workflow](#implementation-workflow)
- [Bug Fix Workflow](#bug-fix-workflow)
- [Session Management](#session-management)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Tips for Effective Prompts](#tips-for-effective-prompts)
- [Agent Refinement](#agent-refinement)

## Quick Start: When to Use Which Approach

Use this decision tree to quickly determine the best approach for your task:

```
┌─ Is this a new feature or command?
│  └─ Yes → Create design doc → Review design → Use design-implementer
│
├─ Is this a bug with clear error output?
│  └─ Yes → Report with FULL error context → Direct fix (see Bug Fix Template)
│
├─ Is this a complex state/architecture change?
│  └─ Yes → Create design doc → Extra review rounds → Use design-implementer
│
├─ Is this a simple documentation update?
│  └─ Yes → Request directly ("Update CLAUDE.md to reflect...")
│
├─ Is this exploratory (understanding codebase)?
│  └─ Yes → Ask Claude to investigate first → Then decide approach
│
└─ Is this an agent behavior refinement?
   └─ Yes → See Agent Refinement section
```

**Expected session lengths:**
- Simple tasks (doc updates, single bugs): **1-5 prompts**
- Feature with design-implementer agent: **3-8 prompts**
- Complex feature without agent: **15-25 prompts** (avoid - use agent instead!)
- Bug without full context: **5-11 prompts** (provide full context to reduce this)

## Overview

The project uses a **design-first, test-driven approach** with three specialized Claude Code agents that work together to ensure high-quality implementations with comprehensive testing and synchronized documentation.

**Key Principles:**
1. **Design before code** - Create clear design documents first
2. **Plan before implementation** - Written plans get user approval
3. **Test-driven development** - Write tests first, then implement
4. **API-level testing** - Prefer testable interfaces over terminal I/O simulation
5. **Comprehensive testing** - Unit, integration, and end-to-end tests
6. **Documentation sync** - All docs automatically kept up-to-date

## Common Session Patterns

Understanding typical session patterns helps set realistic expectations and choose the right approach.

### Pattern 1: Feature Implementation with Agent (RECOMMENDED)

**Characteristics:**
- 3-8 prompts total
- Clean, well-tested implementation
- Documentation automatically updated
- High success rate

**Flow:**
1. Create design document
2. Request design review: "Review designs/X.md for clarity and edge cases"
3. Provide clarifications (numbered responses)
4. Request update: "Update the design with these clarifications"
5. Delegate to agent: "Use design-implementer to implement designs/X.md"
6. Review implementation plan (optional)
7. Approve and proceed
8. Verify completed work

**Example from Session History:**
- Session 7: Open command - 7 prompts, clean implementation with tests
- Session 8: Research command - 6 prompts, comprehensive implementation

### Pattern 2: Bug Fix with Full Context

**Characteristics:**
- 1-3 prompts (with complete error output)
- 5-11 prompts (without complete context)
- Quick resolution with regression tests

**Flow (Effective):**
1. Report bug with FULL error output (see template below)
2. Claude fixes and adds regression test
3. Verify fix works

**Flow (Less Effective):**
1. Report bug vaguely
2. Claude asks for error output
3. You provide output
4. Claude asks for context
5. You provide context
6. Finally gets fixed
7-11. Multiple rounds of refinement...

**Key Success Factor:** Provide complete error output in first message!

### Pattern 3: Complex State Management Changes

**Characteristics:**
- Can become very long (15-25+ prompts) without good design
- Multiple clarification rounds
- May hit context limits

**How to Improve:**
- Use Design Document Quality Checklist (see below)
- Break into smaller designs if possible
- Extra review rounds on design before implementation
- Consider multiple sessions with exports

**Example from Session History:**
- Session 6: State management - 23 prompts (could have been shorter with better upfront design)

### Pattern 4: Simple Documentation or Configuration

**Characteristics:**
- 1-3 prompts
- Straightforward, no issues

**Flow:**
1. Request specific update
2. Claude makes changes
3. Done

### Key Insights

**What Reduces Session Length:**
- ✅ Complete error output in first message
- ✅ Using design-implementer agent for features
- ✅ Well-thought-out designs before review
- ✅ Numbered responses to questions
- ✅ Testing as you go

**What Increases Session Length:**
- ❌ Vague or incomplete error reports
- ❌ Implementing without design-implementer agent
- ❌ Under-specified designs
- ❌ Not running tests yourself
- ❌ Asking questions without context

## The Three-Agent System

### design-implementer (Coordinator)
- **When to use**: Implementing a design document from designs/
- **What it does**:
  - Reviews design and asks clarifying questions
  - Creates detailed implementation plan in design doc
  - Gets user approval before coding
  - Implements with test-driven development
  - Delegates to qa-engineer and doc-maintainer
  - Provides comprehensive summary

### qa-engineer (Testing Specialist)
- **When to use**: Delegated by design-implementer for comprehensive testing
- **What it does**:
  - Writes unit, integration, and E2E tests
  - Ensures API-level testability
  - Validates no existing functionality broken
  - Updates tests/TESTING_SUMMARY.md
  - Reports test coverage achieved

### doc-maintainer (Documentation Specialist)
- **When to use**: Delegated by design-implementer for documentation sync
- **What it does**:
  - Updates README.md for user-facing changes
  - Updates CLAUDE.md for architecture changes
  - Adds concise devlog.md entry (context, changes, outcomes)
  - Ensures consistency across all documentation
  - Marks design status as implemented

## Design-First Workflow

### Step 1: Create Design Document

1. Copy the template: `cp designs/TEMPLATE.md designs/new-feature.md`
2. Fill in the design document:
   - Overview and requirements
   - User stories / use cases
   - Architecture and design
   - Testing considerations
   - Edge cases and error handling

**Tips:**
- Be specific about user interactions
- Include example commands and outputs
- Document edge cases you can think of
- Reference related design documents

### Step 1.5: Design Document Quality Checklist

Before requesting a design review, verify your design is ready. This prevents long clarification sessions and ensures efficient reviews.

**Checklist - Is your design ready for review?**

- [ ] **Specific Examples Included**
  - At least 2-3 example commands with expected output
  - Example user workflows (step-by-step)
  - Sample data or scenarios

- [ ] **Edge Cases Identified**
  - What happens with invalid input?
  - What happens with missing data?
  - What happens with duplicate operations?
  - What happens in error conditions?

- [ ] **State Management Clear**
  - Which state machine states are involved?
  - What state transitions occur?
  - What happens to `last_query_set` and `selected_paper`?
  - When can the command be run (from which states)?

- [ ] **Integration Points Noted**
  - Which existing modules will be modified?
  - Which functions will be called?
  - What data structures will be used?
  - Any dependencies on external services?

- [ ] **Error Handling Specified**
  - What errors can occur?
  - What error messages should be shown?
  - How should errors be logged?
  - Any recovery mechanisms?

- [ ] **Testing Considerations**
  - Key scenarios to test
  - Expected test types (unit, integration, E2E)
  - What mocking might be needed?

**Why this matters:**
- ✅ Prevents 20+ prompt sessions (like Session 6)
- ✅ Reduces back-and-forth clarifications
- ✅ Results in better implementations
- ✅ Saves time for everyone

**If your design has gaps:**
- Iterate on the design doc first
- Get a colleague's review
- Consider breaking into smaller designs
- Add placeholder sections to be filled later (marked as TODO)

### Step 2: Review Design with Claude

**Prompt:**
```
Can you review the design document in designs/new-feature.md?
Let me know if anything is unclear or if there are edge cases I missed.
```

**What Claude will do:**
- Read the design thoroughly
- Ask clarifying questions
- Point out missing specifications
- Suggest edge cases to consider
- Note any conflicts with existing designs

**Your response:**
- Answer clarifying questions
- Add missing details
- Confirm or adjust proposed approaches

### Step 3: Update Design Based on Feedback

**Prompt:**
```
Thanks for the feedback. [Your responses to questions]

Can you update the design document with this information?
```

**What Claude will do:**
- Incorporate your responses into design
- Ensure clarity and completeness
- Mark design as ready for implementation

### Step 4: Implement with design-implementer Agent

**Prompt:**
```
Can you use the design-implementer agent to implement the design
in designs/new-feature.md?
```

**What happens:**
1. **Phase 1: Design Review**
   - Agent reads design and related documents
   - Asks final clarifying questions if needed
   - Updates design with confirmed details

2. **Phase 2: Implementation Planning** ⭐
   - Agent creates detailed plan IN the design document
   - Plan includes: steps, files, tests, risks, docs
   - Agent presents summary and asks: "Review plan or proceed?"
   - **You can review the plan in the design doc before proceeding**

3. **Phase 3: Implementation**
   - Agent writes tests first (TDD approach)
   - Implements to make tests pass
   - Ensures API-level testability
   - Runs tests continuously

4. **Phase 4: Testing**
   - Runs all existing tests (must pass!)
   - Delegates to qa-engineer for comprehensive coverage
   - qa-engineer adds E2E tests and validates nothing broken

5. **Phase 5: Documentation**
   - Completes Implementation section in design
   - Delegates to doc-maintainer
   - doc-maintainer syncs all docs and adds concise devlog entry

6. **Final Summary**
   - Comprehensive report of what was done
   - Test counts and status
   - Documentation updates
   - Any concerns or follow-ups

## Implementation Workflow

### Using design-implementer Agent

**Full command:**
```
Use the design-implementer agent to implement designs/feature-name.md
```

**Abbreviated command:**
```
Implement designs/feature-name.md
```

### Reviewing the Implementation Plan

When design-implementer asks if you want to review the plan:

**Option 1: Proceed immediately**
```
Proceed with implementation
```

**Option 2: Review first**
```
Let me review the plan first
```

Then review the "Implementation Plan" section in the design doc. If you have concerns:
```
I reviewed the plan. Can you [adjust step 3 / add more tests / etc.]?
```

### Monitoring Progress

The agent will update you at each phase:
- ✅ "Phase 1 complete: Design reviewed and clarified"
- ✅ "Phase 2 complete: Implementation plan created (5 steps, 12 test scenarios)"
- ✅ "Phase 3 complete: Implementation finished (tests passing)"
- ✅ "Phase 4 complete: qa-engineer added 8 E2E tests (all passing)"
- ✅ "Phase 5 complete: Documentation synchronized"

### When Implementation is Done

You'll receive a comprehensive summary with:
- Features implemented
- Files modified/created
- Test coverage (e.g., "18 tests: 6 unit, 8 integration, 4 E2E")
- All tests passing status
- Documentation updated
- Design status: implemented
- devlog.md updated with concise entry (context and outcomes)

## Bug Fix Workflow

### For Simple Bugs (No Design Needed)

**CRITICAL: Always provide COMPLETE error output!** Never summarize errors - this is the #1 factor in quick resolution.

**Bug Report Template (RECOMMENDED):**

```
I'm experiencing [brief 1-line description of the bug].

**Command executed:**
```
[exact command that failed, e.g., "summarize 2503.22738v1"]
```

**Full error output:**
```
[COMPLETE error output - never summarize!]
[Include full stack trace if available]
[Include any preceding warning messages]
```

**What I've verified:**
- [Check 1, e.g., "API key is set and valid"]
- [Check 2, e.g., "File exists at expected location"]
- [Check 3, e.g., "Same command worked yesterday"]

**My hypothesis (optional):** [Your theory about the cause]

Can you fix this and add a test to prevent regression?
```

**Example - Good Bug Report:**
```
I'm experiencing a KeyError when trying to summarize a paper.

**Command executed:**
```
summarize 2503.22738v1
```

**Full error output:**
```
Traceback (most recent call last):
  File "workflow.py", line 245, in process_paper
    metadata = load_metadata(paper_id)
  File "paper_manager.py", line 89, in load_metadata
    return data['title']
KeyError: 'title'
```

**What I've verified:**
- The paper PDF exists in docs/pdfs/
- The metadata file exists in docs/paper_metadata/
- I can open the metadata file and it has valid JSON

**My hypothesis:** The metadata file might be missing the 'title' field.

Can you fix this and add a test to prevent regression?
```

**Why this format works:**
- ✅ Complete context in one message
- ✅ Claude can immediately identify root cause
- ✅ Results in 1-3 prompt resolution
- ✅ Always gets a regression test

**Example - Poor Bug Report (DON'T DO THIS):**
```
The summarize command isn't working. Can you fix it?
```
- ❌ No error output (Claude has to ask)
- ❌ No context (Claude has to investigate)
- ❌ Results in 5-11 prompt back-and-forth

**What Claude will do:**
- Analyze the error
- Find the root cause
- Implement fix
- Add regression test
- Run all tests to ensure nothing else broken

**Expected outcome:**
- Fix implemented in 1-3 prompts
- Regression test added automatically
- Full test suite passing

### For Complex Bugs (Design Recommended)

1. Create a short design document explaining:
   - Current behavior (the bug)
   - Expected behavior
   - Root cause (if known)
   - Proposed fix approach

2. Use design-implementer agent to implement the fix

## Session Management

Managing long or complex sessions effectively prevents context limit issues and keeps work organized.

### When Sessions Get Long

**Warning signs you're approaching limits:**
- Session has 20+ prompts
- Claude starts repeating itself
- Context seems to be lost
- You're asked for information already provided

**What to do:**

1. **Export the conversation**
   ```
   /export
   ```
   This saves a text file of the conversation for reference.

2. **Document decisions in design doc**
   - Don't rely on chat history for important decisions
   - Update the design document with clarifications
   - Add a "Decisions" section if needed

3. **Consider breaking into phases**
   - Complete current phase (e.g., finish design review)
   - Start new session for implementation
   - Reference exported conversation if needed

4. **Checkpoint after major phases**
   - After design is finalized → Export and start fresh for implementation
   - After implementation → Start fresh for testing if needed
   - After core feature → Start fresh for enhancements

### Managing Complex Features

**For features that will require many changes:**

1. **Break design into smaller pieces**
   - Instead of one big "authentication system" design
   - Create: "authentication-core.md", "authentication-ui.md", "authentication-testing.md"
   - Implement sequentially

2. **Use multiple design-implementer sessions**
   - Implement core functionality first
   - Start new session for extensions
   - Each session stays focused and manageable

3. **Document progress in design doc**
   - Mark completed sections
   - Note what's left to do
   - Track decisions and outcomes

### Session History as Reference

**Your session history is valuable:**
- Located: `~/.claude/projects/-Users-jfischer-code-my-research-assistant/`
- Can be analyzed for patterns (like we just did!)
- Use `/export` to save important conversations
- Reference past solutions when facing similar issues

**Useful session management commands:**
```bash
# Export current conversation
/export

# View command history in session
history

# Clear screen (doesn't clear context)
clear
```

### Best Practices

**Start sessions focused:**
- One goal per session (implement X, fix Y, review Z)
- State the goal clearly at the start
- Avoid scope creep

**Keep momentum:**
- Address agent questions promptly
- Provide complete information
- Test as you go
- Don't let sessions drag on days

**Know when to split:**
- ✅ Split: Complex multi-day features
- ✅ Split: After hitting major milestones
- ✅ Split: When context seems lost
- ❌ Don't split: In the middle of active debugging
- ❌ Don't split: During agent execution
- ❌ Don't split: Before clarifying questions are answered

## Testing Guidelines

### Test-Driven Development

When implementing features:
1. **Write tests first** that will initially fail
2. **Implement** to make tests pass
3. **Refactor** while keeping tests green

### Three Levels of Testing

1. **Unit Tests**
   - Test individual functions/classes
   - Fast and isolated
   - Use mocks for dependencies

2. **Integration Tests**
   - Test component interactions
   - Example: State machine + Workflow
   - Use temp_file_locations fixture

3. **End-to-End Tests**
   - Test complete user workflows
   - Example: Find → Summarize → Read flow
   - Based on use cases from design

### API-Level Testing (Preferred)

✅ **Good - API Level:**
```python
def test_process_command():
    chat = ChatInterface()
    result = chat.process_command("find machine learning")
    assert result.state == "select-new"
```

❌ **Avoid - Terminal Simulation:**
```python
def test_terminal_interaction():
    # Don't simulate terminal I/O unless specifically testing I/O
    simulate_input("find machine learning")
    output = capture_output()
```

### Using Fixtures

Always use `temp_file_locations` for file operations:
```python
def test_download_paper(temp_file_locations):
    # This automatically uses temp directory
    # and cleans up after test
    download_paper(metadata, temp_file_locations)
```

### Mocking and Patching

**Critical Rule: Patch where the function is used, not where it's defined**

When using `@patch` in tests, always patch the function in the module where it's **imported and used**, not where it's originally defined.

❌ **Wrong - Patches where defined:**
```python
@patch('my_research_assistant.models.get_default_model')
def test_summarize(mock_model):
    # This won't work if summarizer imports get_default_model
    summarize_paper(text, metadata)
```

✅ **Correct - Patches where used:**
```python
@patch('my_research_assistant.summarizer.get_default_model')
def test_summarize(mock_model):
    # This works because summarizer.py uses get_default_model
    summarize_paper(text, metadata)
```

**Why this matters:**
- When `summarizer.py` does `from .models import get_default_model`
- It creates its own reference: `summarizer.get_default_model`
- You must patch that reference, not the original in `models.py`

**Quick check:**
- Look at the import in the file you're testing
- Patch `{that_module}.{function_name}`
- Example: If `chat.py` imports `get_default_model`, patch `chat.get_default_model`

### Checking Test Coverage

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_module.py

# Run tests matching pattern
pytest -k "test_search"
```

## Documentation Standards

### Documentation Files

- **README.md** - User-facing documentation
  - How to install and use
  - Command reference with examples
  - Getting started guide

- **CLAUDE.md** - Developer documentation
  - Architecture overview
  - Testing approach
  - Development conventions
  - Links to design documents

- **designs/*.md** - Feature specifications
  - Requirements and use cases
  - Design and architecture
  - Implementation details
  - Test coverage

- **devlog.md** - Development log
  - Chronological log of changes
  - Original user prompts
  - Implementation summaries
  - Outcomes and decisions

- **tests/TESTING_SUMMARY.md** - Test documentation
  - Test coverage by component
  - End-to-end workflows tested
  - Testing gaps and TODOs

### Automatic Documentation Updates

When using design-implementer agent:
- ✅ README.md updated for new commands
- ✅ CLAUDE.md updated for architecture changes
- ✅ Design doc gets Implementation section
- ✅ devlog.md gets concise entry (simple: 5 lines, major: 10-20 lines)
- ✅ tests/TESTING_SUMMARY.md updated with new tests

**You don't need to manually update these!** The doc-maintainer agent handles it.

**devlog.md format**: Length matches complexity. Simple change = 3-5 lines (what + outcome). Major feature = 10-20 lines (context + changes + outcomes). No file lists - use git log.

## Tips for Effective Prompts

Based on analysis of 20 successful sessions with this project:

### ✅ What Works Best

**1. Provide Complete Context**
```
I'm trying to [goal], but getting this error:

[Full error output with stack trace]

I've verified that [what you checked].
The config file shows [relevant config].

Can you help debug this?
```

**2. Reference Specific Files**
```
Can you update the function in src/vector_store.py:245
to handle the edge case where...
```

**3. Include Error Output**
- Always paste full error messages
- Include stack traces
- Show command that reproduced the issue

**4. Explain What You Know**
```
The tests are failing, but I know the API key works
because [evidence]. This suggests the issue is...
```

**5. Reference Design Documents**
```
Review the design in designs/command-arguments.md and
check for edge cases I might have missed.
```

### ❌ What to Avoid

**1. Vague Requests**
```
Can you make the search better?  ❌
```
Better:
```
Can you improve the semantic search to handle compound
queries like "compare model A vs model B"? ✅
```

**2. Summarized Errors**
```
I'm getting an authentication error  ❌
```
Better:
```
I'm getting this authentication error: [full error text] ✅
```

**3. Skipping Design Phase**
```
Just implement a new research command  ❌
```
Better:
```
I've created a design in designs/research-command.md.
Can you review it, then implement? ✅
```

### Iterative Development

For complex features, expect 15-25 message conversations:
- Ask clarifying questions
- Review intermediate results
- Provide feedback
- Test as you go

This is normal and leads to better outcomes!

## Example: Complete Feature Workflow

### Start to Finish Example

**Step 1: Create Design**
```bash
cp designs/TEMPLATE.md designs/notes-command.md
# Edit the file with requirements
```

**Step 2: Review Design**
```
Review designs/notes-command.md and check for unclear areas
or edge cases.
```

_[Claude asks clarifying questions]_

```
Good questions! Here are my answers:
1. Notes should be stored in...
2. The editor should be...
3. Edge case should be handled by...

Update the design with these details.
```

**Step 3: Implement**
```
Use the design-implementer agent to implement designs/notes-command.md
```

_[Agent creates plan and asks for review]_

```
The plan looks good, proceed with implementation.
```

_[Agent implements, tests, documents]_

**Step 4: Verify**
```bash
# Try the new feature
chat
> notes 2503.22738
```

**Step 5: Check Documentation**
```bash
# Check devlog entry
cat devlog.md

# Check updated README
grep "notes" README.md

# Check test summary
grep "notes" tests/TESTING_SUMMARY.md
```

**Done!** Feature is implemented, tested, and documented.

---

## Quick Reference

### Common Commands

```bash
# Implement a design
"Use design-implementer to implement designs/feature.md"

# Review a design
"Review designs/feature.md for clarity and edge cases"

# Fix a bug with full context
"Fix bug: [description] Error: [full output] Verified: [checks]"

# Run tests
pytest                  # All tests
pytest tests/test_X.py  # Specific file
pytest -k "pattern"     # Pattern match

# Check documentation
cat devlog.md                      # Development log
cat tests/TESTING_SUMMARY.md      # Test coverage
```

### Agent Responsibilities

| Agent | Primary Role | When to Use |
|-------|-------------|-------------|
| **design-implementer** | Coordinates implementation | Implementing design docs |
| **qa-engineer** | Comprehensive testing | Delegated by design-implementer |
| **doc-maintainer** | Documentation sync | Delegated by design-implementer |
| **self-improver** | Analyzes sessions, improves workflow | Every 10-20 sessions for continuous improvement |

### File Locations

- **Designs**: `designs/*.md`
- **Tests**: `tests/*.py`
- **Source**: `src/my_research_assistant/*.py`
- **Docs**: `README.md`, `CLAUDE.md`, `devlog.md`

---

## Frequently Asked Questions

### Do I need to call qa-engineer and doc-maintainer explicitly?

**No!** Just call design-implementer. It automatically delegates to the other agents.

**What you do:**
```
Use design-implementer to implement designs/new-feature.md
```

**What happens automatically:**
1. design-implementer handles review, planning, implementation
2. design-implementer **automatically delegates to qa-engineer** (Phase 4)
   - Writes comprehensive E2E tests
   - Validates nothing broken
   - Updates tests/TESTING_SUMMARY.md
3. design-implementer **automatically delegates to doc-maintainer** (Phase 5)
   - Updates README.md, CLAUDE.md
   - Adds concise devlog.md entry (5 lines for simple, 10-20 for major)
   - Syncs all documentation
4. design-implementer provides final comprehensive summary

**When to call them directly (rare):**
- `qa-engineer`: Only if adding tests outside a full implementation
- `doc-maintainer`: Only if docs got out of sync somehow

**99% of the time**: Just use design-implementer!

### What files should I reference?

- **This file** (`DEVELOPMENT_WORKFLOW.md`) - Complete workflow guide
- `CLAUDE.md` - Architecture and development conventions
- `designs/TEMPLATE.md` - Design document template
- `tests/TESTING_SUMMARY.md` - Test coverage documentation
- `.claude/agents/` - Agent definitions (for advanced users)

### How do I know if the agents are working?

You'll see messages like:
- "Delegating to qa-engineer for comprehensive testing..."
- "Delegating to doc-maintainer for documentation sync..."
- Final summary includes: "Tests added: 15 (5 unit, 7 integration, 3 E2E)"
- Check `devlog.md` - it will have a concise entry with context and outcomes

### What if I just want to fix a quick bug?

For simple bugs without a design document, just ask directly:
```
Fix bug: [description]
Error output: [paste full error]
I've verified: [what you checked]
```

Claude will fix it, add a regression test, and ensure all tests pass.

### Can I review the implementation plan before coding starts?

**Yes!** That's the whole point of Phase 2.

After creating the plan, design-implementer asks:
> "Would you like to review the full plan before I proceed, or should I continue with implementation?"

Options:
- Say "Proceed" to start coding immediately
- Say "Let me review the plan first" to check it
- The plan is written in the design doc's "Implementation Plan" section

---

## Questions?

- See `CLAUDE.md` for architecture details
- See `designs/TEMPLATE.md` for design document structure
- See `tests/TESTING_SUMMARY.md` for test coverage
- See session history: `~/.claude/projects/-Users-jfischer-code-my-research-assistant/`

For the best results:
1. ✅ Design first
2. ✅ Get plan approval
3. ✅ Use complete error messages
4. ✅ Reference specific files
5. ✅ Iterate and ask questions

## Agent Refinement

The three specialized agents can be refined based on your experience using them. This section explains how to provide feedback and update agent behavior.

### When to Refine Agents

**Consider refining when:**
- Agent consistently misses certain types of issues
- Agent asks too many or too few questions
- Agent's output format doesn't match your needs
- You notice patterns in what needs correcting
- Process could be more efficient

**Examples from project history:**
- Session 7: User refined design-implementer to state assumptions instead of asking about every detail
- Result: More efficient Phase 1, better use of experienced lead's judgment

### How to Refine Agents

**Step 1: Identify the issue**
```
I notice the [agent-name] agent [specific behavior].
For example, [concrete example from recent session].
```

**Step 2: Propose the improvement**
```
I'd like to change this so that [desired behavior].
Can you update the agent instructions?
```

**Step 3: Review the changes**
- Claude will show you the proposed changes
- Review carefully - these affect all future sessions
- Ask for adjustments if needed

**Step 4: Test in next session**
- Use the refined agent on next task
- Observe if the improvement worked
- Further refine if needed

### Example Refinement Session

**User observation:**
```
The design-implementer agent asked me very detailed questions about
UI elements (button text, spacing, etc.) that aren't critical to the
design. As an experienced lead, I can make these decisions during
implementation.

Can you update the agent to state assumptions about implementation
details and only ask questions about genuine ambiguities or
architectural decisions?
```

**Result:**
- Agent instructions updated
- Phase 1 becomes more efficient
- Still asks about critical issues
- Trusts lead's judgment on details

### Agent Files Location

```
.claude/agents/
├── design-implementer.md
├── qa-engineer.md
└── doc-maintainer.md
```

You can also edit these files directly, but asking Claude to update them ensures consistency and proper formatting.

### Best Practices for Refinement

**Do:**
- ✅ Be specific about the issue
- ✅ Provide examples from actual sessions
- ✅ Test changes before committing
- ✅ Refine incrementally (one change at a time)
- ✅ Document why you made the change

**Don't:**
- ❌ Make agents too permissive (remove quality checks)
- ❌ Remove important safety features (like "all tests must pass")
- ❌ Change multiple agents at once (hard to isolate effects)
- ❌ Remove the agent's ability to ask questions when truly unclear

### Common Refinements

**1. Adjusting question thresholds**
- Too many questions → Add guidance on when to state assumptions
- Too few questions → Add emphasis on asking about critical decisions

**2. Output format preferences**
- Add preferred templates
- Specify report structure
- Define what details to include/exclude

**3. Process adjustments**
- Change order of operations
- Add or remove checkpoints
- Adjust delegation timing

**4. Quality criteria**
- Adjust what "comprehensive" means for your project
- Define project-specific standards
- Add domain-specific checks

### Tracking Agent Evolution

**Document significant changes:**
- Note in devlog.md when agent behavior changes
- Include rationale for the change
- Track improvements over time
- Share insights with team

**Example devlog entry:**
```markdown
### Agent Refinement: design-implementer Phase 1

Refined design-implementer to state assumptions about implementation
details rather than asking detailed questions. This leverages the lead
developer's experience and reduces Phase 1 from 5-8 prompts to 2-3.

**Outcome:** More efficient design reviews while maintaining quality.
```

## Continuous Improvement with self-improver Agent

The self-improver agent provides systematic, evidence-based improvement of your workflow by analyzing past sessions.

### When to Use

**Recommended frequency:**
- After first 20 sessions (initial calibration)
- Every 10-20 sessions thereafter (periodic refinement)
- After major workflow changes (validate impact)
- When you notice patterns or inefficiencies

### How to Use

**Simple invocation:**
```
Use the self-improver agent to analyze recent sessions and suggest improvements.
```

**What the agent does:**

1. **Analyzes sessions** using `utils/analyze_sessions.py`
   - Categorizes session types (design, bug fix, agent workflow, etc.)
   - Measures efficiency (prompts per outcome)
   - Identifies patterns and anti-patterns

2. **Summarizes findings interactively**
   - What's working well (with evidence)
   - What's not working (with data)
   - Key insights
   - **Asks for your feedback** before proceeding

3. **Proposes specific improvements**
   - Exactly which files/sections to modify
   - What to add/change (with examples)
   - Expected impact
   - **Asks for your approval** before implementing

4. **Implements approved changes**
   - Updates DEVELOPMENT_WORKFLOW.md
   - Refines agent instructions
   - Adds templates or checklists
   - Reports progress

5. **Documents the learning**
   - Creates/updates session_analysis.md
   - Adds devlog.md entry
   - Proposes metrics to track

### Example Session

```
You: Use the self-improver agent to analyze the last 20 sessions

Agent: [Runs analysis script]

Agent: I've analyzed 20 sessions. Here's what I found:

What's Working Well ✅
1. Agent-workflow sessions average 4.2 prompts (very efficient!)
2. Bug fixes with full error output resolve in 2.3 prompts
[etc.]

What's Not Working Well ⚠️
1. Clarification-heavy sessions average 18.5 prompts (3x more!)
2. [etc.]

Questions for You:
1. [Question about priorities]
2. [Question about patterns]

You: [Answer questions]

Agent: Based on your feedback, I propose these improvements:

Improvement 1: Add "Design Readiness Checklist"
- Problem: 30% of design sessions are clarification-heavy
- Change: Add checklist to DEVELOPMENT_WORKFLOW.md
- Expected impact: Reduce clarification rounds
[etc.]

Do these align with your priorities? Should I proceed?

You: Yes, proceed with all improvements

Agent: [Makes changes]

Agent: ✅ Self-improvement cycle complete
- 5 improvements implemented
- Files modified: DEVELOPMENT_WORKFLOW.md, design-implementer.md
- Next review: After 20 more sessions
```

### What Gets Analyzed

The script examines:
- Session length (prompts per session)
- Session types (design, bug fix, testing, etc.)
- Efficiency patterns (which approaches work best)
- Common pain points (clarification loops, missing context)
- Success patterns (what leads to quick resolutions)

### Benefits

✅ **Evidence-based improvement** - Changes based on actual usage data, not theory

✅ **Identifies blind spots** - Patterns you might not notice in individual sessions

✅ **Continuous evolution** - Workflow improves with experience

✅ **Preserves what works** - Emphasizes successful patterns

✅ **Measurable impact** - Tracks metrics to validate improvements

### Analysis Tools

Two scripts support the self-improver:

**`utils/analyze_sessions.py`** - Statistical analysis
- Categorizes sessions by type
- Calculates efficiency metrics
- Generates insights and recommendations
- Can output to file for review

**`utils/extract_claude_session_prompts.py`** - Detailed prompt review
- Shows actual prompt text
- Good for understanding specific sessions
- Helps validate automated analysis

You can also run these scripts manually:
```bash
# Get statistical analysis
python utils/analyze_sessions.py . --max-sessions 20

# Save analysis to file
python utils/analyze_sessions.py . --max-sessions 20 --output analysis.txt

# Get insights only (no full summary)
python utils/analyze_sessions.py . --insights-only

# Review actual prompts
python utils/extract_claude_session_prompts.py . --max-sessions 10
```

### Self-Improvement Philosophy

The workflow isn't static - it should evolve based on how you actually work:
- **Learn from success**: Codify what works into templates and guidance
- **Learn from inefficiency**: Add guardrails to prevent common pitfalls
- **Adapt to your style**: Workflow should match your preferences
- **Measure impact**: Track whether changes actually help

The self-improver agent makes this evolution systematic and evidence-based rather than ad-hoc.
