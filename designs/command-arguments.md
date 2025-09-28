---
status: implemented
---
# Design for specifying papers on commands

## Basic idea
Several commands in the chat interface operate on a specific paper:

- `summarize` - generate the summary for a paper
- `summary` - show the summary for a paper
- `open` - open a paper in the system's PDF viewer (only partially implemented)
- `reindex-paper` - re-index a specific paper through all steps

Each of these takes a single argument specifying the paper. Currently the meaning of this argument is
inconsistent across commands. For each of these commands, we want there to be two ways of specifying the
paper:

1. If the `last_query_set` workflow state variable is currently set to one or more papers (after a
   `find`, `list`, `sem-search`, or `research` command), the user can specify a positive integer. This
    integer represents a 1-indexed reference to a paper in the the `last_query_set` list.
2. The user can provide an arxiv paper id ((e.g. "2107.03374v2"). The paper id should correspond to one
   of the downloaded papers in the entire repository (not just the current `last_query_set`). This way
   of specifying a paper should work in any workflow state, even if `last_query_set` is empty.
    
## State management
The state management design has been specified in
[Workflow state machine and commands](workflow-state-machine-and-commands.md). That document
specifies which states a command can be run in. The updated rules are:

1. **Integer paper numbers**: Can only be used in states where `last_query_set` has been populated
2. **ArXiv paper IDs**: Can be used from any state, regardless of `last_query_set` status

After `summarize`, `summary`, or `open` has been executed successfully, the workflow
state should be adjusted as follows:

1. **If the selected paper is in `last_query_set`**: `last_query_set` is preserved
2. **If the selected paper is not in `last_query_set`**: `last_query_set` is cleared (set to empty list)
3. `selected_paper` is set to the paper corresponding to the argument of the command

The command `reindex-paper` is an exception - it does not change the workflow state by its execution.
This is because it is a maintenance command, so we don't want to interrupt the user's previous task
more than necessary. `reindex-paper` accepts both integer numbers (when `last_query_set` exists) and
ArXiv IDs (from any state).

## Edge cases / errors
Here are some specific cases that should result in an error message to the user:

1. If the `last_query_set` workflow state variable is empty, providing an integer paper number is an error. However, providing an ArXiv paper ID is always valid regardless of the current state.
2. If the `last_query_set` workflow state variable has N papers and the user specifies a value below 1 or
   above N, that is an error.
3. If the user provides something that looks like a arxiv paper id, but it doesn't correspond to a downloaded
   paper, that is an error.
4. If the user provides an arxiv paper id without a version (e.g. "2107.03374"), and only one version of
   that paper has been downloaded in the entire repository, select the downloaded paper. If there is more
   than one version of the paper that has been downloaded (e.g. "2107.03374v1" and "2107.03374v2"), provide
   an error message asking the user to specify a version.
5. If the user does not provide any argument to the command or more than one argument, that is an error.
6. If the user provides an argument that is neither an integer nor an arxiv paper id, that is an error.
7. If, for any reason, the selected paper doesn't existing in the pdfs directory, that is an error.

In general, a specific error message should be provided for each error situation, so that the user understands
what they did wrong. Individual commands many have other error situations that should be handled by those commands.
For example if you try to run `summary` on a paper that has not yet been summarized, the user is informed that
the paper has not yet been summarized, and asks them whether to initiate summarization.

## Examples
For each example scenario, we show the chat transcript in triple-backtick blocks. A line containing only "..."
indicates elided content.

### List, followed by summary
Here, the user runs a `list` command and then requests the summary of paper number 7.
```chat
You: list
📋 Downloaded Papers

                                                        Page 1/1
┏━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ #   ┃ Paper ID      ┃ Title                                                  ┃ Authors                   ┃ Published ┃
┡━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 1   │ 2107.03374v2  │ Evaluating Large Language Models Trained on Code       │ Mark Chen, Jerry Tworek   │ 2021-07-… │
│     │               │                                                        │ ...                       │           │
│ 2   │ 2210.03629v3  │ ReAct: Synergizing Reasoning and Acting in Language    │ Shunyu Yao, Jeffrey       │ 2022-10-… │
│     │               │ Mo...                                                  │ Zhao...                   │           │
│ 3   │ 2306.11698v5  │ DecodingTrust: A Comprehensive Assessment of           │ Boxin Wang, Weixin Chen   │ 2023-06-… │
│     │               │ Trustwort...                                           │ ...                       │           │
│ 4   │ 2401.02777v2  │ From LLM to Conversational Agent: A Memory Enhanced    │ Na Liu, Liangyu Chen +4   │ 2024-01-… │
│     │               │ Ar...                                                  │ ...                       │           │
│ 5   │ 2402.05367v2  │ Principled Preferential Bayesian Optimization          │ Wenjie Xu, Wenbin Wang    │ 2024-02-… │
│     │               │                                                        │ +...                      │           │
│ 6   │ 2402.14860v4  │ Ranking Large Language Models without Ground Truth     │ Amit Dhurandhar, Rahul    │ 2024-02-… │
│     │               │                                                        │ N...                      │           │
│ 7   │ 2404.16130v2  │ From Local to Global: A Graph RAG Approach to          │ Darren Edge, Ha Trinh     │ 2024-04-… │
│     │               │ Query-Fo...                                            │ +8...                     │           │
│ 8   │ 2412.19437v2  │ DeepSeek-V3 Technical Report                           │ DeepSeek-AI, Aixin Liu    │ 2024-12-… │
│     │               │                                                        │ +...                      │           │
│ 9   │ 2502.04644v2  │ Agentic Reasoning: A Streamlined Framework for         │ Junde Wu, Jiayuan Zhu     │ 2025-02-… │
│     │               │ Enhanci...                                             │ +3...                     │           │
│ 10  │ 2502.09369v1  │ Language Agents as Digital Representatives in          │ Daniel Jarrett, Miruna    │ 2025-02-… │
│     │               │ Collecti...                                            │ P...                      │           │
└─────┴───────────────┴────────────────────────────────────────────────────────┴───────────────────────────┴───────────┘
📄 Page 1 of ` • Total: 10 papers
End of list

💾 **Storage Locations:**
• PDFs: `/Users/jfischer/code/my-research-assistant/docs/pdfs`
• Summaries: `/Users/jfischer/code/my-research-assistant/docs/summaries`
• Index: `/Users/jfischer/code/my-research-assistant/docs/index`

💡 **Next steps:**
• Use `summary <number|id>` to view existing summaries
• Use `open <number|id>` to view paper content
• Use `sem-search <query>` to search across papers
You: summary 7
╭──────────────────────────────────────────────────── 📝 Response ─────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                     From Local to Global: A GraphRAG Approach to Query-Focused Summarization                     ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                      │
│  • Paper id: 2404.16130v2                                                                                            │
│  • Authors: Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt, Dasha        │
│    Metropolitansky, Robert Osazuwa Ness, Jonathan Larson                                                             │
│  • Categories: Computation and Language, Artificial Intelligence, Information Retrieval, H.3.3; I.2.7                │
│  • Published: 2024-04-24 18:38:11+00:00                                                                              │
│  • Updated: 2025-02-19 10:49:41+00:00                                                                                │
│  • Paper URL: http://arxiv.org/abs/2404.16130v2                                                                      │
│                                                                                                                      │
│                                                                                                                      │
│                                                       Abstract                                                       │
│                                                                                                                      │
│ The use of retrieval-augmented generation (RAG) to retrieve relevant information from an external knowledge source
...
```
### Summary command with a paper id
```chat
You: summary 2404.16130v2
╭──────────────────────────────────────────────────── 📝 Response ─────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                     From Local to Global: A GraphRAG Approach to Query-Focused Summarization                     ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                      │
│  • Paper id: 2404.16130v2                                                                                            │
│  • Authors: Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt, Dasha        │
│    Metropolitansky, Robert Osazuwa Ness, Jonathan Larson                                                             │
│  • Categories: Computation and Language, Artificial Intelligence, Information Retrieval, H.3.3; I.2.7                │
│  • Published: 2024-04-24 18:38:11+00:00                                                                              │
│  • Updated: 2025-02-19 10:49:41+00:00                                                                                │
│  • Paper URL: http://arxiv.org/abs/2404.16130v2                                                                      │
│                                                                                                                      │
│                                                                                                                      │
│                                                       Abstract                                                       │
│                                                                                                                      │
│ The use of retrieval-augmented generation (RAG) to retrieve relevant information from an external knowledge source
...
```

### Paper with arxiv id that has not been downloaded or does not exist
Here is an example with `reindex-paper`. The proper error handling has already been implmented. The error handling
should be moved to a common function, and the other commands thus should provide a similar error message for edge
cases #3 and #7.

```chat
You: reindex-paper 2107.03379
🔄 Reindexing paper 2107.03379...
❌ Reindex failed: Paper 2107.03379 has not been downloaded. PDF not found at
/Users/jfischer/code/my-research-assistant/docs/pdfs/2107.03379.pdf
You:
```

The command should be included in the error message, as shown above. Thus, you will need to provide the attempted
command as an argument to the argument-processing function (see below).

### Invalid paper number after list, etc.
Here is an example of an error situation where the user performed a `list` and then ran `summary` providing
an out of bounds paper number.

```chat
You: list
📋 Downloaded Papers

                                                        Page 1/2
┏━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ #   ┃ Paper ID      ┃ Title                                                  ┃ Authors                   ┃ Published ┃
┡━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 1   │ 2107.03374v2  │ Evaluating Large Language Models Trained on Code       │ Mark Chen, Jerry Tworek   │ 2021-07-… │
│     │               │                                                        │ ...                       │           │
│ 2   │ 2210.03629v3  │ ReAct: Synergizing Reasoning and Acting in Language    │ Shunyu Yao, Jeffrey       │ 2022-10-… │
│     │               │ Mo...                                                  │ Zhao...                   │           │
│ 3   │ 2306.11698v5  │ DecodingTrust: A Comprehensive Assessment of           │ Boxin Wang, Weixin Chen   │ 2023-06-… │
│     │               │ Trustwort...                                           │ ...                       │           │
│ 4   │ 2401.02777v2  │ From LLM to Conversational Agent: A Memory Enhanced    │ Na Liu, Liangyu Chen +4   │ 2024-01-… │
│     │               │ Ar...                                                  │ ...                       │           │
│ 5   │ 2402.05367v2  │ Principled Preferential Bayesian Optimization          │ Wenjie Xu, Wenbin Wang    │ 2024-02-… │
│     │               │                                                        │ +...                      │           │
│ 6   │ 2402.14860v4  │ Ranking Large Language Models without Ground Truth     │ Amit Dhurandhar, Rahul    │ 2024-02-… │
│     │               │                                                        │ N...                      │           │
│ 7   │ 2404.16130v2  │ From Local to Global: A Graph RAG Approach to          │ Darren Edge, Ha Trinh     │ 2024-04-… │
│     │               │ Query-Fo...                                            │ +8...                     │           │
│ 8   │ 2412.19437v2  │ DeepSeek-V3 Technical Report                           │ DeepSeek-AI, Aixin Liu    │ 2024-12-… │
│     │               │                                                        │ +...                      │           │
│ 9   │ 2502.04644v2  │ Agentic Reasoning: A Streamlined Framework for         │ Junde Wu, Jiayuan Zhu     │ 2025-02-… │
│     │               │ Enhanci...                                             │ +3...                     │           │
│ 10  │ 2502.09369v1  │ Language Agents as Digital Representatives in          │ Daniel Jarrett, Miruna    │ 2025-02-… │
│     │               │ Collecti...                                            │ P...                      │           │
└─────┴───────────────┴────────────────────────────────────────────────────────┴───────────────────────────┴───────────┘
...
📄 Page 2 of 2 • Total: 19 papers
End of list

💾 **Storage Locations:**
• PDFs: `/Users/jfischer/code/my-research-assistant/docs/pdfs`
• Summaries: `/Users/jfischer/code/my-research-assistant/docs/summaries`
• Index: `/Users/jfischer/code/my-research-assistant/docs/index`

💡 **Next steps:**
• Use `summary <number|id>` to view existing summaries
• Use `open <number|id>` to view paper content
• Use `sem-search <query>` to search across papers
You: summary 20
❌ Invalid paper number '20'. Choose 1-19.
You:
```

### Preserved query set example
Here, the user runs a `list` command, then uses `summary` commands with both numbers and ArXiv IDs,
demonstrating that `last_query_set` is preserved when the selected paper is in the set.

```chat
You: list
📋 Downloaded Papers

                                                        Page 1/2
┏━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ #   ┃ Paper ID      ┃ Title                                                  ┃ Authors                   ┃ Published ┃
┡━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 1   │ 2107.03374v2  │ Evaluating Large Language Models Trained on Code       │ Mark Chen, Jerry Tworek   │ 2021-07-… │
│     │               │                                                        │ ...                       │           │
│ 2   │ 2210.03629v3  │ ReAct: Synergizing Reasoning and Acting in Language    │ Shunyu Yao, Jeffrey       │ 2022-10-… │
│     │               │ Mo...                                                  │ Zhao...                   │           │
│ 3   │ 2306.11698v5  │ DecodingTrust: A Comprehensive Assessment of           │ Boxin Wang, Weixin Chen   │ 2023-06-… │
│     │               │ Trustwort...                                           │ ...                       │           │
└─────┴───────────────┴────────────────────────────────────────────────────────┴───────────────────────────┴───────────┘
📄 Page 1 of 2 • Total: 19 papers
End of list
You: summary 1
╭──────────────────────────────────────────────────── 📝 Response ─────────────────────────────────────────────────────╮
│                                                                                                                      │
│                     Evaluating Large Language Models Trained on Code (Codex)                                        │
│                                                                                                                      │
│  • Paper id: 2107.03374v2                                                                                            │
│  • Authors: Mark Chen, Jerry Tworek, et al.                                                                          │
│                                                                                                                      │
│                                                       Summary                                                        │
│                                                                                                                      │
│ This paper introduces Codex, a large language model trained on code...
...
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
You: summary 2
╭──────────────────────────────────────────────────── 📝 Response ─────────────────────────────────────────────────────╮
│                                                                                                                      │
│                ReAct: Synergizing Reasoning and Acting in Language Models                                            │
│                                                                                                                      │
│  • Paper id: 2210.03629v3                                                                                            │
│  • Authors: Shunyu Yao, Jeffrey Zhao, et al.                                                                         │
│                                                                                                                      │
│                                                       Summary                                                        │
│                                                                                                                      │
│ This paper presents ReAct, a method that combines reasoning and acting...
...
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
You: summary 2404.16130v2
╭──────────────────────────────────────────────────── 📝 Response ─────────────────────────────────────────────────────╮
│                                                                                                                      │
│                From Local to Global: A Graph RAG Approach to Query-Focused Summarization                            │
│                                                                                                                      │
│  • Paper id: 2404.16130v2                                                                                            │
│  • Authors: Darren Edge, Ha Trinh, et al.                                                                            │
│                                                                                                                      │
│                                                       Summary                                                        │
│                                                                                                                      │
│ This paper introduces GraphRAG, a method for retrieval-augmented generation...
...
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
You: summary 3
╭──────────────────────────────────────────────────── 📝 Response ─────────────────────────────────────────────────────╮
│                                                                                                                      │
│           DecodingTrust: A Comprehensive Assessment of Trustworthiness in GPT Models                                │
│                                                                                                                      │
│  • Paper id: 2306.11698v5                                                                                            │
│  • Authors: Boxin Wang, Weixin Chen, et al.                                                                          │
│                                                                                                                      │
│                                                       Summary                                                        │
│                                                                                                                      │
│ This paper presents DecodingTrust, a comprehensive evaluation framework...
...
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
You:
```

In this example:
- After `summary 1` and `summary 2`, the `last_query_set` is preserved because papers 1 and 2 are in the original list
- After `summary 2404.16130v2` (ArXiv ID), the `last_query_set` would be cleared if this paper is not in the original list, or preserved if it is
- After the ArXiv ID usage, `summary 3` still works if the `last_query_set` was preserved

## Implementation
The design has been implemented with a common function for parsing command arguments that performs validation and returns
the specified paper metadata object. This function has comprehensive unit tests covering all edge cases.

### Design Clarifications
Based on implementation discussions, the following clarifications have been made:

1. **Repository-wide paper lookup**: When a user specifies a paper ID (with or without version), the system
   should search the entire repository of downloaded papers, not just the current `last_query_set`.

2. **Command name in error messages**: The common parsing function should take the command name as a parameter
   and include it in error messages for better user feedback.

3. **State management responsibility**: The common parsing function should not modify workflow state. Individual
   commands are responsible for calling state transition methods after successful execution.

4. **List command scope**: The `list` command should remain argument-free and show all downloaded papers.

### Implementation Summary

The design was implemented with enhanced state management and conditional query set preservation:

#### Enhanced Paper Argument Parsing in `paper_manager.py`

1. **`parse_paper_argument_enhanced(command_name, argument, last_query_set, file_locations)`**: Enhanced function that returns (PaperMetadata, error_message, was_resolved_by_integer) to enable conditional state management.

2. **`parse_paper_argument(command_name, argument, last_query_set, file_locations)`**: Original function maintained for backward compatibility, returns (PaperMetadata, error_message).

3. **`is_arxiv_id_format(text)`**: Validates whether a string matches ArXiv ID format using regex pattern `^\d{4}\.\d{4,5}(v\d+)?$`.

4. **`find_downloaded_papers_by_base_id(base_id, file_locations)`**: Finds all downloaded versions of a paper by its base ID (without version).

#### Conditional Query Set Preservation in `state_machine.py`

1. **`set_selected_paper(paper, draft_content, preserve_query_set=False)`**: Enhanced to conditionally preserve `last_query_set` based on `preserve_query_set` parameter.

2. **`is_paper_in_query_set(paper_id)`**: Helper method to check if a paper ID exists in the current `last_query_set`.

3. **Enhanced transition methods**: All paper selection transitions (`transition_after_summarize`, `transition_after_summary_view`, `transition_after_open`) now check if the selected paper is in the current query set and preserve it accordingly.

4. **Dynamic command validation**: `get_valid_commands()` now dynamically adds `summary` and `open` commands to SUMMARIZED state when `last_query_set` exists.

#### Updated Command Handlers in `chat.py`

The following command handlers were updated to use enhanced parsing and conditional preservation:

- **`process_summarize_command()`**: Uses `parse_paper_argument_enhanced()` and preserves query set if paper resolved by integer
- **`process_summary_command()`**: Uses `parse_paper_argument_enhanced()` and preserves query set if paper resolved by integer
- **`process_open_command()`**: Uses `parse_paper_argument_enhanced()` and preserves query set if paper resolved by integer
- **`process_reindex_paper_command()`**: Uses `parse_paper_argument_enhanced()` but doesn't change state per design

#### State Management Logic

**Query Set Preservation Rules:**
- **Preserve**: When paper is resolved by integer reference (in current query set)
- **Clear**: When paper is resolved by ArXiv ID (repository-wide lookup) and not in current query set
- **Preserve**: When paper is resolved by ArXiv ID and happens to be in current query set

**Workflow Examples:**
- `list` → `summary 1` → `summary 2` → `summary 3` (query set preserved throughout)
- `list` → `summary 2107.03374v1` (query set cleared if paper not in list, preserved if it is)
- `find "transformers"` → `summarize 1` → `summary 2210.03629v3` (behavior depends on whether ArXiv ID is in query set)

#### Comprehensive Testing in `test_paper_argument_parsing.py`

Enhanced test coverage with 24 test cases across 7 test classes:

1. **`TestEnhancedParsing`**: Tests the enhanced parsing function's resolution method tracking
2. **`TestStateVariablePreservation`**: Tests conditional query set preservation logic
3. **`TestStateMachineTransitions`**: Tests state transitions with new preservation behavior
4. **`TestDynamicCommandValidation`**: Tests dynamic command availability in SUMMARIZED state
5. **`TestPaperInQuerySetCheck`**: Tests helper method for query set membership
6. **`TestArXivIdFormatValidation`**: Tests ArXiv ID format validation (maintained)
7. **`TestDownloadedPaperFinding`**: Tests finding papers by base ID (maintained)

#### Key Implementation Features

1. **Backward Compatibility**: Original `parse_paper_argument()` function maintained alongside enhanced version
2. **Type Safety**: All functions use proper type hints and return structured tuples
3. **Error Consistency**: All error messages follow the pattern `❌ {command_name} failed: {specific_error_details}`
4. **State Consistency**: Query set preservation ensures numbered references remain valid across command sequences
5. **Comprehensive Validation**: Full ArXiv ID format validation, version handling, and file existence checking

#### Test Coverage Summary

- **66 total tests** covering all functionality
- **24 new tests** specifically for enhanced paper argument parsing
- **All existing tests updated** to work with new implementation
- **100% test pass rate** ensuring no regressions

The implementation successfully delivers the enhanced state management requirements with conditional query set preservation, enabling workflows like `list` → `summary 1` → `summary 2` while maintaining full backward compatibility and comprehensive error handling.
