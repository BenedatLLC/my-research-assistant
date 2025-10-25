# Development log

## TODO
* When indexing a file, be sure to skip steps that have already been completed. For example,
  it seems like summaries get re-indexed each time. Also, is the index truely idempotent?
  * We may want a --verbose option to print more details
* improve the deep research
* Finish the notes command
* chat interface with intent detection
* Handle "old-style" arxiv ids that contain a "/"

## Wednesday Oct 23, 2025

### Systematic Error Handling and Logging

Implemented comprehensive logging infrastructure and standardized error reporting across the research assistant.

**Context:** User wanted consistent error messages for users and detailed logging for troubleshooting, with command-line control over log output.

**What was added:**
- `logging_config.py` module with Rich terminal integration, file logging, and API key redaction
- CLI arguments for chat command: `--loglevel` (ERROR/WARNING/INFO/DEBUG) and `--logfile`
- Standardized error message format starting with ❌ prefix
- Automatic API key redaction showing first 6 and last 4 characters
- Session delimiters in log files for multi-run tracking
- LlamaIndex and OpenAI logging suppression

**Error reporting improvements:**
- Consistent ❌ prefix on all user-facing error messages
- Concise 1-3 line error messages with actionable information
- API errors from external services include full details
- Internal errors use simplified format

**Logging features:**
- Terminal format: Single-character level indicator (E/W/I/D) + message
- File format: ISO timestamp + level + message
- Logs appended to file (not overwritten) with session markers
- Context included in logs: paper ID, workflow state, substep information

**Test coverage:**
- 26 logging-specific unit tests
- Updated workflow tests for new error format
- All 361 tests passing

**Original user prompt:** "I want to make the error reporting and logging more systematic. Can you review the design at designs/error-handling-and-logging.md and see if you have any questions?"

## Monday Oct 21, 2025

### Improved Pagination with Single-Key Input

Replaced line-buffered pagination (requiring Enter key) with immediate single-keypress pagination for `list` and `open` commands.

**What was added:**
- New `pagination.py` module with `getch()` for single-character input using termios
- `TablePaginator` class for row-aware table pagination (list command)
- `TextPaginator` class for line-aware markdown pagination (open command)
- Terminal-aware sizing: ~80% initial display, ~45% scroll increments
- Graceful fallback when terminal doesn't support raw mode
- No mid-row breaks for table rows
- Cumulative display (content remains visible between scrolls)

**Key improvements:**
- SPACE key adds more content without requiring Enter
- Any other key exits immediately back to command mode
- Auto-exit when reaching end of content
- Terminal height detection for responsive pagination
- Better UX - matches user expectations for pagination controls

**Test coverage:**
- 38 tests: 33 unit tests + 5 integration tests
- All tests passing (286 total in test suite)

**Original user prompt:** "I'd like to change the pagination logic we have with the `list` and `open` commands. Currently, it is a little awkward... you actually have to enter the key AND enter to do that. This is because it is reading the buffered input in line mode. Is it possible to just read a single character?"

## Friday Oct 17, 2025

### Enhanced Find Command with Google Custom Search

Implemented Google Custom Search integration as primary paper discovery method with automatic ArXiv API fallback.

**Context:** ArXiv API keyword search had reliability issues. User requested enhanced find command using Google Custom Search for better quality and more reliable results.

**What was added:**
- Google Custom Search integration for paper discovery (10 results per query)
- Automatic version deduplication (selects latest when multiple versions found)
- Paper ID sorting for consistent numbering across commands (find, list, summary)
- Automatic fallback to ArXiv API when Google credentials not configured
- Credential detection based on GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables

**Key improvements:**
- More reliable search results compared to ArXiv API keyword search
- Higher quality relevance matching from Google
- Backward compatible - users without Google credentials still get working search
- Consistent paper numbering via ID sorting after semantic reranking

**Test coverage:**
- 29 total tests: 20 unit/integration tests, 9 E2E workflow tests
- All tests passing (248 total in test suite)

**Usage:** Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables to enable Google search. Without credentials, system automatically uses ArXiv API search.

**Original user prompt:** "Can you use the design-implementer subagent to implement the new find command design described in designs/find-command.md?"

## Tuesday Oct 14, 2025

* Implemented search api using Google Custom Search engine (google_search.py).

## Sunday Oct 12, 2025

### Three-Agent Development Workflow System

Implemented a comprehensive agent system for development workflow based on analysis of 20 Claude Code sessions.

**Context:** Sessions revealed patterns of broken tests (3 instances), documentation drift (3 manual update sessions), and testing gaps. User requested enhanced subagent system with written implementation plans, comprehensive testing, and automatic documentation sync.

**What was added:**
- Three specialized agents: design-implementer (coordinator), qa-engineer (testing), doc-maintainer (docs)
- Implementation plan phase - written in design docs before coding, requires user approval
- Test-driven development workflow with API-level testing preference
- Automatic documentation synchronization across README, CLAUDE, designs, and devlog
- Comprehensive testing documentation (TESTING_SUMMARY.md covering 22 test files, 150+ tests, 6 E2E flows)
- Complete workflow guide (DEVELOPMENT_WORKFLOW.md) with FAQ

**Key improvements:**
- Prevents broken tests through qa-engineer validation
- Eliminates documentation drift via auto-sync
- Captures development history with original prompts
- Provides clear implementation roadmap before coding

**Usage:** Just call design-implementer - it automatically delegates to qa-engineer and doc-maintainer.

### Model Configuration Support

Fixed embedding model configuration to use API keys from environment variables. Added test_models.py with 4 tests.

**Outcome:** All embedding tests passing. Support for custom model endpoints via environment variables.

## Monday Oct 6, 2025
* Prompted Claud to create a readme file:
  > I want to open source this project. Can you update the README.md file with the content to help new users
  > understand the purpose of the project, how to use it, and how it is structured? Be sure to include:
  > - what the project does and why
  > - Getting started
  >   - project file layout
  >   - pre-requisites
  >   - installation
  >   - running
  >   - example session
  > - Command reference
  > - Document store layout
  > - Implementation overview
  > - License
  > 
  > If you have any questions, be sure to ask me.

## Sunday Oct 5, 2025
* Wrote design for research command based on an initial prompt from Gemini
* Asked Claude to update the design, using the following prompt:
  > Can you review the design for the research command in designs/research-command.md? Is everything clear?
  > Are there more details that you need? Is it consistent with the other designs and current implementations?
* Implementation via:
  > Can you use the design-implementer subagent to implment the updated design at designs/research-command.md?
  Claude seemed to think that *it* was the Project Lead, not the user. It approved its own assumptions and I had
  to prompt it to continue.

## Saturday Oct 4, 2025
* Asked Claude to create an agent for me. Here's the prompt I gave it (which was edited by claude):
```
You are a senior developer implementing an design that extends an existing project.
You can work independently, but take direction from a project lead. When their design and/or
requests are unclear, you ask for clarificiation from the project lead. You write clean
code and test thoroughly, but do not over-engineer things. If you get stuck (e.g. you've
tried several options to make something work, and it still doesn't), you ask for help.

The designs for this project are markdown files in the directory designs/. The project lead
gives you a specific design that has not yet been implemented (or perhaps partially
implemented).  Given the design, please do the following:

1. Review the design document and let the project lead know if anything is unclear or
   if there are important edges cases that are not specified. In the process of reviewing
   the design, be sure to look at the other relevent design documents so that you understand
   how the new design fits in with the existing project.
2. The project lead will give you clarifications and feedback on your questions. Update
   the design based on this feedback.
3. Compare the design against the current implementation. 
4. Write a plan for the code changes needed to implement the design. If there are any questions you have, be
   sure to ask the project lead first, unless there are pretty clear assumptions you can make.
5. Update the plan (and the design, if necessary) based on the feedback from the project lead.
6. Implement the design per the plan. As you are implementing, add any unit tests needed to validate your
   changes. Repeatable unit tests under the tests/ subdirectory are preferred to one time checks. Fix any
   problems you find in the implementation.
7. Update the existing tests under tests/ and the implementation to make sure the existing unit tests still
   pass while keeping to the design documents.
8. Write any additional unit tests needed to ensure reasonable coverage of the new and old functionality and
   to ensure the design has been correctly implemented. Fix any issues encountered. If the design calls for
   specific test scenarios, make sure they are included.
9. Add (or update if it exists) the "Implementation" section of the design document, including a summary
   of how the design was implemented and noting any assumptions that were made.

At the end, double check that the design, implementation and tests are all consistent. If not go back and
fix things (asking the project lead for help). Finally, provide a summary to the project lead of what you did.
```
* Finished writing the design for the open command.
* Used the new agent to implement open command:
  > Use the design-implementer agent to implment the open command design described in designs/open-command.md.
* Wrote the design for the remove-paper command
* Used the agent to implement the command:
  > Can you use the design-implementer subagent to implement the design at designs/remove-paper-command.md?
* Ran into bug where a `summarize` after `find` using paper numbers was processing the wrong paper. This was
  because the find command returned results in order of relevance, but the internal store was sorting by
  paper id (per the design). Claude had trouble fixing this (kept getting connection errors), so went and
  used CoPilot. CoPilot was able to successfully fix the issue, but got stuck running unit tests.

## Sunday Sept 28, 2025
* Updated state management for paper command arguments. If you select a specific paper, it doesn't not clear
  the current query set *unless* that paper is not in the query set. I did this with Claude as follows:
  1. Described the desired changes and asked it to review the design documents for what would need to change
     in the design. Also told it to ask me for clarifications to the design.
  2. I provided the clarifications and asked it to update the design documents.
  3. I then asked it to proceed with the implementation, giving it steps 2 - 7 below.
* Wrote design and implementation for paper command arguments
* Here's the dev flow I used with the paper command arguments:
  1. Write design document
  2. Ask Claude to review design and point out gaps:
     > Can you review the design document for commands with paper arguments. It is located at
     > designs/command-arguments.md. Let me know if anything is unclear or there are edge cases I missed.
  3. Update design based on feedback
  4. Prompt Claude to do the implementation:
     > Ok, can you implment the design for paper command arguments found in designs/command-arguments.md?
     > Use the following steps:
     > 1. Review the latest design
     > 2. Compare the design against the current implementation
     > 3. Write a plan for the code changes needed to implement the design. If there are any questions you have, be
     >    sure to ask me first, unless there are pretty clear assumptions you can make.
     > 4. Implement the design per the plan
     > 5. Add unit tests needed to validate the new functionality and to make sure it matches the design
     > 6. Update the tests under tests/ and the implementation to make sure the existing unit tests still pass while
     >    keeping to the design documents
     > 7. Update the "Implementation" section of command-arguments.md, adding a summary of how the design was
     >    implemented and noting any assumptions that were made.
   5. Claude came back with some more clarification questions. Answered the questions, asked it to update the design
      document, and then continue with the implementation plan:
      > Thank you for the insightful questions. Here are my responses:
      > 1. In general, if the user specifies a paper id, ...
      > ...
      > Can you update the design document with this information and then continue with your implementation plan?
      

## Saturday Sept 27, 2025
### Added

### Fixed
* Summaries were not always being indexed
* Compound queries did not work (e.g. compare the Deepseek V3 and Kimi K2 models). Asked Claude to improve
  similarity search strategy - it added support for an MMR reranker. This took several tries for Claude
  to get it right - I had to ask it to create a unit test for my specific scenario.
* `summary 2` was printing the wrong summary because the `list` command was sorting papers but the workflow
  state variable was not sorted. Changed to keep the current query set in the workflow to always be sorted
  by paper id so that papers are displayed and accessed in a consistent order.


## Friday Sept 26, 2025

### Added
* `validate-store` command - created design doc, asked claude to indicate what's unclear, fixed, then implemented.


### Fixed
* Logic to tell if a document was indexed was wrong - it would say that something was indexed, when it wasn't
