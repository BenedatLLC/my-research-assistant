"""State machine for the research assistant workflow.

This module implements the state machine described in the design document,
managing state transitions and state variables for the chat interface.
"""

from enum import Enum
from typing import List, Optional, Union
from dataclasses import dataclass, field
from .project_types import PaperMetadata


class WorkflowState(Enum):
    """States in the research assistant workflow state machine."""
    INITIAL = "initial"
    SELECT_NEW = "select-new"
    SELECT_VIEW = "select-view"
    SUMMARIZED = "summarized"
    SEM_SEARCH = "sem-search"
    RESEARCH = "research"


@dataclass
class StateVariables:
    """State variables that persist across commands in a session."""
    last_query_set: List[str] = field(default_factory=list)  # Paper IDs from last query
    selected_paper: Optional[PaperMetadata] = None  # Currently selected paper
    draft: Optional[str] = None  # In-progress draft content
    original_query: Optional[str] = None  # Original user query for semantic search/research

    def clear(self):
        """Clear all state variables (transition to initial state)."""
        self.last_query_set = []
        self.selected_paper = None
        self.draft = None
        self.original_query = None

    def clear_query_state(self):
        """Clear query-related state (for new queries)."""
        self.last_query_set = []
        self.selected_paper = None
        self.draft = None
        self.original_query = None

    def set_query_results(self, paper_ids: List[str]):
        """Set the results of a query operation."""
        self.last_query_set = paper_ids
        self.selected_paper = None
        # Keep existing draft if we're in a search/research state

    def set_selected_paper(self, paper: PaperMetadata, draft_content: str):
        """Set the selected paper and its associated draft."""
        self.selected_paper = paper
        self.draft = draft_content
        self.last_query_set = []  # Clear query set when selecting a specific paper

    def set_draft(self, content: str):
        """Update the draft content."""
        self.draft = content


class StateMachine:
    """State machine for managing workflow state and transitions."""

    def __init__(self):
        self.current_state = WorkflowState.INITIAL
        self.state_vars = StateVariables()

    def reset(self):
        """Reset to initial state and clear all state variables."""
        self.current_state = WorkflowState.INITIAL
        self.state_vars.clear()

    def get_valid_commands(self) -> List[str]:
        """Get list of valid commands for the current state."""
        # Global commands that work in any state
        global_commands = ["rebuild-index", "reindex-paper <paper_id>", "summarize-all", "validate-store", "help", "status", "history", "clear", "quit", "exit"]

        # State-specific commands based on the design document
        state_commands = {
            WorkflowState.INITIAL: [
                "find <query>", "sem-search <query>", "research <query>", "list"
            ],
            WorkflowState.SELECT_NEW: [
                "summarize <number|id>", "find <query>", "sem-search <query>",
                "research <query>", "list"
            ],
            WorkflowState.SELECT_VIEW: [
                "summary <number|id>", "open <number|id>", "find <query>",
                "sem-search <query>", "research <query>", "list"
            ],
            WorkflowState.SUMMARIZED: [
                "improve <text>", "notes", "find <query>", "sem-search <query>",
                "research <query>", "list"
            ],
            WorkflowState.SEM_SEARCH: [
                "save", "improve <feedback>", "summary <number|id>", "open <number|id>",
                "find <query>", "sem-search <query>", "research <query>", "list"
            ],
            WorkflowState.RESEARCH: [
                "save", "improve <feedback>", "summary <number|id>", "open <number|id>",
                "find <query>", "sem-search <query>", "research <query>", "list"
            ]
        }

        return global_commands + state_commands[self.current_state]

    def is_command_valid(self, command: str) -> bool:
        """Check if a command is valid in the current state."""
        valid_commands = self.get_valid_commands()

        # Extract base command from user input
        cmd_base = command.split()[0].lower() if command.strip() else ""

        # Check against valid command patterns
        for valid_cmd in valid_commands:
            valid_base = valid_cmd.split()[0].lower()
            if cmd_base == valid_base:
                return True

        return False

    def transition_to_initial(self, reason: str = ""):
        """Transition to initial state and clear state variables."""
        self.current_state = WorkflowState.INITIAL
        self.state_vars.clear()

    def transition_after_find(self, found_papers: bool) -> WorkflowState:
        """Handle state transition after find command."""
        if found_papers:
            self.current_state = WorkflowState.SELECT_NEW
        else:
            self.transition_to_initial("No papers found")
        return self.current_state

    def transition_after_list(self) -> WorkflowState:
        """Handle state transition after list command."""
        self.current_state = WorkflowState.SELECT_VIEW
        self.state_vars.draft = None  # Clear draft when listing papers
        return self.current_state

    def transition_after_summarize(self, paper: PaperMetadata, summary: str) -> WorkflowState:
        """Handle state transition after summarize command."""
        self.current_state = WorkflowState.SUMMARIZED
        self.state_vars.set_selected_paper(paper, summary)
        return self.current_state

    def transition_after_sem_search(self, found_results: bool, search_results: str, paper_ids: List[str], original_query: str = "") -> WorkflowState:
        """Handle state transition after sem-search command."""
        if found_results:
            self.current_state = WorkflowState.SEM_SEARCH
            self.state_vars.set_query_results(paper_ids)
            self.state_vars.set_draft(search_results)
            self.state_vars.original_query = original_query
        else:
            self.transition_to_initial("No search results found")
        return self.current_state

    def transition_after_research(self, found_results: bool, research_results: str, paper_ids: List[str], original_query: str = "") -> WorkflowState:
        """Handle state transition after research command."""
        if found_results:
            self.current_state = WorkflowState.RESEARCH
            self.state_vars.set_query_results(paper_ids)
            self.state_vars.set_draft(research_results)
            self.state_vars.original_query = original_query
        else:
            self.transition_to_initial("No research results found")
        return self.current_state

    def transition_after_summary_view(self, paper: PaperMetadata, summary: str) -> WorkflowState:
        """Handle state transition after viewing a paper summary."""
        self.current_state = WorkflowState.SUMMARIZED
        self.state_vars.set_selected_paper(paper, summary)
        return self.current_state

    def stay_in_current_state(self):
        """Explicitly stay in current state (for commands like open, improve, etc.)."""
        return self.current_state

    def get_state_description(self) -> str:
        """Get a human-readable description of the current state."""
        descriptions = {
            WorkflowState.INITIAL: "Ready for new command",
            WorkflowState.SELECT_NEW: f"Found {len(self.state_vars.last_query_set)} papers - select one to summarize",
            WorkflowState.SELECT_VIEW: f"Viewing {len(self.state_vars.last_query_set)} papers - view summaries or content",
            WorkflowState.SUMMARIZED: f"Working with paper: {self.state_vars.selected_paper.title if self.state_vars.selected_paper else 'Unknown'}",
            WorkflowState.SEM_SEARCH: f"Semantic search results from {len(self.state_vars.last_query_set)} papers",
            WorkflowState.RESEARCH: f"Research results from {len(self.state_vars.last_query_set)} papers"
        }
        return descriptions.get(self.current_state, "Unknown state")

    def validate_paper_reference(self, reference: str, available_papers: List[PaperMetadata]) -> Optional[PaperMetadata]:
        """Validate and resolve a paper reference (number or ID) against available papers.

        Args:
            reference: User input - either a number (1, 2, 3...) or paper ID (2503.22738)
            available_papers: List of papers currently available for selection

        Returns:
            PaperMetadata if valid reference, None otherwise
        """
        if not available_papers:
            return None

        # Try parsing as a number first (1-indexed)
        try:
            paper_num = int(reference)
            if 1 <= paper_num <= len(available_papers):
                return available_papers[paper_num - 1]
        except ValueError:
            pass

        # Try matching as paper ID
        for paper in available_papers:
            if paper.paper_id == reference or paper.paper_id.startswith(reference):
                return paper

        return None