---
status: not yet implemented
---
# Command processing design using a dispatcher and sub-agents
This is the design for a two level system for processing user commands.
The top level is a dispatcher, which will dispatch to a running sub-agent
or start a new one.
The goal is to make it clear what commands can be run based on the history
of the conversation and make the rules easy to reason about.
We want to preserve invariants like:
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
- notes - Edit notes for a paper
- sem-search <query> - Search your indexed papers semantically
- list - List all downloaded papers (with pagination)
- summary <number|id> - Show the summary of a paper listed via sem-search or list
- open <number|id> - Show the contents of a paper selected from a paper list or by arxiv id
- research <query> - Perform deep research on the downloaded papers
- help - Show this help message
- status - Show the current workflow status
- history - Show conversation history
- clear - Clear conversation history
- quit or exit - Exit the chat

Note that there is no longer a `save` command -- the current draft of a summary
is always saved. In the future, we might consider an `undo` command, but leave
that for the next iteration on the design.

## State variables
There are three main "state variables" that are shared between the dispatcher and the
individual agents:

- `last_query_set` - a list of paper ids representing the results of the last query (via
  find, sem-search, list, or research).
- `selected_paper` - paper selected from a query's results for further processing (summarization,
  viewing the summary, or viewing the original paper pdf).
- `draft` - markdown representing an in-progress draft of a paper summary, a semantic search,
  or a deep research query.

## Dispatcher
### Dispatcher states
The dispatcher has states that determine which commands can be processed and which sub-agent
should they be dispatched to.

```table
| state           | active sub-sagent | description                                                                  |
|-----------------|-------------------|------------------------------------------------------------------------------|
| initial         | None              | The overall workflow begins in this state.                                   |
|-----------------|-------------------|------------------------------------------------------------------------------|
| found           | None              | A set of papers have been returned by a find command.                        |
|-----------------|-------------------|------------------------------------------------------------------------------|
| summarizer      | summarizer        | Review and refine a paper's summary                                          |
|                 |                   |                                                                              |
|-----------------|-------------------|------------------------------------------------------------------------------|
| semantic-search | semantic-search   | Search the index for relevant papers and summarize. Basically, RAG.          |
|-----------------|-------------------|------------------------------------------------------------------------------|
| research        | research          | Answer a broader research question using indexed summaries and papers.       |
|--------------- -|-------------------|------------------------------------------------------------------------------|
```

Here are the commands and the actions taken by the dispatcher:

```table
| command                | dispatcher state   | action(s)                   | next dispatcher state |
|------------------------|--------------------|-----------------------------|-----------------------|
| find <query>           | ANY                | terminate any running agents| found                 |
|                        |                    | last_query_set=[P1,P2,....] |                       |
|------------------------|--------------------|-----------------------------|-----------------------|
| summarize <number|id>  | found              | last_query_set=[]           | summarizer            |
|                        |                    | selected_paper=Pn           |                       |
|                        |                    | ensure paper is indexed     |                       |
|                        |                    | instantiate summary agent   |                       |
|------------------------|--------------------|-----------------------------|-----------------------|
| improve <feedback>     | summarizer         | dispatch to sumarizer agent | summarizer            |
|------------------------|--------------------|-----------------------------|-----------------------|
| notes                  | summarizer         | open editor on notes file   | summarizer            |
|                        |                    |    for paper                |                       |
|------------------------|--------------------|-----------------------------|-----------------------|
| sem-search <query>     | ANY                | instantiate semantic-search | semantic-search       |
|                        |                    |    agent                    |                       |
|                        |                    | from results of search,     |                       |
|                        |                    |    set last_query_set       |                       |
|------------------------|--------------------|-----------------------------|-----------------------|
| improve <feedback>     | 
```

The user can transition between any two states in the level-1 workflow, but those transitions are only
allowed in certain level-2 workflow states. Here are the commands which switch between states/sub-workflows:

```table
|                        |                      |                            | initial state    |
|                        | new state /          |                            | in second-level  |
| command                | sub-workflow         | action(s)                  | state machine    |
|------------------------|----------------------|----------------------------|------------------|
| find <query>           | new-paper            | last_query_set=[P1,P2,...] | select-new       |
|                        |                      | selected_paper=None        |                  |
|                        |                      | draft=None                 |                  |
|------------------------|----------------------|----------------------------|------------------|
| list                   | view-paper           | last_query_set=all_papers  | select-existing- |
|                        |                      | selected_paper=None        |                  |
|                        |                      | draft=None                 |                  |
|------------------------|----------------------|----------------------------|------------------|
| sem-search <query>     | semantic-search      | last_query_set=[P1,P2,...] | draft sem-search |
|                        |                      | selected_paper=None        |                  |
|                        |                      | draft=None                 |                  |
|------------------------|----------------------|----------------------------|------------------|
| research <query>       | research             | last_query_set=[P1,P2,...] | draft research   |
|                        |                      | selected_paper=None        |                  |
|                        |                      | draft=None                 |                  |
|------------------------|----------------------|----------------------------|------------------|
```

If the command (find, list, sem-search, or research) returns no papers, then the level-1 state machine
goes back to the initial state.

## Level-2 state machines / sub-workflows
Each state in the level-1 state machine corresponds to a sub-workflow / state machine in the
second level. We can look at each one independently. There are states that permit the user to
issue a command to exit the second level workflow and change states in the first level state
machine. We call these stats *exit states*.

### new-paper workflow
Here is a table listing the states of the new-paper workflow:

```table
|            |                            | exit   |
| state      | state variable values      | state? | description                                            |
|------------|----------------------------|--------|--------------------------------------------------------|
| select-new | last_query_set=[P1,P2,...] | No     | User ran a find command and a list of papers was       |
| (initial   | selected_paper=None        |        | returned. The user can now select one for downloading. |
|  state)    | draft=None                 |        |                                                        |
|------------|----------------------------|--------|--------------------------------------------------------|
| draft      | last_query_set=[]          | No     | User selected a paper to download. It was downloaded,  |
| summary    | selected_paper=Pn          |        | indexed, and summarized. They can review the summary   |
|            | draft="..."                |        | improve it, save it, or abandon it.                    |
|------------|----------------------------|--------|--------------------------------------------------------|
| summarized | last_query_set=[]          | Yes    | A paper has been summarized and saved. The user can    |
|            | selected_paper=Pn          |        | do more with this paper or start another query.        |
|            | draft="..."                |        |                                                        |
|------------|----------------------------|--------|--------------------------------------------------------|
```

Here is a table showing each command, the valid start states for that command, the actions taken on
the state variables by the command, and the next state(s).

```table
| command            | start state(s)    | actions                    | next state(s)           |
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
| abandon            | draft summary     | last_query_set=[]          | exit the workflow and   |
|                    |                   | selected_paper=None        | go to the initial state |
|                    |                   | draft=None                 | of the level-1 state    |
|                    |                   |                            | machine                 |
|--------------------|-------------------|----------------------------|-------------------------|
| save               | draft summary     | last_query_set=[]          | summarized              |
|                    |                   | selected_paper=Pn          |                         |
|                    |                   | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|

### view-paper workflow
Here is a table listing the states of the view-paper workflow:

```table
|               |                            | exit   |
| state         | state variable values      | state? | description                                            |
|---------------|----------------------------|--------|--------------------------------------------------------|
| select-view   | last_query_set=[P1,P2,...] | Yes    | User ran a list command and the list of indexed        |
| (initial      | selected_paper=None        |        | papers was returned. The user can now select one for   |
|  state)       | draft=None                 |        | viewing.                                               |
|---------------|----------------------------|--------|--------------------------------------------------------|
```

Here is a table showing each command, the valid start states for that command, the actions taken on
the state variables by the command, and the next state(s).

```table
| command            | start state(s)    | actions                    | next state(s)           |
|--------------------|-------------------|----------------------------|-------------------------|
| open <number>      | select-view       | last_query_set=[P1,P2,Pn]  | select-view             |
|                    |                   | selected_paper=None        |                         |
|                    |                   | draft=None                 |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| summary <number>   | select-view       | last_query_set=[P1,P2,Pn]  | select-view             |


```table
|------------|----------------------------|--------------------------------------------------------|
| draft      | last_query_set=[P1,P2,...] | User ran a semantic search, which returned a summary   |
| sem-search | selected_paper=None        | and a list of papers. They can improve the results,    |
|            | draft="..."                | save the results, or select a paper.                   |
|------------|----------------------------|--------------------------------------------------------|
| draft      | last_query_set=[P1,P2,...] | User ran a deep research query, which returns a report |
| research   | selected_paper=None        | and a list of papers. They can improve the results,    |
|            | draft="..."                | save the results, or select a paper.                   |
|------------|----------------------------|--------------------------------------------------------|
```

### State transitions
Here is a table showing each command, the valid start states for that command, the actions taken on
the state variables by the command, and the next state(s).

```table
| command            | start state(s)    | actions                    | next state(s)           |
|--------------------|-------------------|----------------------------|-------------------------|
| find <query>       | ANY, except for   | last_query_set=[P1,P2,...] | select, if papers found |
|                    | draft summary     | selected_paper=None        | initial, otherwise      |
|                    |                   | draft=None                 |                         |
|--------------------|-------------------|----------------------------|-------------------------|
| summarize <number> | select            | last_query_set=[]          | draft summary           |
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
| list               | ANY, except for   | last_query_set=[P1,P2...]  |   ?                     | 
|                    | draft summary     | selected_paper=None        |                         |
|                    | draft research    | draft="..."                |                         |
|--------------------|-------------------|----------------------------|-------------------------|
```
