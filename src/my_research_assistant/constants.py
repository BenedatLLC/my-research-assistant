"""
Centralized constants for the research assistant application.

This module contains all hard-coded parameter values used throughout the application,
particularly for search operations and workflow configurations. By centralizing these
values, we can:

1. Easily understand and tune hyperparameters in one place
2. Ensure consistency across different parts of the codebase
3. Avoid accidentally using different values for the same logical parameter

All constants should be ALL_UPPERCASE and include comments explaining their use.
"""

# === ARXIV SEARCH CONSTANTS ===

# Number of papers to retrieve and display from ArXiv search.
# This determines how many search results the user sees when using the 'find' command.
ARXIV_SEARCH_RESULT_COUNT = 5

# Number of papers to retrieve from Google Custom Search.
# Google Custom Search returns up to 10 results per query (free tier limit).
# After retrieval, these are deduplicated and reranked before showing to the user.
GOOGLE_SEARCH_RESULT_COUNT = 10

# Maximum number of candidate papers to retrieve from ArXiv API keyword search.
# This is only used when Google Custom Search is not configured (fallback mode).
# Higher values provide more candidates for semantic reranking but increase API latency.
ARXIV_CANDIDATE_LIMIT = 50


# === CONTENT INDEX SEARCH CONSTANTS ===

# Number of text chunks to retrieve from the content index during semantic search.
# Higher values provide more context but may include less relevant results.
# Used for the 'sem-search' command to answer questions from paper content.
CONTENT_SEARCH_K = 20

# Whether to use Maximum Marginal Relevance (MMR) for content index search.
# MMR balances relevance with diversity, helping retrieve chunks from multiple papers
# rather than all chunks from a single highly-relevant paper.
CONTENT_SEARCH_USE_MMR = True

# Minimum similarity score threshold for content index search results.
# Results below this threshold are filtered out. Range: 0.0 (no filtering) to 1.0 (exact match).
# 0.6 provides moderate filtering, removing low-quality matches while keeping relevant content.
CONTENT_SEARCH_SIMILARITY_CUTOFF = 0.6

# MMR alpha parameter for balancing relevance vs diversity in content search.
# Range: 0.0 (maximum diversity) to 1.0 (maximum relevance).
# 0.5 provides balanced results with both relevant and diverse content.
CONTENT_SEARCH_MMR_ALPHA = 0.5


# === SUMMARY INDEX SEARCH CONSTANTS ===

# Number of summary/note chunks to retrieve from the summary index.
# Used in the research workflow (Stage 1) to identify relevant papers.
# Lower than content search since summaries are more concise and high-level.
SUMMARY_SEARCH_K = 5

# Whether to use Maximum Marginal Relevance (MMR) for summary index search.
# Enables diversity across different papers when searching summaries and notes.
SUMMARY_SEARCH_USE_MMR = True

# Minimum similarity score threshold for summary index search results.
# Lower threshold (0.5) than content search because summaries are more abstract
# and may not contain exact query terms while still being relevant.
SUMMARY_SEARCH_SIMILARITY_CUTOFF = 0.5


# === RESEARCH WORKFLOW CONSTANTS ===

# Number of papers to identify from summary search in Stage 1 of research workflow.
# The research command uses a two-stage approach: first identify relevant papers
# from summaries, then search detailed content within those papers.
RESEARCH_SUMMARY_PAPERS = 5

# Number of detailed text chunks to retrieve in Stage 2 of research workflow.
# After identifying relevant papers, this determines how many detailed excerpts
# to retrieve from those papers for synthesis into the final research answer.
RESEARCH_DETAIL_CHUNKS = 10

# Minimum similarity score for content search in research workflow.
# Applied during Stage 2 when searching detailed content within identified papers.
# Uses same threshold as summary search for consistency.
RESEARCH_CONTENT_SIMILARITY_CUTOFF = 0.5
