---
status: implemented
---

# Design for improve command
The `improve` command refines a paper summary, a sem-search result, or a research result,
using the original paper content, the summary generated, and the feedback from the user. Details about
how this command interacts with the workflow state machine and state variables is at
`designs/workflow-state-machine-and-commands.md`.

## Expected flow for use after summarize command
This is the expected flow when used with finding and summarizing a paper:

1. User runs `find` to select candidate papers from the Arxiv site
2. User selects a paper to summarize from the result list using `summarize n`, where
   `n` is the number of the paper in the output or a paper id.
3. The `summarize` command does the following:
   a. Downloads the paper
   b. Indexes the paper
   c. Extracts markdown from the paper
   d. Sends the paper to an LLM with a prompt asking for a summary
   e. Saves and indexes the resulting summary
   f. Stores the summary in the `draft` state variable
   g. Returns the summary to the user
4. The user enters `improve <instructions>` with instructions on
   how to improve the summary
5. The `improve` command does the following:
   a. Loads the original paper content (markdown text) from disk at `extracted_paper_text/<paper_id>.md`
   b. Builds a prompt for the LLM including the original paper content,
      the summary produced in step 3 (stored in `draft`), and the instructions from the user.
   c. This prompt is sent to the LLM.
   d. When the response is received, it is stored in the `draft` state variable
      and also returned to the user.
6. User can run `improve` multiple times to iteratively refine the summary
7. User runs `save` to save the final improved summary to disk and index it

## Expected flow for use after sem-search and deep-research commands
This is the expected flow when used with semantic search (RAG) and deep research.

1. User runs the `sem-search` or `research` commands with a query.
2. The `sem-search` command finds relevant chunks and sends them to the LLM with the query
   and a prompt. The current design of the `research` command is described in
   `designs/research-command.md`. Either way, the final result is stored in the `draft`
   state variable and returned to the user.
3. The user enters `improve <instructions>` with instructions on
   how to improve the response
4. The `improve` command does the following:
   a. Builds a prompt for the LLM including the current content (from `draft`),
      the original user query (from `original_query` state variable), and the user's
      feedback.
   b. This prompt is sent to the LLM.
   c. When the response is received, it is stored in the `draft` state variable
      and also returned to the user.
5. User can run `improve` multiple times to iteratively refine the results
6. User runs `save` to save the final improved results to a file

## Design Requirements

### Prompt Templates
All LLM prompts should be stored as prompt templates under `src/my_research_assistant/prompts`.
The prompts for the improve command are:
- `improve-summary-v1.md` - For improving paper summaries (version 1 format)
- `improve-summary-v2.md` - For improving paper summaries (version 2 format)
- `improve-search-v1.md` - For improving semantic search results
- `improve-research-v1.md` - For improving research results

Prompts should not be intermixed with source code in the `.py` files.

### Invariants

**1. Prompt Variable Syntax**
- All prompt templates MUST use double-brace syntax `{{variable_name}}` for variable substitution
- Single braces `{variable_name}` will not be substituted and will appear as literal text in the prompt
- This is enforced by the `subst_prompt()` function in `prompt.py`

**2. Title Requirement for Summaries**
- All improved summaries MUST include the paper title as the first line
- The title MUST be formatted as a markdown level 1 header (starting with a single `#`)
- This requirement is explicitly stated in the prompt templates to ensure the LLM includes it
- The `insert_metadata()` function in `summarizer.py` will raise `SummarizationError` if no title is found

**3. Paper Text Loading for Summary Improvements**
- When improving summaries, the original paper text MUST be loaded from disk
- Paper text is stored at `extracted_paper_text/<paper_id>.md`
- The full paper text provides necessary context for the LLM to make informed improvements
- Empty or missing paper text will result in poor quality improvements

**4. Content Type Mapping**
- The `improve_content()` method requires a `content_type` parameter
- Content type MUST match the current state: "semantic search" for sem-search state, "research" for research state
- Content type determines which prompt template is used for improvement
- Invalid content types will trigger a fallback to generic improvement with a warning

**5. Save Command Availability**
- The `save` command MUST be available in the SUMMARIZED state
- This allows users to save improved summaries after iterative refinement
- The save handler uses the `draft` state variable which contains the latest improved content
- After saving, the state remains SUMMARIZED (does not transition)

## Implementation

### Summary

The `improve` command was implemented with support for three content types:
1. **Paper summaries** (after `summarize` command) - Uses paper text, previous summary, and feedback
2. **Semantic search results** (after `sem-search` command) - Uses current results, original query, and feedback
3. **Research results** (after `research` command) - Uses current results, original query, and feedback

The implementation follows the template-based prompt architecture with variable substitution.

### Key Components

**1. State Machine Updates** (`state_machine.py:115-118`)
- Added `save` command to SUMMARIZED state's valid commands
- Ensures users can save improved summaries after iterative refinement

**2. Chat Interface** (`chat.py`)
- `process_improve_workflow_command()` (lines 1029-1078):
  - Determines content type based on current state (summarized, sem-search, or research)
  - For summaries: Loads paper text from `extracted_paper_text/<paper_id>.md`
  - Calls appropriate workflow method with all required parameters
  - Updates `draft` state variable with improved content
  - Displays result to user with markdown rendering

- `process_save_command()` (lines 415-451):
  - Saves improved summaries from `draft` state variable
  - Indexes summary for semantic search
  - Displays success message with file location
  - Stays in summarized state (allows continued work)

**3. Workflow Runner** (`workflow.py`)
- `improve_summary()` (lines 789-806):
  - Takes paper metadata, current summary, paper text, and user feedback
  - Uses `summarize_paper()` with feedback and previous_summary parameters
  - Returns improved summary in result object

- `improve_content()` (lines 896-962):
  - Generic method for improving search/research results
  - Takes current content, feedback, content_type, and optional original_query
  - Selects appropriate prompt template based on content_type
  - Uses `subst_prompt()` for variable substitution
  - Returns improved content in ProcessingResult object

**4. Prompt Templates** (`src/my_research_assistant/prompts/`)

All prompt templates use double-brace syntax `{{variable_name}}` for variable substitution:

- **improve-summary-v1.md**:
  - Variables: `{{feedback}}`, `{{previous_summary}}`, `{{text_block}}`
  - Includes CRITICAL instruction to always include paper title
  - Structure: Key ideas, Implementation approach, Experiments, Related work

- **improve-summary-v2.md**:
  - Variables: `{{feedback}}`, `{{previous_summary}}`, `{{text_block}}`
  - Enhanced with "IMPORTANT FORMATTING REQUIREMENTS" section
  - Explicit requirement: First line MUST be paper title as `# Title`
  - Structure: What is the research, Contributions, How it works, Related work, Significance

- **improve-search-v1.md**:
  - Variables: `{{query}}`, `{{feedback}}`, `{{current_content}}`
  - Maintains search result structure with numbered paper references
  - Preserves citations, page numbers, and file paths

- **improve-research-v1.md**:
  - Variables: `{{query}}`, `{{feedback}}`, `{{current_content}}`
  - Maintains research structure with inline citations and detailed references
  - Prevents invention of new citations (only uses existing papers)

### Test Coverage

**State Machine Tests** (`tests/test_state_machine.py`):
- `test_flow_1_find_summarize_improve_notes` - Tests improve in summarized state
- `test_flow_2_find_summarize_save` - Tests save after summary
- `test_flow_3_list_summary_improve` - Tests improve from list workflow
- `test_flow_4_sem_search_improve_save` - Tests improve and save for semantic search
- `test_flow_5_research_save` - Tests save for research results

All tests pass ✅ (384 passed, 1 skipped)

### User Experience

After implementation, users can:
1. **Improve summaries multiple times**: `improve add more details` → `improve expand methodology section` → `save`
2. **Improve search results**: `sem-search <query>` → `improve give me more detail on characteristics` → `save`
3. **Improve research results**: `research <query>` → `improve add more citations` → `save`
4. **See proper progress messages**: "🔄 Improving summary based on feedback..." and "✨ Summary improved!"
5. **Save at any point**: `save` command works in summarized, sem-search, and research states
