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

**Why it works**: Summaries are information-dense. This search is fast and quickly identifies the top candidate papers without getting bogged down in the full text. It's like reading abstracts to create a shortlist.

**Output**: A ranked list of the most relevant papers and the specific summary passages that matched the query.

### Stage 2: Deep Dive & Evidence Gathering
Now that you have a shortlist of relevant papers, you need to find the specific details within them to answer the question thoroughly.

**Action**: Use the original question, potentially refined with keywords from the summary passages found in Stage 1, to perform a semantic search only on the full paper content index (Source 4) of the shortlisted papers.

**Why it works**: This is a targeted deep dive. You're no longer searching your entire library, just the most promising documents. This retrieves the specific, detailed evidence (e.g., methodology details, specific results, or discussion points) needed for a robust answer.

**Output**: A collection of highly relevant text chunks from the full content of the papers, each with associated metadata (e.g., paper ID, section, page number).

### Stage 3: Synthesis & Citation Generation
This is where the magic happens. You provide the gathered evidence to a large language model (LLM) to construct the final answer.

**Action**: Pass the evidence chunks from Stage 2 into the context window of an LLM. The prompt should explicitly instruct the model to:

1. Synthesize the provided information into a single, coherent answer to the original question.
2. Base the answer strictly on the provided text chunks and avoid outside knowledge.
3. Cite every statement by referencing the specific source paper and page it came from. For example, the model could add a marker like [Source 1], [Source 2], etc., after each sentence or claim.

**Why it works**: By providing only the most relevant, pre-filtered information, you reduce noise and help the LLM focus on generating a high-quality, factual synthesis. The explicit instruction to cite is crucial for traceability.

**Output**: A synthesized paragraph with inline citation markers.

### Stage 4: Formatting & Source Linking
Finally, you clean up the model's output and make the citations useful for the end-user.

**Action**: Post-process the LLM's text output. Parse the inline citation markers (e.g., [Source 1]) and replace them with formatted references.

**Why it works**: This final step connects the synthesized answer back to the ground truth. The links can point to the full paper text (Source 2) or its summary (Source 1), allowing the user to verify the information and explore the topic further.

**Output**: The final, user-facing answer with clear links back to the source documents.

## State management
This is covered in the design [Workflow state machine and commands](command-arguments.md)

## Error situations
Here are some error situations and how to handle them:

## Examples
In this examples below, we elide output lines that are not relevent to the example
via a line containing only ellipsis ("...").

## Implementation
