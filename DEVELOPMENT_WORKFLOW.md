# Development Workflow

This document describes the recommended workflow for implementing new features and fixing bugs in the my-research-assistant project using Claude Code's agent system.

## Table of Contents

- [Overview](#overview)
- [The Three-Agent System](#the-three-agent-system)
- [Design-First Workflow](#design-first-workflow)
- [Implementation Workflow](#implementation-workflow)
- [Bug Fix Workflow](#bug-fix-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Tips for Effective Prompts](#tips-for-effective-prompts)

## Overview

The project uses a **design-first, test-driven approach** with three specialized Claude Code agents that work together to ensure high-quality implementations with comprehensive testing and synchronized documentation.

**Key Principles:**
1. **Design before code** - Create clear design documents first
2. **Plan before implementation** - Written plans get user approval
3. **Test-driven development** - Write tests first, then implement
4. **API-level testing** - Prefer testable interfaces over terminal I/O simulation
5. **Comprehensive testing** - Unit, integration, and end-to-end tests
6. **Documentation sync** - All docs automatically kept up-to-date

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

**Prompt:**
```
I found a bug: [describe the issue]

Here's the error output:
[paste complete error/stack trace]

I've verified that [what you've checked].

Can you fix this?
```

**What Claude will do:**
- Analyze the error
- Find the root cause
- Implement fix
- Add regression test
- Run all tests to ensure nothing else broken

### For Complex Bugs (Design Recommended)

1. Create a short design document explaining:
   - Current behavior (the bug)
   - Expected behavior
   - Root cause (if known)
   - Proposed fix approach

2. Use design-implementer agent to implement the fix

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
