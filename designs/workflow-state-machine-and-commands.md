---
status: not yet implemented
---
# Workflow state machine and commands
This is a design of a workflow that is controlled through a single
state machine. The goal is to make it clear what commands can be
run in each state of the user's conversation. The general priciples are:

1. The user has to select a paper before performing certain commands
   (e.g. adding to the collection, viewing, or viewing its summary).
2. Summaries are always created and saved when adding a new paper through `summarize`.
   They can optionally refine the summary through `improve` or add their own notes through
   `notes`.
3. Semantic searches and deep research produce a numbered list of source papers. The user
   can refine the current results through `improve`, save the results to a file via `save`,
   or look at a specific paper (or its summary) from the citation list. When saving the results
   of the semantic search or deep research, the system will come up with a unique title based on the
   search topic and let the user know the saved file location.

## Commands
The current commands are:

- find <query> - Find papers on ArXiv to download
- sem-search <query> - Search your indexed papers semantically
- list - Show all downloaded papers (with pagination)
- select <number> - select a paper from search results and summarize it
- improve <feedback> - improve current summary
- save - save the current summary
- help - Show this help message
- status - Show the current workflow status
- history - Show conversation history
- clear - Clear conversation history
- quit or exit - Exit the chat

We want to refactor to the following set of commands:

- find <query> - Find papers on ArXiv to download
- summarize <number|id> - Select a paper from find results and summarize it
- improve <feedback> - Improve current summary or semantic search or deep research
- save - Save the current summary, semantic search result, or deep research result
- abandon - Abandon the current paper summary
- notes - Edit notes file for a paper
- sem-search <query> - Search your indexed papers semantically
- list - List all downloaded papers (with pagination)
- summary <number|id> - Show the summary of a paper listed via sem-search or list
- open <number|id> - Show the contents of a paper listed via sem-search or list
- research <query> - Perform deep research on the downloaded papers
- save - Save the current semantic search result or deep research result
- rebuild-index - Rebuild the index files for both paper content and summaries.
- help - Show the valid commands for the current conversation state.
- status - Show the current workflow status
- history - Show conversation history
- clear - Clear conversation history
- quit or exit - Exit the chat

## State variables
There are three main "state variables" in the workflow that, in addition ot the state value,
help to keep track of information across commands:

- `last_query_set` - a list of paper ids representing the results of the last query (via
  find, sem-search, list, or research).
- `selected_paper` - paper selected from a query's results for further processing (summarization,
  viewing the summary, or viewing the original paper pdf).
- `draft` - markdown representing an in-progress draft of a paper summary, a semantic search,
  or a deep research query.

## States
### State descriptions
Here is a table listing the states of the workflow, the expected values of state variables when
entering those states, and a description of the state:

```table
| state       | state variable values      | description                                            | valid commands        |
|-------------|----------------------------|--------------------------------------------------------|-----------------------|
| initial     | last_query_set=[]          | The workflow begins in this state.                     | find <query>          |
|             | selected_paper=None        |                                                        | sem-search <query>    |
|             | draft=None                 |                                                        | research <query>      |
|             |                            |                                                        | list                  |
|-------------|----------------------------|--------------------------------------------------------|-----------------------|
| select-new  | last_query_set=[P1,P2,...] | User ran a find command and a list of papers was       | summarize <number|id> |
|             | selected_paper=None        | returned. The user can now select one for downloading. | find <query>          |
|             | draft=None                 |                                                        | sem-search <query>    |
|             |                            |                                                        | research <query>      |
|             |                            |                                                        | list                  |
|-------------|----------------------------|--------------------------------------------------------|-----------------------|
| select-view | last_query_set=[P1,P2,...] | The user ran a list command, which returns papers from | summary <number|id>   |
|             | selected_paper=None        | from the store without creating any kind of draft.     | open <number|id>      |
|             | draft=None                 |                                                        | find <query>          |
|             |                            |                                                        | sem-search <query>    |
|             |                            |                                                        | research <query>      |
|             |                            |                                                        | list                  |
|-------------|----------------------------|--------------------------------------------------------|-----------------------|
| summarized  | last_query_set=[]          | A paper has been summarized and saved. The user can    | improve <text>        |
|             | selected_paper=Pn          | do more with this paper or start another query.        | notes                 |
|             | draft="..."                |                                                        | find <query>          |
|             |                            |                                                        | sem-search <query>    |
|             |                            |                                                        | research <query>      |
|             |                            |                                                        | list                  |
|-------------|----------------------------|--------------------------------------------------------|-----------------------|
|             | last_query_set=[P1,P2,...] | User ran a semantic search, which returned a summary   | save                  |
| sem-search  | selected_paper=None        | and a list of papers. They can improve the results,    | improve <feedback>    |
|             | draft="..."                | save the results, or select a paper.                   | summary <number|id>   |
|             |                            |                                                        | open <number|id>      |
|             |                            |                                                        | find <query>          |
|             |                            |                                                        | sem-search <query>    |
|             |                            |                                                        | research <query>      |
|             |                            |                                                        | list                  |
|-------------|----------------------------|--------------------------------------------------------|-----------------------|
|             | last_query_set=[P1,P2,...] | User ran a deep research query, which returns a report | save                  |
| research    | selected_paper=None        | and a list of papers. They can improve the results,    | improve <feedback>    |
|             | draft="..."                | save the results, or select a paper.                   | summary <number|id>   |
|             |                            |                                                        | open <number|id>      |
|             |                            |                                                        | find <query>          |
|             |                            |                                                        | sem-search <query>    |
|             |                            |                                                        | research <query>      |
|             |                            |                                                        | list                  |
|-------------|----------------------------|--------------------------------------------------------|-----------------------|
```

The commands `rebuild-index`, `help`, `status`, `history`, `clear`, `quit`, and `exit` can be run from any state.

### State transitions
Here is a table showing each command, the valid start states for that command, the actions taken on
the state variables by the command, and the next state(s).

```table
| command               | start state(s)    | actions                    | next state(s)           |
|-----------------------|-------------------|----------------------------|------------------- -----|
| find <query>          | ANY               | last_query_set=[P1,P2,...] | select-new,             |
|                       |                   | selected_paper=None        |  if papers found        |
|                       |                   | draft=None                 | initial, otherwise      |
|-----------------------|-------------------|----------------------------|-------------------------|
| summarize <number|id> | select-new        | last_query_set=[]          | summarized              |
|                       |                   | selected_paper=Pn          |                         |
|                       |                   | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| improve <feedback>    | summarized        | last_query_set=[]          | summarized              |
|                       |                   | selected_paper=Pn          |                         |
|                       |                   | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| notes                 | summarized        | last_query_set=[]          | summarized              |
|                       |                   | selected_paper=Pn          |                         |
|                       |                   | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| sem-search <query>    | ANY               | last_query_set=[P1,P2,...] | sem-search,             |
|                       |                   | selected_paper=None        | if papers found         |
|                       |                   | draft="..."                | initial, otherwise      |
|-----------------------|-------------------|----------------------------|-------------------------|
| save                  | sem-search        | last_query_set=[P1,P2,...] | sem-search              |
|                       |                   | selected_paper=None        |                         |
|                       |                   | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| improve <feedback>    | sem-search        | last_query_set=[P1,P2,...] | sem-search              |
|                       |                   | selected_paper=None        |                         |
|                       |                   | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| research <query>      | ANY               | last_query_set=[P1,P2,...] | research                |
|                       |                   | selected_paper=None        | if papers found         |
|                       |                   | draft="..."                | initial, otherwise      |
|-----------------------|-------------------|----------------------------|-------------------------|
| save                  | research          | last_query_set=[P1,P2,...] | research                |
|                       |                   | selected_paper=None        |                         |
|                       |                   | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| improve <feedback>    | research          | last_query_set[P1,P2,...]  | research                |
|                       |                   | selected_paper=None        |                         |
|                       |                   | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| summary <number|id>   | sem-search or     | last_query_set[P1,P2,...]  | summarized              |
|                       | research or       | selected_paper=None        |                         |
|                       | select-view       | draft="..."                |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| open <number|id>      | summarized or     | last_query_set[P1,P2,...]  | current state           |
|                       | sem-search or     | selected_paper=None        |                         |
|                       | research or       | draft="..."                |                         |
|                       | select-view       |                            |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
| list                  | ANY               | last_query_set=[P1,P2...]  | select-view             | 
|                       |                   | selected_paper=None        |                         |
|                       |                   | draft=None                 |                         |
|-----------------------|-------------------|----------------------------|-------------------------|
```
