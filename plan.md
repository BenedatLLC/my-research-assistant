# Plan

This is the development plan for the project.
The overall objective is to build a chatbot agent that can aid in keeping up with the
latest research in generative AI, as published on arxiv.org. The interface
to the agent is a command line shell, using the `rich` python library for formatting.

## Development plan

1.  [x] Create the basic chatbot
2.  [x] Review workflow.py and refactor it to make it clearer
3.  [ ] Add new results and notes directories to FileLocations
4.  [ ] Create a separate index for summaries and notes; make sure indexing tools are idempotent
5.  [ ] Refactor the chatbot commands with a state machine to control the workflow
6.  [ ] Add view summary and open commands (use case 2)
7.  [ ] Finish the RAG command (use case 3)
8.  [ ] Implement deep research (use case 4)
9.  [ ] Add any commands needed to finish use case 5 (maintenance)
10. [ ] Add intent detection in front of the commands, so that user can just provide natural text queries

## Designs
The following documents in the `designs` subdirectory provide the intended design for the system:

- `user-stories.md` - high level user stories
- `file-store.md` - how various data for each paper are stored in the file system
- `workflow-state-machine-and-commands.md` - state machine to control the overall workflow and associated commands
