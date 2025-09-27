---
status: implemented
---
# Validate-store command design

This is the design for the `validate-store` command -- a command to print the status
of the store for each downloaded paper. The command can be run from any workflow state and does not
change the current state.

The command should examine all papers that have PDFs in the `pdfs/` directory and report on the
various indexed and processed states for each paper.

## Output
The output of the `validate-store` command should be a table with a row for each downloaded paper id.
It should have the following columns:

- Paper id: the arXiv id for the paper
- Has Metadata: either ✅ or ❌ depending on whether there is a file at paper_metadata/PAPER_ID.json
- Content index chunks: The number of chunks for this paper in the content index (content ChromaDB instance). If there are none, show a "❌" instead.
- Has summary: either ✅ or ❌ depending on whether there is a file at summaries/PAPER_ID.md
- Has extracted paper text: either ✅ or ❌ depending on whether there is a file at extracted_paper_text/PAPER_ID.md
- Summary index chunks: the number of chunks for this paper in the summary index (summary ChromaDB instance, includes both summaries and notes). If there are none, show a "❌" instead.
- Has notes: either ✅ or ❌ depending on whether there is a file at notes/PAPER_ID.md

The content index and summary index refer to the separate ChromaDB instances maintained by `vector_store.py`:
- Content index: stores chunked PDF content from papers
- Summary index: stores chunked summaries and notes for semantic search


## Example output
Here is an example output:

```table
|              | Has      | Content      | Has     | Has extracted  | Summary      | Has   |
| Paper id     | Metadata | index chunks | summary | paper text     | index chunks | notes |
|--------------|----------|--------------|---------|----------------|--------------|-------|
| 2707.03374v2 |    ✅    |          50  |    ✅   |       ✅       |         20   |   ✅  |
| 2210.03629v3 |    ✅    |          24  |    ❌   |       ❌       |         ❌   |   ❌  |
| 2401.02777v2 |    ❌    |          ❌  |    ✅   |       ✅       |         10   |   ✅  |
```

