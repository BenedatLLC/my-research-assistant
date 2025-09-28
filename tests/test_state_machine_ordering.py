"""Tests for consistent paper ID ordering in state machine."""

import pytest
from my_research_assistant.state_machine import StateMachine, StateVariables


class TestStateMachineOrdering:
    """Test that state machine always maintains consistent paper ID ordering."""

    def test_set_query_results_sorts_paper_ids(self):
        """Test that set_query_results always sorts paper IDs in ascending order."""
        state_vars = StateVariables()

        # Test with unsorted paper IDs
        unsorted_ids = ["2507.20534v1", "2412.19437v2", "2301.10095v1"]
        state_vars.set_query_results(unsorted_ids)

        # Verify they are stored in sorted order
        expected_sorted = ["2301.10095v1", "2412.19437v2", "2507.20534v1"]
        assert state_vars.last_query_set == expected_sorted

    def test_set_query_results_handles_already_sorted(self):
        """Test that already sorted IDs remain sorted."""
        state_vars = StateVariables()

        # Test with already sorted paper IDs
        sorted_ids = ["2301.10095v1", "2412.19437v2", "2507.20534v1"]
        state_vars.set_query_results(sorted_ids)

        # Verify they remain in sorted order
        assert state_vars.last_query_set == sorted_ids

    def test_set_query_results_handles_empty_list(self):
        """Test that empty list is handled correctly."""
        state_vars = StateVariables()

        state_vars.set_query_results([])
        assert state_vars.last_query_set == []

    def test_set_query_results_handles_single_paper(self):
        """Test that single paper ID works correctly."""
        state_vars = StateVariables()

        state_vars.set_query_results(["2507.20534v1"])
        assert state_vars.last_query_set == ["2507.20534v1"]

    def test_state_machine_transitions_maintain_sorting(self):
        """Test that state machine transitions maintain sorted order."""
        sm = StateMachine()

        # Test sem-search transition
        unsorted_ids = ["2507.20534v1", "2412.19437v2", "2301.10095v1"]
        sm.transition_after_sem_search(
            found_results=True,
            search_results="Test search results",
            paper_ids=unsorted_ids,
            original_query="test query"
        )

        expected_sorted = ["2301.10095v1", "2412.19437v2", "2507.20534v1"]
        assert sm.state_vars.last_query_set == expected_sorted

    def test_research_transition_maintains_sorting(self):
        """Test that research transition maintains sorted order."""
        sm = StateMachine()

        # Test research transition
        unsorted_ids = ["2507.20534v1", "2412.19437v2", "2301.10095v1"]
        sm.transition_after_research(
            found_results=True,
            research_results="Test research results",
            paper_ids=unsorted_ids,
            original_query="research query"
        )

        expected_sorted = ["2301.10095v1", "2412.19437v2", "2507.20534v1"]
        assert sm.state_vars.last_query_set == expected_sorted

    def test_mixed_version_numbers_sort_correctly(self):
        """Test that papers with different version numbers sort correctly."""
        state_vars = StateVariables()

        # Test with mixed version numbers
        mixed_ids = ["2507.20534v2", "2507.20534v1", "2412.19437v2", "2412.19437v1"]
        state_vars.set_query_results(mixed_ids)

        # Should sort by the full ID string (including version)
        expected_sorted = ["2412.19437v1", "2412.19437v2", "2507.20534v1", "2507.20534v2"]
        assert state_vars.last_query_set == expected_sorted

    def test_clearing_methods_work_correctly(self):
        """Test that clearing methods work correctly with the new sorting."""
        state_vars = StateVariables()

        # Set some paper IDs
        state_vars.set_query_results(["2507.20534v1", "2412.19437v2"])
        assert len(state_vars.last_query_set) == 2

        # Test clear
        state_vars.clear()
        assert state_vars.last_query_set == []

        # Set again and test clear_query_state
        state_vars.set_query_results(["2507.20534v1", "2412.19437v2"])
        state_vars.clear_query_state()
        assert state_vars.last_query_set == []

    def test_list_summary_consistency_scenario(self):
        """Test the specific scenario from the original issue."""
        # This simulates the exact problem:
        # 1. Papers downloaded in order: Kimi (2507.20534v1), DeepSeek (2412.19437v2)
        # 2. List command should show them sorted by ID: DeepSeek first, then Kimi
        # 3. Summary 1 should refer to DeepSeek (first in sorted order)

        state_vars = StateVariables()

        # Simulate papers returned in download order (unsorted)
        download_order_ids = ["2507.20534v1", "2412.19437v2"]  # Kimi first, DeepSeek second

        # When we set query results, they should be sorted
        state_vars.set_query_results(download_order_ids)

        # Verify they are stored in ID-sorted order (DeepSeek first, Kimi second)
        expected_sorted = ["2412.19437v2", "2507.20534v1"]  # DeepSeek first, Kimi second
        assert state_vars.last_query_set == expected_sorted

        # This means:
        # - List will show: 1. DeepSeek (2412.19437v2), 2. Kimi (2507.20534v1)
        # - Summary 1 will get index 0 = "2412.19437v2" (DeepSeek) ✓
        # - Summary 2 will get index 1 = "2507.20534v1" (Kimi) ✓