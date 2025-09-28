---
status: not yet implemented
---
# Design for Open Command

The `open` command takes either a paper id or a paper number and launches the platform's pdf viewer with the paper's
downloaded pdf.

## Command argument
The command requires one argument, either an arxiv paper id (e.g. "2107.03374v2") or an positive integer paper number.
See [Design for specifying papers on commands](command-arguments.md) for the common design for paper argument processing.

## Specifying the PDF viewer
The path to a program to view PDFs is specified via the `PDF_VIEWER` environment variable.
