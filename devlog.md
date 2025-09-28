# Development log

## TODO
* Implement the open command
* Finish the notes command

## Sunday Sept 28, 2025
* Updated state management for paper command arguments. If you select a specific paper, it doesn't not clear
  the current query set *unless* that paper is not in the query set. I did this with Claude as follows:
  1. Described the desired changes and asked it to review the design documents for what would need to change
     in the design. Also told it to ask me for clarifications to the design.
  2. I provided the clarifications and asked it to update the design documents.
  3. I then asked it to proceed with the implementation, giving it steps 2 - 7 below.
* Wrote design and implementation for paper command arguments
* Here's the dev flow I used with the paper command arguments:
  1. Write design document
  2. Ask Claude to review design and point out gaps:
     > Can you review the design document for commands with paper arguments. It is located at
     > designs/command-arguments.md. Let me know if anything is unclear or there are edge cases I missed.
  3. Update design based on feedback
  4. Prompt Claude to do the implementation:
     > Ok, can you implment the design for paper command arguments found in designs/command-arguments.md?
     > Use the following steps:
     > 1. Review the latest design
     > 2. Compare the design against the current implementation
     > 3. Write a plan for the code changes needed to implement the design. If there are any questions you have, be
     >    sure to ask me first, unless there are pretty clear assumptions you can make.
     > 4. Implement the design per the plan
     > 5. Add unit tests needed to validate the new functionality and to make sure it matches the design
     > 6. Update the tests under tests/ and the implementation to make sure the existing unit tests still pass while
     >    keeping to the design documents
     > 7. Update the "Implementation" section of command-arguments.md, adding a summary of how the design was
     >    implemented and noting any assumptions that were made.
   5. Claude came back with some more clarification questions. Answered the questions, asked it to update the design
      document, and then continue with the implementation plan:
      > Thank you for the insightful questions. Here are my responses:
      > 1. In general, if the user specifies a paper id, ...
      > ...
      > Can you update the design document with this information and then continue with your implementation plan?
      

## Saturday Sept 27, 2025
### Added

### Fixed
* Summaries were not always being indexed
* Compound queries did not work (e.g. compare the Deepseek V3 and Kimi K2 models). Asked Claude to improve
  similarity search strategy - it added support for an MMR reranker. This took several tries for Claude
  to get it right - I had to ask it to create a unit test for my specific scenario.
* `summary 2` was printing the wrong summary because the `list` command was sorting papers but the workflow
  state variable was not sorted. Changed to keep the current query set in the workflow to always be sorted
  by paper id so that papers are displayed and accessed in a consistent order.


## Friday Sept 26, 2025

### Added
* `validate-store` command - created design doc, asked claude to indicate what's unclear, fixed, then implemented.


### Fixed
* Logic to tell if a document was indexed was wrong - it would say that something was indexed, when it wasn't
