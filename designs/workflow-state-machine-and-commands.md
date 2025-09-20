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

## Implementation instructions
To implement these changed, do the following:
1. Review the design and the current implementation
2. Ask for clarification on any unclear aspects of the design that are relevant
   to the implementation.
3. Come up with a written plan for the changes. A recommended sequnce:
   a. Make any changes/additions to lower level functions and tools needed
      for the new design.
   b. Refactor the workflow, adding the state variables, and the appropriate state transitions.
   c. Refactor the chat interface to reflect the new commands and workflow.
   d. Make sure the existing unit tests pass, fixing them as needed
   e. Add test cases corresponding to the "Test flows" section and make sure they pass
4. Do the implementation according to the plan.
5. Add a section to this document giving an outline of the implementation.

## Commands
The current commands are:

- find <query> - Find papers on ArXiv to download
- sem-search <query> - Search your indexed papers semantically
- list - Show all downloaded papers (with pagination)
- select <number> - select a paper from search results and summarize it
- improve <feedback> - improve current summary
- save - save the current summary
- rebuild-index - Rebuild the index files for both paper content and summaries.
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
  viewing the summary, or viewing the original paper pdf). This replace `current_paper` in the
  existing implementation.
- `draft` - markdown representing an in-progress draft of a paper summary, a semantic search,
  or a deep research query. This should replace and extend the existing `current_summary`
  variable.

State variables are only kept in memory for the current session. A new session always starts in
the `initial` state. Transitions back to the initial state (e.g. after an unexpected error)
should clear the state variables.

## Error handling
If there is a crash, the underlying functions should generally be able to
recover from inconsistent or corrupted state. For example, the command `rebuild-index` can be
used to rebuild the index. If content related to a paper is missing, it can be (re-)generated.

If a network error or other unexpected error occurs, report the error to the user and go back to the
initial state, clearing any state variables.

We can assume that files referenced in state variables are not externally deleted or modified while the
application is running.

If a query command (find, sem-search, research, or list) does not return any papers, that should
be indicated and the initial state restored. If the user enters an invalid paper id or paper number,
just let the user know and go back to the same state.

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

## Test plan
The following command flows should be included in the unit tests to cover the basic state handling.

### Flow #1: Basic find → summarize → sem-search flow

1. find "Deep research agents: a systematic examination and roadmap"
2. summarize 1  # Given an exact title search, it should return the paper as the only option
3. improve "This is a survey paper, so adjust the outline to better match a survey rather than a unique contribution"
4. sem-search "what is a deep research agent"
5. save
6. summary 1
7. exit

**States tested:** initial → select-new → summarized → sem-search → summarized
**Key transitions:** find with results, summarize selection, improve summary, sem-search with results, save results, view summary from results

### Flow #2: list → view operations flow

1. list
2. summary 2  # View summary of second paper in list
3. open 1     # View full content of first paper (should stay in summarized state)
4. notes      # Edit notes for the currently summarized paper
5. find "transformers"
6. summarize 1
7. exit

**States tested:** initial → select-view → summarized → summarized → select-new → summarized
**Key transitions:** list papers, view summary from list, view paper content, edit notes, find from summarized state

### Flow #3: Deep research workflow

1. research "attention mechanisms in neural networks"
2. improve "Focus more on the mathematical foundations and less on applications"
3. save
4. summary 2  # View summary of second paper from research results
5. open 3     # View full content of third paper
6. research "transformer architectures"  # New research from summarized state
7. exit

**States tested:** initial → research → research → summarized → summarized → research
**Key transitions:** research query, improve research results, save research, view summaries from research results, new research from summarized state

### Flow #4: Multiple query types from different states

1. find "BERT language models"
2. sem-search "language model pre-training"  # Sem-search from select-new state
3. improve "Include more details about training procedures"
4. list  # List from sem-search state
5. summary 1
6. research "BERT fine-tuning strategies"  # Research from summarized state
7. exit

**States tested:** initial → select-new → sem-search → select-view → summarized → research
**Key transitions:** Multiple query transitions, switching between different query result types

### Flow #5: Error and edge case handling

1. find "nonexistent paper that should not be found"  # Should return to initial
2. find "machine learning"  # Should find multiple papers
3. summarize 999  # Invalid paper number - should stay in select-new
4. summarize 1    # Valid selection
5. sem-search "query with no results"  # Should return to initial
6. list
7. open 999  # Invalid paper number - should stay in select-view
8. summary 1 # Valid selection
9. exit

**States tested:** initial → initial → select-new → select-new → summarized → initial → select-view → select-view → summarized
**Key transitions:** Error handling, invalid inputs, queries with no results

### Flow #6: Direct state transitions and shortcuts

1. sem-search "neural network architectures"  # Direct to sem-search from initial
2. summary 1  # Direct to summarized from sem-search
3. list       # Direct to select-view from summarized
4. open 2     # Stay in select-view
5. research "optimization algorithms"  # Direct to research from select-view
6. summary 1  # Direct to summarized from research
7. find "gradient descent"  # Direct to select-new from summarized
8. exit

**States tested:** initial → sem-search → summarized → select-view → select-view → research → summarized → select-new
**Key transitions:** Direct transitions between all major states, no intermediate states

### Flow #7: Save operations across different states

1. research "deep learning fundamentals"
2. save  # Save research results
3. improve "Add more practical examples"
4. save  # Save improved research results
5. sem-search "backpropagation algorithm"
6. save  # Save sem-search results
7. improve "Include mathematical derivations"
8. save  # Save improved sem-search results
9. exit

**States tested:** initial → research → research → research → sem-search → sem-search → sem-search
**Key transitions:** Save operations in research and sem-search states, improve operations

### Flow #8: Complex multi-state navigation

1. find "attention mechanisms"
2. summarize 1
3. notes  # Edit notes
4. improve "Add more technical details"
5. sem-search "self-attention"
6. improve "Compare different attention variants"
7. research "transformer models"
8. save
9. list
10. open 3
11. summary 2
12. exit

**States tested:** initial → select-new → summarized → summarized → summarized → sem-search → sem-search → research → research → select-view → select-view → summarized
**Key transitions:** Complex state navigation with multiple operations in each state, testing persistence of state variables

## Test Coverage Summary

The 8 test flows above provide comprehensive coverage of the state machine:

### State Coverage
- **initial**: Entry point for all flows
- **select-new**: Covered in flows #1, #2, #4, #5, #6, #8
- **select-view**: Covered in flows #2, #4, #5, #6, #8
- **summarized**: Covered in all flows except #7
- **sem-search**: Covered in flows #1, #4, #6, #7, #8
- **research**: Covered in flows #3, #4, #6, #7, #8

### Command Coverage
- **find**: Tested from initial, select-new, summarized, select-view states
- **summarize**: Tested for valid and invalid selections
- **improve**: Tested in summarized, sem-search, and research states
- **save**: Tested in sem-search and research states (multiple saves)
- **notes**: Tested in summarized state
- **sem-search**: Tested from all states, with and without results
- **list**: Tested from multiple states
- **summary**: Tested for viewing summaries from different result sets
- **open**: Tested for viewing paper content, with error handling
- **research**: Tested from initial, summarized, and select-view states

### Error Handling Coverage
- No results found (flows #5)
- Invalid paper numbers/IDs (flows #5)
- State transitions after errors (flows #5)
- Multiple error conditions in sequence (flows #5)

### Edge Cases Coverage
- Multiple query types in sequence (flows #4, #6)
- Save operations without improve (flows #7)
- Multiple improve/save cycles (flows #7)
- Complex multi-command sequences (flows #8)
- Direct state transitions without intermediates (flows #6)

### State Variable Testing
Each flow tests that state variables (`last_query_set`, `selected_paper`, `draft`) are properly:
- Set when entering states
- Maintained during operations within states
- Cleared when transitioning to appropriate states
- Preserved across multiple operations in the same state

These test flows ensure that the state machine behaves correctly under all normal usage patterns, error conditions, and edge cases.
