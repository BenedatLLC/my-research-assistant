"""Integration test for research command in chat interface."""

import pytest
from my_research_assistant.state_machine import StateMachine, WorkflowState


def test_research_command_in_state_machine():
    """Test that research command is properly registered in state machine."""

    # Create state machine
    sm = StateMachine()

    # Verify research command is in valid commands from initial state
    valid_commands = sm.get_valid_commands()
    assert "research <query>" in valid_commands or "research" in [cmd.split()[0] for cmd in valid_commands]

    # Verify transition_after_research exists
    assert hasattr(sm, 'transition_after_research')

    # Test the transition
    paper_ids = ["2301.12345v1", "2302.67890v2"]
    research_content = "Test research content"
    query = "test query"

    new_state = sm.transition_after_research(
        found_results=True,
        research_results=research_content,
        paper_ids=paper_ids,
        original_query=query
    )

    # Verify state transitioned correctly
    assert new_state == WorkflowState.RESEARCH
    assert sm.current_state == WorkflowState.RESEARCH

    # Verify state variables are set correctly
    assert sm.state_vars.last_query_set == sorted(paper_ids)  # Should be sorted
    assert sm.state_vars.draft == research_content
    assert sm.state_vars.original_query == query
    assert sm.state_vars.selected_paper is None


def test_research_state_valid_commands():
    """Test that research state has correct valid commands."""

    sm = StateMachine()

    # Transition to research state
    sm.transition_after_research(
        found_results=True,
        research_results="test content",
        paper_ids=["2301.12345v1"],
        original_query="test"
    )

    # Get valid commands for research state
    valid_commands = sm.get_valid_commands()

    # Verify key commands are available
    assert any("save" in cmd for cmd in valid_commands)
    assert any("improve" in cmd for cmd in valid_commands)
    assert any("summary" in cmd for cmd in valid_commands)
    assert any("open" in cmd for cmd in valid_commands)
    assert any("find" in cmd for cmd in valid_commands)
    assert any("sem-search" in cmd for cmd in valid_commands)
    assert any("research" in cmd for cmd in valid_commands)


def test_research_command_from_various_states():
    """Test that research command can be run from any state."""

    sm = StateMachine()

    # Test from each state
    states_to_test = [
        WorkflowState.INITIAL,
        WorkflowState.SELECT_NEW,
        WorkflowState.SELECT_VIEW,
        WorkflowState.SUMMARIZED,
        WorkflowState.SEM_SEARCH,
        WorkflowState.RESEARCH
    ]

    for state in states_to_test:
        sm.current_state = state
        valid_commands = sm.get_valid_commands()

        # Research should be available from all states
        assert any("research" in cmd for cmd in valid_commands), \
            f"research command not found in {state.value} state"
