----
status: partially implemented
----

# User stories

These are the high level operations for the agent.

1. [x] Find, download, index, and summarize papers from Arxiv.
   * [x] The papers are found using google search, with a simple keyword search as fallback. When
     a paper has been downloaded, it is chunked and indexed for later semantic searches and
     deep research.
   * [x] Summaries are created using a specific prompt and can be optionally refined from the user.
   * [ ] Optionally, the user can add their own notes for a paper.
   * [x] The summaries and notes are indexed for use in deep research.
2. [x] View the content of the repository
   * [x] List the set of papers that have been indexed.
   * [x] View individual papers and summaries
3. [x] Semantic search over the papers, with summarized answers and references to specific paper pages.
   * This uses the index chunks and metadata.
4. [ ] Deep research over the papers
   * [ ] Use semantic search over the summaries to obtain high level information
   * [ ] Detailed analysis uses semantic search over the document chunks.
5. [x] Maintenance of the paper repository
   * [x] Can re-index entire repository
   * [x] Can selectively re-index and or re-summarize individual papers on demand
   * [x] Pdfs, extracted text, and summaries are kept and reused across requests. If missing, they will be
     re-generated on demand.
   * [x] Can remove a paper from the repository, including pdf, summary, and indexed data, etc. This is useful
     when multiple versions of the same paper have been included in the repository.

