---
status: partially implemented
---
# Design for specifying papers on commands

## Basic idea
Several commands in the chat interface operate on a specific paper:

- `list` - show all downloaded papers
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
   of the downloaded papers. This way of specifying a paper should work in any workflow state, even
   if `last_query_set` is empty.
    
## State management
The state management design has been specified in
[Workflow state machine and commands](workflow-state-machine-and-commands.md). That document
specifies which states a command can be run in. In general, if a positive integer paper number is provided,
that can only be used in states where `last_query_set` has been populated. For now, most commands will follow
the same restrictions when a paper id has been provided. An exception is `reindex-paper` which has been
specified to run from any state.

After `list`, `summarize`, `summary`, or `open` has been executed successfully successfully, the workflow
state should be adjusted as follows:

1. `last_query_set` is cleared (set to the empty list)
2. `selected_paper` is set to the paper corresponding to the argument of the command

The command `reindex-paper` is an exception - it does not change the workflow state by its execution.
This is because it is a maintenance command, so we don't want to interrupt the user's previous task
more than necessasry.

TODO: In a future refactoring, we may consider changing the state management logic. For example,
it should be possible to run a command that is given a paper id from any state. Also, we may
forego clearing `last_query_set` to allow the user to go back and pick another paper from the list.
For now, let's leave the logic as described in the workflow state management design.

## Edge cases / errors
Here are some specific cases that should result in an error message to the user:

1. If the `last_query_set` workflow state variable is empty, providing an integer paper number is an error.
2. If the `last_query_set` workflow state variable has N papers and the user specifies a value below 1 or
   above N, that is an error.
3. If the user provides something that looks like a arxiv paper id, but it doesn't correspond to a downloaded
   paper, that is an error.
4. If the user provides an arxiv paper id without a version (e.g. "2107.03374"), and only one version of
   that paper has been downloaded, select the downloaded paper. If there is more than one version of the
   paper that has been downloaded (e.g. "2107.03374v1" and "2107.03374v2"), providing an error message asking
   the user to specify a version.
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
command as an argument to the argument-processsing function (see below).

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

## Implementation
There should be a common function for parsing the command arguments that does the validation and returns the
specified paper id (or paper metadata object if that makes more sense). That function should have unit tests.
