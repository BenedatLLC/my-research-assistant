---
status: abandoned
---
# Single level workflow state machine
This is a design of a workflow that is controlled through a single
state machine. The goal is to make it clear what commands can be
run in each state of the user's conversation, preserving invariants
like:
1. A user has to select a paper before performing certain commands
   (e.g. adding to the collection, viewing, or viewing its summary).
2. When we add a paper to the collection (starting with the `find` command),
   we take the user through the process of adding a summary. They can abandon
   that only through the explicit `abandon` command.
3. It should be clear when a user is switching to another sub-workflow

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
- summarize <number> - Select a paper from find results and summarize it
- improve <feedback> - Improve current summary or semantic search or deep research
- save - Save the current summary, semantic search result, or deep research result
- abandon - Abandon the current paper summary
- notes <text> - Add notes to a summary
- sem-search <query> - Search your indexed papers semantically
- list - List all downloaded papers (with pagination)
- summary <number> - Show the summary of a paper listed via sem-search or list
- open <number> - Show the contents of a paper listed via sem-search or list
- research <query> - Perform deep research on the downloaded papers
- help - Show this help message
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
| state       | state variable values      | description                                            |
|-------------|----------------------------|--------------------------------------------------------|
| initial     | last_query_set=[]          | The workflow begins in this state.                     |
|             | selected_paper=None        |                                                        |
|             | draft=None                 |                                                        |
|-------------|----------------------------|--------------------------------------------------------|
| select-new  | last_query_set=[P1,P2,...] | User ran a find command and a list of papers was       |
|             | selected_paper=None        | returned. The user can now select one for downloading. |
|             | draft=None                 |                                                        |
|-------------|----------------------------|--------------------------------------------------------|
| select-view | last_query_set=[]          | The user ran a list command, which returns papers from |
|             | selected_paper=Pn          | from the store without creating any kind of draft.     |
|             | draft=None                 |                                                        |
|-------------|----------------------------|--------------------------------------------------------|
| draft       | last_query_set=[]          | User selected a paper to download. It was downloaded,  |
| summary     | selected_paper=Pn          | indexed, and summarized. They can review the summary   |
|             | draft="..."                | improve it, save it, or abandon it.                    |
|-------------|----------------------------|--------------------------------------------------------|
| summarized  | last_query_set=[]          | A paper has been summarized and saved. The user can    |
|             | selected_paper=Pn          | do more with this paper or start another query.        |
|             | draft="..."                |                                                        |
|-------------|----------------------------|--------------------------------------------------------|
| draft       | last_query_set=[P1,P2,...] | User ran a semantic search, which returned a summary   |
| sem-search  | selected_paper=None        | and a list of papers. They can improve the results,    |
|             | draft="..."                | save the results, or select a paper.                   |
|-------------|----------------------------|--------------------------------------------------------|
| draft       | last_query_set=[P1,P2,...] | User ran a deep research query, which returns a report |
| research    | selected_paper=None        | and a list of papers. They can improve the results,    |
|             | draft="..."                | save the results, or select a paper.                   |
|-------------|----------------------------|--------------------------------------------------------|
```

### State transitions
Here is a table showing each command, the valid start states for that command, the actions taken on
the state variables by the command, and the next state(s).

```table
| command            | start state(s)    | actions                    | next state(s)           |
|--------------------|-------------------|----------------------------|------------------- -----|
| find <query>       | ANY, except for   | last_query_set=[P1,P2,...] | select-new,             |
|                    | draft summary     | selected_paper=None        |  if papers found        |
|                    |                   | draft=None                 | initial, otherwise      |
|--------------------|-------------------|----------------------------|-------------------------|
| summarize <number> | select-new        | last_query_set=[]          | draft summary           |
|                    |                   | selected_paper=Pn          |                         |
|                    |                   | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| improve <feedback> | draft summary     | last_query_set=[]          | draft summary           |
|                    |      or           | selected_paper=Pn          |                         |
|                    | summarized        | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| notes <text>       | draft summary     | last_query_set=[]          | current state           |
|                    |      or           | selected_paper=Pn          |                         |
|                    | summarized        | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| abandon            | draft summary     | last_query_set=[]          | initial                 |
|                    |                   | selected_paper=None        |                         |
|                    |                   | draft=None                 |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| save               | draft summary     | last_query_set=[]          | summarized              |
|                    |                   | selected_paper=Pn          |                         |
|                    |                   | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| sem-search <query> | ANY, except for   | last_query_set=[P1,P2,...] | draft sem-search,       |
|                    | draft summary     | selected_paper=None        | if papers found         |
|                    |                   | draft="..."                | initial, otherwise      |
|--------------------|-------------------|----------------------------|-------------------------|
| save               | draft sem-search  | last_query_set=[P1,P2,...] | draft sem-search        |
|                    |                   | selected_paper=None        |                         |
|                    |                   | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| improve <feedback> | draft sem-search  | last_query_set=[P1,P2,...] | draft sem-search        |
|                    |                   | selected_paper=None        |                         |
|                    |                   | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| research <query>   | ANY, except for   | last_query_set=[P1,P2,...] | draft research,         |
|                    | draft summary     | selected_paper=None        | if papers found         |
|                    |                   | draft="..."                | initial, otherwise      |
|--------------------|-------------------|----------------------------|-------------------------|
| save               | draft research    | last_query_set=[P1,P2,...] | draft research          |
|                    |                   | selected_paper=None        |                         |
|                    |                   | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| improve <feedback> | draft research    | last_query_set[P1,P2,...]  | draft research          |
|                    |                   | selected_paper=None        |                         |
|                    |                   | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| summary <number>   | draft sem-search  | last_query_set[P1,P2,...]  | current state           |
|                    |       or          | selected_paper=None        |                         |
|                    | draft research    | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| open <number>      | draft sem-search  | last_query_set[P1,P2,...]  | current state           |
|                    |       or          | selected_paper=None        |                         |
|                    | draft research    | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| list               | ANY, except for   | last_query_set=[P1,P2...]  | select-view             | 
|                    | draft summary     | selected_paper=None        |                         |
|                    | draft research    | draft=None                 |                         |
|--------------------|-------------------|----------------------------|-------------------------|

|--------------------|-------------------|----------------------------|-------------------------|
```
