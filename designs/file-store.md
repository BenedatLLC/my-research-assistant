----
status: implemented
----

# File store design

## Paper states
Papers are uniquely identified by their Arxiv ids. A paper can have the following state associated with
it:

1. Paper metadata - obtained from Arxiv using `get_paper_metadata()`
2. Downloaded pdf - downloaded full text of the paper in pdf format
3. Extracted markdown - markdown extracted by parsing the pdf
4. Content index - semantic search index created from paper content, using
   parsing, chunking, and embedding
5. Summary - markdown summary of the paper, created by an LLM
6. Notes - human-provided notes about the paper, highlighting key points of interest. In markdown format.
7. Summary index - semantic search index created from summaries and notes, using chunking and embedding


## Storage
The files are stored under the directory identified by the environment variable `$DOC_HOME`. These
contain most of the state described in the previous section (except for the paper metadata). The
key directories under `$DOC_HOME` are as follows:

```
$DOC_HOME
     |
     |---- pdfs/                 - downloads of the full papers, in pdf format. Filenames have the
     |                             form PAPER_ID.pdf.
     |
     |---- paper_metadata/       - this contains json files for the paper metadata obtained from Arxiv
     |
     |
     |---- extracted_paper_text/ - this is the where markdown extracted from the pdfs is stored
     |                             Filenames have the form PAPER_ID.md.
     |
     |---- index/                - semantic search index created by LlamaIndex
     |
     |
     |---- summaries/            - llm-generated summaries of the papers. Filenames have the form
     |                             PAPER_NAME.md.
     |
     |---- notes/                - human-generated notes (not yet implemented)
     |
     |---- results/              - saved results from semantic searches and deep research
```

