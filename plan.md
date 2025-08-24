# Plan

This is the development plan for the project.
The overall objective is to build a chatbot agent that can aid in keeping up with the
latest research in generative AI, as published on arxiv.org. The interface
to the agent is a command line shell, using the `rich` python library for formatting.

## User stories
These are the high level operations for the agent.

1. Find, download, index, and summarize papers from Arxiv.
   * The papers are found using a simple keyword search, with refinement from the user.
   * Summaries are created using a specific prompt and can be optionally refined from the user.
2. View the content of the repository
   * List the set of papers that have been indexed.
   * View individual papers and summaries
3. Semantic search over the papers, with summarized answers and references to specific paper pages.
   * This uses the index chunks and metadata.
4. Deep research over the papers
   * Use semantic search over the summaries to obtain high level information
   * Detailed analysis uses semantic search over the document chunks.
5. Maintenance of the paper repository
   * Can re-index entire repository
   * Can selectively re-index and or re-summarize individual papers on demand
   * Pdfs, extracted text, and summaries are kept and reused across requests. If missing, they will be
     re-generated on demand.

## Development plan

1. [x] Create the basic chatbot
2. [ ] Review workflow.py and refactor it to make it clearer
3. [ ] Refactor the chatbot commands to more clearly save context between requests
4. [ ] Add view summary command (use cae 2)
5. [ ] Finish the RAG command (use case 3)
6. [ ] Implement deep research (use case 4)
7. [ ] Add any commands needed to finish use case 5 (maintenance)
8. [ ] Add intent detection in front of the commands, so that user can just provide natural text queries

## Specific tasks

### Workflow refactor

