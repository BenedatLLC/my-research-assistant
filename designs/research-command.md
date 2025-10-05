---
status: not implemented
---
# Design for research command

The `research` command is provided a query similar to the `sem-search` command. However, rather than just doing
RAG (Retrieval Augmented Generation), it uses the layered information in the paper store to perform "deep research" --
intelligently using the different information sources in a logical sequence to build a comprehensive, synthesized, and
well-cited answer. This is done through a multi-stage agent that mimics the human research process by starting broad and
then diving deep for details. This method, often called a *Hierarchical RAG* (Retrieval-Augmented Generation) or
a *funnel strategy*, is more efficient and effective than querying all sources at once.

## Sources of content
There are four sources of content available to agents from the paper [file store](file-store.md):

1. Summaries for each paper available as text in markdown format (under summaries/)
2. The full content of each paper available as text in markdown format (under extracted_paper_text/)
3. A semantic search indexed over the summaries using chunked passages of the summaries (under index/)
4. A semantic search indexed over the full paper content using chunked passages of the papers (also under index/)

## The four-stage deep research approach
This approach breaks the task into distinct stages, ensuring high-quality retrieval before the final synthesis.
It utilizes the four sources of content listed above.

### Stage 1: Initial Scoping & Paper Identification
The first step is to quickly figure out which papers are relevant to the user's question.

**Action**: Perform a semantic search only on the summaries index (Source 3).

**Parameters**:
- Search target: Summary index (summaries + notes)
- Number of results: k=8 (retrieve top 8 summary chunks)
- Use MMR: Yes (alpha=0.5 for balanced relevance/diversity)
- Similarity cutoff: 0.5 (lower threshold for broader initial scoping)

**Why it works**: Summaries are information-dense. This search is fast and quickly identifies the top candidate papers without getting bogged down in the full text. It's like reading abstracts to create a shortlist.

**Output**: A ranked list of the most relevant papers (deduplicated by paper_id) and the specific summary passages that matched the query. Expect 5-8 unique papers from the 8 chunks retrieved.

### Stage 2: Deep Dive & Evidence Gathering
Now that you have a shortlist of relevant papers, you need to find the specific details within them to answer the question thoroughly.

**Action**: Use the original question to perform a semantic search only on the full paper content index (Source 4), filtered to only search within the shortlisted papers from Stage 1.

**Parameters**:
- Search target: Content index (full paper text), filtered by paper_ids from Stage 1
- Number of results: k=15 (retrieve top 15 content chunks from shortlisted papers)
- Use MMR: Yes (alpha=0.6 for higher relevance priority in detail gathering)
- Similarity cutoff: 0.6 (standard threshold for quality content)
- Query: Use original user query (no refinement needed - the paper filtering provides the scoping)

**Why it works**: This is a targeted deep dive. You're no longer searching your entire library, just the most promising documents. This retrieves the specific, detailed evidence (e.g., methodology details, specific results, or discussion points) needed for a robust answer.

**Output**: A collection of 10-15 highly relevant text chunks from the full content of the shortlisted papers, each with associated metadata (paper_id, page number extracted from chunk metadata).

### Stage 3: Synthesis & Citation Generation
This is where the magic happens. You provide the gathered evidence to a large language model (LLM) to construct the final answer.

**Action**: Pass the evidence chunks from Stage 2 into the context window of an LLM using a synthesis prompt.

**Prompt Template**: Use `prompts/research_synthesis_v1.md` with the following variables:
- `{{QUERY}}`: The original user research query
- `{{EVIDENCE_CHUNKS}}`: Formatted list of text chunks with metadata (chunk text, paper_id, page number)
- `{{CITATION_FORMAT}}`: The required citation format: `[PAPER_ID, page PAGE_NO]`

**Prompt Instructions** (to be included in template):
1. Synthesize the provided information into a single, coherent answer to the original question
2. Base the answer strictly on the provided text chunks and avoid outside knowledge
3. For every fact or opinion that comes from a specific paper, cite the specific source paper and page it came from
4. Use citation format: `[PAPER_ID, page PAGE_NO]` (e.g. `[2509.10446v1, page 5]`)
5. Statements or facts that cannot be traced back to the source papers should not be included
6. Organize the answer with clear structure using markdown headings and formatting

**Why it works**: By providing only the most relevant, pre-filtered information, you reduce noise and help the LLM focus on generating a high-quality, factual synthesis. The explicit instruction to cite is crucial for traceability.

**Output**: A synthesized answer in markdown format with inline citation markers and structured sections.

### Stage 4: Formatting & Source Linking
Finally, you clean up the model's output and make the citations useful for the end-user.

**Action**: Post-process the LLM's synthesized text to extract citations and build a reference section.

**Processing Steps**:
1. Parse inline citation markers using regex pattern: `\[(\d{4}\.\d{4,5}v?\d*),\s*page\s*(\d+)\]`
2. Extract unique paper IDs from all citations (deduplicated)
3. Load metadata for each cited paper (from paper_metadata directory)
4. Sort cited papers by ArXiv ID order for consistent reference numbering
5. Build "## References" section with format:
   ```
   1. PAPER_ID - TITLE
      Authors: AUTHOR_LIST
      Published: DATE
   ```
6. Append references section to the synthesized answer
7. Populate `last_query_set` state variable with cited paper IDs (in order)

**Reference Formatting**: Use existing formatting from `paper_manager.py` for consistency with other commands.

**Why it works**: This final step connects the synthesized answer back to the ground truth. Users can verify information, explore topics further, and easily navigate to specific papers using numbered references.

**Output**: The final markdown document with:
- Synthesized answer with inline citations
- Formatted references section
- Paper IDs ready for `last_query_set` population

## State management
This is covered in the design [Workflow state machine and commands](workflow-state-machine-and-commands.md).
The `research` command follows the same state management pattern as `sem-search`:

**State Transition**:
- **Start state**: ANY (can be run from any state)
- **End state**: `research` (if papers found) or `initial` (if no results)

**State Variables**:
- `last_query_set`: Set to list of paper IDs that were cited in the research answer (in ArXiv ID order)
- `selected_paper`: Set to None
- `draft`: Set to the synthesized research answer with citations and reference section
- `original_query`: Set to the user's research query (for use with `improve` command)

This allows users to:
- Use `save` to save the research results to a file
- Use `improve <feedback>` to refine the research answer
- Use `summary <number|id>` or `open <number|id>` to explore cited papers
- Start a new query with `find`, `sem-search`, `research`, or `list` 

## Error situations
Here are some error situations and how to handle them by stage:

**Stage 1 - Summary Search Failure**:
- If no papers are found in the summary index (no relevant summaries), report:
  `❌ No papers found relevant to query: "<query>". Try refining your search terms.`
- Transition to `initial` state and clear all state variables

**Stage 2 - Content Search Failure**:
- If shortlisted papers have no indexed content, report:
  `❌ No detailed content found in the selected papers. Papers may not be properly indexed.`
- Suggest running `rebuild-index` command
- Transition to `initial` state

**Stage 3 - Synthesis Failure**:
- If LLM synthesis fails (API error, timeout, etc.), report:
  `❌ Failed to synthesize research answer: <error details>`
- Allow user to retry or transition to `initial` state
- State variables should be cleared

**Stage 4 - Formatting Failure**:
- If citation parsing fails, proceed with answer but warn:
  `⚠️  Some citations could not be formatted correctly`
- Still transition to `research` state with partial results

**General Errors**:
- Network errors or unexpected failures should report the error and return to `initial` state
- All state variables should be cleared on error transitions

## Examples
In the examples below, we elide output lines that are not relevant to the example
via a line containing only ellipsis ("...").

### Example 1: Successful Research Query

```chat
You: research what is prompt engineering
🔍 Stage 1: Searching summaries for relevant papers...
   Found 6 relevant papers

📚 Stage 2: Gathering detailed evidence from 6 papers...
   Retrieved 14 content chunks

✍️  Stage 3: Synthesizing answer from evidence...

╭──────────────────────────────────── 📝 Research Results ────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                              What is Prompt Engineering?                                    ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                  │
│ # What is Prompt Engineering?                                                                    │
│                                                                                                  │
│ Prompt engineering is the practice of designing and refining input prompts to guide large       │
│ language models (LLMs) toward desired outputs [2301.12345v1, page 3]. It involves crafting      │
│ instructions, examples, and context that shape model behavior without modifying model            │
│ parameters [2302.67890v2, page 12].                                                              │
│                                                                                                  │
│ The key techniques include few-shot prompting, where examples are provided to demonstrate the   │
│ desired task [2301.12345v1, page 7], and chain-of-thought prompting, which encourages the      │
│ model to show its reasoning process [2303.11111v1, page 5]. These approaches have been shown   │
│ to significantly improve performance on complex reasoning tasks [2303.11111v1, page 15].        │
│                                                                                                  │
│ Recent work has explored automatic prompt optimization methods that use LLMs to generate and    │
│ refine prompts [2304.22222v1, page 9], as well as prompt tuning approaches that learn soft      │
│ prompts as continuous vectors [2302.67890v2, page 18].                                          │
│                                                                                                  │
│ ## References                                                                                    │
│                                                                                                  │
│  1. 2301.12345v1 - Prompt Engineering Techniques for Large Language Models                       │
│     Authors: Smith, J., Johnson, A., Williams, B.                                                │
│     Published: 2023-01-15                                                                        │
│                                                                                                  │
│  2. 2302.67890v2 - Language Model Prompting: Strategies and Applications                         │
│     Authors: Jones, M., Davis, K.                                                                │
│     Published: 2023-02-20                                                                        │
│                                                                                                  │
│  3. 2303.11111v1 - Chain-of-Thought Prompting in Neural Language Models                          │
│     Authors: Brown, T., Garcia, L., Martinez, C.                                                 │
│     Published: 2023-03-10                                                                        │
│                                                                                                  │
│  4. 2304.22222v1 - Automatic Prompt Optimization for LLMs                                        │
│     Authors: Anderson, R., Taylor, S.                                                            │
│     Published: 2023-04-05                                                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯

💡 Next steps:
• Use `save` to save these results
• Use `improve <feedback>` to refine the answer
• Use `summary <number>` to view paper summaries (e.g., `summary 1`)
• Use `open <number>` to view full papers (e.g., `open 2`)
You:
```

### Example 2: Research with Improvement

```chat
You: research how do transformers work
🔍 Stage 1: Searching summaries for relevant papers...
   Found 5 relevant papers

📚 Stage 2: Gathering detailed evidence from 5 papers...
   Retrieved 12 content chunks

✍️  Stage 3: Synthesizing answer from evidence...

╭──────────────────────────────────── 📝 Research Results ────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                How Do Transformers Work?                                    ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                  │
│ Transformers are neural network architectures based on self-attention mechanisms...              │
│ ...                                                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
You: improve add more details about the mathematical foundations
✍️  Improving research answer with your feedback...

╭──────────────────────────────────── 📝 Research Results ────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                How Do Transformers Work?                                    ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                  │
│ ## Mathematical Foundations                                                                      │
│                                                                                                  │
│ The transformer architecture uses scaled dot-product attention, computed as:                     │
│ Attention(Q,K,V) = softmax(QK^T/√d_k)V [1706.03762v5, page 4]                                   │
│ ...                                                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
You: save
💾 Saving research results...
✅ Research results saved to: /Users/jfischer/code/my-research-assistant/docs/results/how-do-transformers-work_2025-10-05_14-23-15.md
You:
```

### Example 3: No Results Found

```chat
You: research quantum computing applications in medieval literature
🔍 Stage 1: Searching summaries for relevant papers...
❌ No papers found relevant to query: "quantum computing applications in medieval literature". Try refining your search terms.
You:
```

### Example 4: Following Up on Research Results

```chat
You: research attention mechanisms in neural networks
🔍 Stage 1: Searching summaries for relevant papers...
   Found 7 relevant papers
...
╭──────────────────────────────────── 📝 Research Results ────────────────────────────────────────╮
│ ## References                                                                                    │
│  1. 1706.03762v5 - Attention is All You Need                                                     │
│  2. 1409.0473v7 - Neural Machine Translation by Jointly Learning to Align and Translate         │
│  3. 2010.11929v2 - An Attentive Survey of Attention Models                                       │
│ ...                                                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
You: summary 1
╭────────────────────────────────────────────────────── 📝 Response ──────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                         Attention is All You Need                                                ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                       │
│  • Paper id: 1706.03762v5                                                                                             │
│  • Authors: Ashish Vaswani, Noam Shazeer, et al.                                                                      │
│ ...                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
You: open 2
╭────────────────────────────────────────────────────── 📝 Response ──────────────────────────────────────────────────────╮
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                        Paper Content: 1409.0473v7                                                 ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                       │
│ PDF Location: /Users/jfischer/code/my-research-assistant/docs/pdfs/1409.0473v7.pdf                                    │
│ Paper has been opened using PDF viewer /usr/bin/open                                                                  │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
You:
```

## Implementation

### Architecture and Files

**Workflow Implementation** (`src/my_research_assistant/workflow.py`):
- Implement as a new method in the existing `ResearchAssistantWorkflow` class or as a dedicated LlamaIndex workflow
- Method signature: `async def research_query(query: str, file_locations: FileLocations) -> QueryResult`
- Returns structured `QueryResult` with success status, papers, paper_ids, content (synthesized answer), and message

### New Functions Required

#### 1. Summary Index Search (`src/my_research_assistant/vector_store.py`)
```python
def search_summary_index(
    query: str,
    k: int = 8,
    file_locations: FileLocations = FILE_LOCATIONS,
    use_mmr: bool = True,
    similarity_cutoff: float = 0.5,
    mmr_alpha: float = 0.5
) -> list[SearchResult]:
    """
    Search the summary index for papers matching the query.
    Returns search results from summaries and notes.
    Similar to search_index() but targets the summary index instead of content index.
    """
```

#### 2. Filtered Content Search (`src/my_research_assistant/vector_store.py`)
```python
def search_content_index_filtered(
    query: str,
    paper_ids: list[str],
    k: int = 15,
    file_locations: FileLocations = FILE_LOCATIONS,
    use_mmr: bool = True,
    similarity_cutoff: float = 0.6,
    mmr_alpha: float = 0.6
) -> list[SearchResult]:
    """
    Search the content index for papers matching the query,
    filtered to only search within the specified paper_ids.

    Implementation: Use ChromaDB's where filter with paper_id metadata:
    where={"paper_id": {"$in": paper_ids}}
    """
```

#### 3. Research Synthesis (`src/my_research_assistant/workflow.py`)
```python
async def synthesize_research_answer(
    query: str,
    evidence_chunks: list[SearchResult],
    file_locations: FileLocations
) -> str:
    """
    Use LLM to synthesize a research answer from evidence chunks.

    - Loads prompt template from prompts/research_synthesis_v1.md
    - Formats evidence chunks with metadata (text, paper_id, page)
    - Calls LLM with synthesis prompt
    - Returns synthesized markdown answer with inline citations
    """
```

#### 4. Citation Formatting (`src/my_research_assistant/paper_manager.py` or new module)
```python
def format_research_result(
    synthesized_answer: str,
    file_locations: FileLocations
) -> tuple[str, list[str]]:
    """
    Parse citations from synthesized answer and build reference section.

    Returns:
    - Complete formatted result (answer + references section)
    - List of cited paper IDs (for last_query_set)

    Steps:
    1. Extract paper IDs from inline citations using regex
    2. Load paper metadata for each cited paper
    3. Build formatted references section
    4. Append to synthesized answer
    5. Return final result and paper ID list
    """
```

### Prompt Template

**File**: `src/my_research_assistant/prompts/research_synthesis_v1.md`

```markdown
You are a research assistant helping to answer questions based on academic papers.

# Research Query
{{QUERY}}

# Evidence from Papers
Below are relevant excerpts from academic papers. Each excerpt includes the paper ID and page number.

{{EVIDENCE_CHUNKS}}

# Task
Synthesize a comprehensive answer to the research query using ONLY the provided evidence.

## Requirements
1. Write a clear, well-structured answer in markdown format
2. Cite every fact with the format {{CITATION_FORMAT}} (e.g., [2509.10446v1, page 5])
3. Do NOT include information not found in the evidence
4. Use markdown headings to organize the answer
5. Be thorough but concise

Write your answer below:
```

### Progress Reporting

As the `research` command executes, print progress information at each stage:

**Stage 1 - Summary Search**:
```python
print("🔍 Stage 1: Searching summaries for relevant papers...")
# After search completes:
print(f"   Found {num_papers} relevant papers")
```

**Stage 2 - Content Search**:
```python
print(f"📚 Stage 2: Gathering detailed evidence from {num_papers} papers...")
# After search completes:
print(f"   Retrieved {num_chunks} content chunks")
```

**Stage 3 - Synthesis**:
```python
print("✍️  Stage 3: Synthesizing answer from evidence...")
# No follow-up message - display results immediately after
```

**Stage 4 - Formatting** (silent, no output):
- Format citations and references
- Transition directly to displaying results

### Integration Points

**Chat Interface** (`src/my_research_assistant/chat.py`):
- Add `process_research_command(query: str)` method
- Call workflow's `research_query()` method
- Display formatted results in Rich panel
- Handle state transition via `state_machine.transition_to_research()`
- Update state variables: `last_query_set`, `draft`, `original_query`

**State Machine** (`src/my_research_assistant/state_machine.py`):
- `research` command already defined in state machine design
- Ensure transition logic properly sets state variables
- Handle error transitions to `initial` state

### Testing

**New Test File**: `tests/test_research_workflow.py`
- Test Stage 1: Summary index search returns correct papers
- Test Stage 2: Filtered content search only searches specified papers
- Test Stage 3: Synthesis produces properly formatted answer with citations
- Test Stage 4: Citation extraction and reference formatting
- Test full workflow: End-to-end research query
- Test error cases: No papers found, synthesis failures, etc.

### Dependencies

**No new external dependencies required** - uses existing:
- LlamaIndex for workflow orchestration
- ChromaDB for vector search with metadata filtering
- OpenAI LLM for synthesis (via existing models.py)
- Rich for terminal UI (via existing chat.py)
