---
status: implemented
---
# Design for command types
We can divide the commands in the chat interface in several (potentially overlapping) categories:

1. **Query commands**: these select a (sub)set of the papers
2. **Paper select commands**: these select and operate on a specific paper
3. **Paper refinement commands**: these operate on an already selected paper
4. **Maintenance commands**: these help in maintenance of the paper index
5. **Meta commands**: these provide information about the state of the chat engine or perform other meta-actions


```table
|                | Workflow state             | Effect on workflow           |
| Category       | variable preconditions     | state variables              | Commands
|----------------|----------------------------|------------------------------|----------------------------------
| Query commands | None                       | last_query_set=[P1,P2,...]   | find, list, sem-search, research
|----------------|----------------------------|------------------------------|-----------------------------------
| Paper select   | last_query_set=[P1,P2,...] | selected_paper=Pn            | summarize, summary, open, reindex-paper
| commands       |                            | (except for reindex-paper)   |
|----------------|----------------------------|------------------------------|-----------------------------------
| Paper          | selected_paper=Pn          | None                         | improve, notes, save
| refinement     |                            |                              |
| commands       |                            |                              |
|----------------|----------------------------|------------------------------|-----------------------------------
| Maintenance    | None, except that          | None                         | rebuild-index, reindex-paper
| commands       | reindex-paper requires     |                              | summaryize-all, validate-store
|                | last_query_set if a paper  |                              |
|                | index number is provided   |                              |
|----------------|----------------------------|------------------------------|-----------------------------------
| Meta commands  | None                       | None, except for clear       | status, history, clear, help,
|                |                            |                              | quit/exit
|----------------|----------------------------|------------------------------|-----------------------------------
```
