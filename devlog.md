# Development log

## TODO
* Make sure each command that acts on a paper can take a paper id or a selection number
* Implement the open command
* Finish the notes command

## Saturday Sept 27, 2025
### Added

### Fixed
* Summaries were not always being indexed
* Compound queries did not work (e.g. compare the Deepseek V3 and Kimi K2 models). Asked Claude to improve
  similarity search strategy - it added support for an MMR reranker. This took several tries for Claude
  to get it right - I had to ask it to create a unit test for my specific scenario.


## Friday Sept 26, 2025

### Added
* `validate-store` command - created design doc, asked claude to indicate what's unclear, fixed, then implemented.


### Fixed
* Logic to tell if a document was indexed was wrong - it would say that something was indexed, when it wasn't
