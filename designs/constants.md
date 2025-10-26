---
status: implemented
---

# Design for centralized constants file

There are various constants spread throughtout the application, particularly around search
(e.g. `k` or various hyperparameters). We want to gather them in a single file so that:

1. We can easily understand the values for these parameters and change them if necessary, and
2. We avoid having the same function different parameter values, unless intended.

The file should be called `constants.py`. Constants in that file should be `ALL_UPPERCASE`
and each constant should have comments explaining its use.

Functions that accept parameters associated with constants should:
1. Use the constant as the default value in the function definition
2. Have callers explicitly provide the constant value at the call site

This approach ensures that:
- The function signature clearly documents the default behavior
- Callers are explicit about which constants they're using
- It's easy to see where non-default values are being used

### Example

**Function definition:**
```python
def google_search_arxiv(query: str, k: int = constants.GOOGLE_SEARCH_RESULT_COUNT, verbose: bool = False) -> list[str]:
    ...
```

**Function call:**
```python
def _google_search_arxiv_papers(query: str) -> list[PaperMetadata]:
    ...
    paper_ids = google_search_arxiv(query, k=constants.GOOGLE_SEARCH_RESULT_COUNT)
```

## Specific cases
Here are some specific cases that should be included:

- In workflow.py there are two calls to `search_index`. The values of `k`, `use_mmr`,
  `similarity_cutoff`, and `mmr_alpha` should all be in the constants file. The constants
  for `k` and `similarity_cutoff` should also be used for calls to `search_content_index_filtered`
- Calls to `search_summary_index` should have constants as well, but a separate set, since we
  may want diffenent constant values for the summary index vs. the content index.
- Calls to `google_search_arxiv` in archive_downloader.py should put the number of papers
  to be retrieved (`k`) as a constant.

## Testing
No additional testing is needed, but the existing tests should continue to run without errors.

