"""Test the state machine implementation and state transitions."""

import pytest
from unittest.mock import Mock, patch

from my_research_assistant.state_machine import StateMachine, WorkflowState, StateVariables
from my_research_assistant.project_types import PaperMetadata
from datetime import datetime


class TestStateMachine:
    """Test StateMachine functionality."""

    def test_state_machine_initialization(self):
        """Test that StateMachine initializes correctly."""
        sm = StateMachine()

        assert sm.current_state == WorkflowState.INITIAL
        assert sm.state_vars is not None
        assert sm.state_vars.last_query_set == []
        assert sm.state_vars.selected_paper is None
        assert sm.state_vars.draft is None

    def test_reset(self):
        """Test state machine reset functionality."""
        sm = StateMachine()

        # Set some state
        sm.current_state = WorkflowState.SUMMARIZED
        sm.state_vars.last_query_set = ["paper1", "paper2"]
        sm.state_vars.selected_paper = Mock()
        sm.state_vars.draft = "some content"

        # Reset
        sm.reset()

        assert sm.current_state == WorkflowState.INITIAL
        assert sm.state_vars.last_query_set == []
        assert sm.state_vars.selected_paper is None
        assert sm.state_vars.draft is None

    def test_valid_commands_initial_state(self):
        """Test valid commands in initial state."""
        sm = StateMachine()
        valid_commands = sm.get_valid_commands()

        # Should include global commands and initial state commands
        assert "help" in valid_commands
        assert "find <query>" in valid_commands
        assert "sem-search <query>" in valid_commands
        assert "research <query>" in valid_commands
        assert "list" in valid_commands

    def test_command_validation(self):
        """Test command validation in different states."""
        sm = StateMachine()

        # In initial state
        assert sm.is_command_valid("find machine learning")
        assert sm.is_command_valid("help")
        assert sm.is_command_valid("list")
        assert not sm.is_command_valid("summarize 1")  # Not valid in initial state

        # Move to select-new state
        sm.current_state = WorkflowState.SELECT_NEW
        assert sm.is_command_valid("summarize 1")
        assert sm.is_command_valid("find new query")  # Still valid
        assert not sm.is_command_valid("improve feedback")  # Not valid in select-new

    def test_transition_after_find_success(self):
        """Test state transition after successful find command."""
        sm = StateMachine()

        result_state = sm.transition_after_find(found_papers=True)

        assert result_state == WorkflowState.SELECT_NEW
        assert sm.current_state == WorkflowState.SELECT_NEW

    def test_transition_after_find_failure(self):
        """Test state transition after failed find command."""
        sm = StateMachine()

        result_state = sm.transition_after_find(found_papers=False)

        assert result_state == WorkflowState.INITIAL
        assert sm.current_state == WorkflowState.INITIAL

    def test_transition_after_summarize(self):
        """Test state transition after summarize command."""
        sm = StateMachine()

        # Create mock paper
        paper = Mock(spec=PaperMetadata)
        paper.title = "Test Paper"
        paper.paper_id = "test.123"

        summary = "Test summary content"

        result_state = sm.transition_after_summarize(paper, summary)

        assert result_state == WorkflowState.SUMMARIZED
        assert sm.current_state == WorkflowState.SUMMARIZED
        assert sm.state_vars.selected_paper == paper
        assert sm.state_vars.draft == summary

    def test_transition_after_sem_search_success(self):
        """Test state transition after successful semantic search."""
        sm = StateMachine()

        search_results = "Search results content"
        paper_ids = ["paper1", "paper2", "paper3"]

        result_state = sm.transition_after_sem_search(
            found_results=True,
            search_results=search_results,
            paper_ids=paper_ids
        )

        assert result_state == WorkflowState.SEM_SEARCH
        assert sm.current_state == WorkflowState.SEM_SEARCH
        assert sm.state_vars.draft == search_results
        assert sm.state_vars.last_query_set == paper_ids

    def test_transition_after_research_success(self):
        """Test state transition after successful research command."""
        sm = StateMachine()

        research_results = "Research results content"
        paper_ids = ["paper1", "paper2"]

        result_state = sm.transition_after_research(
            found_results=True,
            research_results=research_results,
            paper_ids=paper_ids
        )

        assert result_state == WorkflowState.RESEARCH
        assert sm.current_state == WorkflowState.RESEARCH
        assert sm.state_vars.draft == research_results
        assert sm.state_vars.last_query_set == paper_ids

    def test_transition_after_list(self):
        """Test state transition after list command."""
        sm = StateMachine()

        result_state = sm.transition_after_list()

        assert result_state == WorkflowState.SELECT_VIEW
        assert sm.current_state == WorkflowState.SELECT_VIEW
        assert sm.state_vars.draft is None  # Draft should be cleared

    def test_state_description(self):
        """Test state descriptions."""
        sm = StateMachine()

        # Initial state
        desc = sm.get_state_description()
        assert "Ready for new command" in desc

        # Select-new state with papers
        sm.current_state = WorkflowState.SELECT_NEW
        sm.state_vars.last_query_set = ["paper1", "paper2"]
        desc = sm.get_state_description()
        assert "Found 2 papers" in desc

        # Summarized state with selected paper
        sm.current_state = WorkflowState.SUMMARIZED
        paper = Mock()
        paper.title = "Test Paper Title"
        sm.state_vars.selected_paper = paper
        desc = sm.get_state_description()
        assert "Test Paper Title" in desc


class TestStateVariables:
    """Test StateVariables functionality."""

    def test_state_variables_initialization(self):
        """Test StateVariables initialization."""
        sv = StateVariables()

        assert sv.last_query_set == []
        assert sv.selected_paper is None
        assert sv.draft is None

    def test_clear(self):
        """Test clear functionality."""
        sv = StateVariables()

        # Set some state
        sv.last_query_set = ["paper1"]
        sv.selected_paper = Mock()
        sv.draft = "content"

        # Clear
        sv.clear()

        assert sv.last_query_set == []
        assert sv.selected_paper is None
        assert sv.draft is None

    def test_set_query_results(self):
        """Test setting query results."""
        sv = StateVariables()

        paper_ids = ["paper1", "paper2"]
        sv.set_query_results(paper_ids)

        assert sv.last_query_set == paper_ids
        assert sv.selected_paper is None  # Should be cleared

    def test_set_selected_paper(self):
        """Test setting selected paper."""
        sv = StateVariables()
        sv.last_query_set = ["paper1", "paper2"]  # Set initial query state

        paper = Mock()
        draft_content = "Summary content"

        sv.set_selected_paper(paper, draft_content)

        assert sv.selected_paper == paper
        assert sv.draft == draft_content
        assert sv.last_query_set == []  # Should be cleared when selecting specific paper

    def test_set_draft(self):
        """Test setting draft content."""
        sv = StateVariables()

        content = "Draft content"
        sv.set_draft(content)

        assert sv.draft == content


class TestStateMachineFlows:
    """Test complete state machine flows based on the design document test flows."""

    def test_flow_1_find_summarize_improve_notes(self):
        """Test Flow 1: find → summarize → improve → notes."""
        sm = StateMachine()

        # Start in initial state
        assert sm.current_state == WorkflowState.INITIAL

        # 1. find command with results
        sm.transition_after_find(found_papers=True)
        assert sm.current_state == WorkflowState.SELECT_NEW
        sm.state_vars.set_query_results(["paper1", "paper2"])

        # 2. summarize command
        paper = Mock()
        paper.title = "Test Paper"
        summary = "Test summary"
        sm.transition_after_summarize(paper, summary)
        assert sm.current_state == WorkflowState.SUMMARIZED
        assert sm.state_vars.selected_paper == paper
        assert sm.state_vars.draft == summary

        # 3. improve command (stay in same state)
        improved_summary = "Improved test summary"
        sm.state_vars.set_draft(improved_summary)
        sm.stay_in_current_state()
        assert sm.current_state == WorkflowState.SUMMARIZED
        assert sm.state_vars.draft == improved_summary

        # 4. notes command (stay in same state)
        sm.stay_in_current_state()
        assert sm.current_state == WorkflowState.SUMMARIZED

    def test_flow_2_find_summarize_save(self):
        """Test Flow 2: find → summarize → save."""
        sm = StateMachine()

        # find → select-new
        sm.transition_after_find(found_papers=True)
        sm.state_vars.set_query_results(["paper1"])

        # summarize → summarized
        paper = Mock()
        summary = "Summary content"
        sm.transition_after_summarize(paper, summary)
        assert sm.current_state == WorkflowState.SUMMARIZED

        # save (stay in same state)
        sm.stay_in_current_state()
        assert sm.current_state == WorkflowState.SUMMARIZED

    def test_flow_3_list_summary_improve(self):
        """Test Flow 3: list → summary → improve."""
        sm = StateMachine()

        # list → select-view
        sm.transition_after_list()
        assert sm.current_state == WorkflowState.SELECT_VIEW
        sm.state_vars.set_query_results(["paper1", "paper2"])

        # summary → summarized
        paper = Mock()
        summary = "Existing summary"
        sm.transition_after_summary_view(paper, summary)
        assert sm.current_state == WorkflowState.SUMMARIZED

        # improve (stay in same state)
        sm.stay_in_current_state()
        assert sm.current_state == WorkflowState.SUMMARIZED

    def test_flow_4_sem_search_improve_save(self):
        """Test Flow 4: sem-search → improve → save."""
        sm = StateMachine()

        # sem-search → sem-search state
        search_results = "Search results"
        paper_ids = ["paper1", "paper2"]
        sm.transition_after_sem_search(True, search_results, paper_ids)
        assert sm.current_state == WorkflowState.SEM_SEARCH

        # improve (stay in same state)
        improved_content = "Improved search results"
        sm.state_vars.set_draft(improved_content)
        sm.stay_in_current_state()
        assert sm.current_state == WorkflowState.SEM_SEARCH

        # save (stay in same state)
        sm.stay_in_current_state()
        assert sm.current_state == WorkflowState.SEM_SEARCH

    def test_flow_5_research_save(self):
        """Test Flow 5: research → save."""
        sm = StateMachine()

        # research → research state
        research_results = "Research findings"
        paper_ids = ["paper1"]
        sm.transition_after_research(True, research_results, paper_ids)
        assert sm.current_state == WorkflowState.RESEARCH

        # save (stay in same state)
        sm.stay_in_current_state()
        assert sm.current_state == WorkflowState.RESEARCH

    def test_flow_6_find_no_results(self):
        """Test Flow 6: find (no results) → back to initial."""
        sm = StateMachine()

        # find with no results → initial
        sm.transition_after_find(found_papers=False)
        assert sm.current_state == WorkflowState.INITIAL

    def test_flow_7_sem_search_no_results(self):
        """Test Flow 7: sem-search (no results) → back to initial."""
        sm = StateMachine()

        # sem-search with no results → initial
        sm.transition_after_sem_search(False, "", [])
        assert sm.current_state == WorkflowState.INITIAL

    def test_flow_8_clear_command(self):
        """Test Flow 8: clear command from any state → initial."""
        sm = StateMachine()

        # Set up in summarized state
        sm.current_state = WorkflowState.SUMMARIZED
        sm.state_vars.selected_paper = Mock()
        sm.state_vars.draft = "content"

        # clear → initial (with reset)
        sm.reset()
        assert sm.current_state == WorkflowState.INITIAL
        assert sm.state_vars.selected_paper is None
        assert sm.state_vars.draft is None


class TestListCommandIntegration:
    """Test list command integration with state machine."""

    @pytest.mark.asyncio
    async def test_list_command_state_machine_integration(self):
        """Test that list command works with state machine and returns proper content."""
        from my_research_assistant.workflow import WorkflowRunner
        from my_research_assistant.file_locations import FileLocations
        import tempfile
        import os

        # Create temporary file locations for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_locations = FileLocations.get_locations(temp_dir)

            # Create the necessary directories
            os.makedirs(temp_locations.pdfs_dir, exist_ok=True)
            os.makedirs(temp_locations.paper_metadata_dir, exist_ok=True)

            # Create workflow runner
            runner = WorkflowRunner(llm=None, interface=None, file_locations=temp_locations)

            # Test list command when no papers exist
            result = await runner.get_list_of_papers()

            assert result.success is True
            assert result.content is not None
            assert "No papers have been downloaded yet" in result.content
            assert "find <query>" in result.content
            assert result.papers == []
            assert result.paper_ids == []

    @pytest.mark.asyncio
    async def test_list_command_with_papers_state_machine(self):
        """Test list command with papers using state machine."""
        from my_research_assistant.workflow import WorkflowRunner
        from my_research_assistant.file_locations import FileLocations
        from unittest.mock import patch, Mock
        import tempfile
        import os

        # Create temporary file locations for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_locations = FileLocations.get_locations(temp_dir)

            # Create the necessary directories
            os.makedirs(temp_locations.pdfs_dir, exist_ok=True)
            os.makedirs(temp_locations.paper_metadata_dir, exist_ok=True)

            # Create mock PDF file to simulate downloaded paper
            paper_id = "test.123"
            pdf_path = os.path.join(temp_locations.pdfs_dir, f"{paper_id}.pdf")
            with open(pdf_path, 'w') as f:
                f.write("mock pdf content")

            # Mock the get_paper_metadata function to return our test paper
            mock_paper = Mock()
            mock_paper.title = "Test Paper Title"
            mock_paper.authors = ["Author One", "Author Two"]
            mock_paper.paper_id = paper_id
            mock_paper.published = Mock()
            mock_paper.published.strftime.return_value = "2024-01-01"

            with patch('my_research_assistant.arxiv_downloader.get_paper_metadata') as mock_get_metadata:
                mock_get_metadata.return_value = mock_paper

                # Create workflow runner
                runner = WorkflowRunner(llm=None, interface=None, file_locations=temp_locations)

                # Test list command
                result = await runner.get_list_of_papers()

                assert result.success is True
                assert result.content is not None
                assert "Test Paper Title" in result.content
                assert "Author One, Author Two" in result.content
                assert paper_id in result.content
                assert len(result.papers) == 1
                assert len(result.paper_ids) == 1
                assert result.paper_ids[0] == paper_id

    @pytest.mark.asyncio
    async def test_list_command_state_transition(self):
        """Test that list command causes proper state transition."""
        from my_research_assistant.state_machine import StateMachine, WorkflowState

        # Create state machine
        sm = StateMachine()

        # Start in initial state
        assert sm.current_state == WorkflowState.INITIAL

        # Simulate list command result with papers found
        sm.transition_after_list()

        # Should transition to select-view state
        assert sm.current_state == WorkflowState.SELECT_VIEW

        # Draft should be cleared after list
        assert sm.state_vars.draft is None

    @pytest.mark.asyncio
    async def test_list_command_pagination_integration(self):
        """Test that list command pagination works with many papers."""
        from my_research_assistant.chat import ChatInterface
        from my_research_assistant.workflow import WorkflowRunner
        from my_research_assistant.file_locations import FileLocations
        from unittest.mock import patch, Mock, AsyncMock
        import tempfile
        import os

        # Create temporary file locations for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_locations = FileLocations.get_locations(temp_dir)

            # Create the necessary directories
            os.makedirs(temp_locations.pdfs_dir, exist_ok=True)
            os.makedirs(temp_locations.paper_metadata_dir, exist_ok=True)

            # Create mock PDF files to simulate many downloaded papers (15 papers for pagination test)
            mock_papers = []
            for i in range(15):
                paper_id = f"test.{i+1:03d}"
                pdf_path = os.path.join(temp_locations.pdfs_dir, f"{paper_id}.pdf")
                with open(pdf_path, 'w') as f:
                    f.write("mock pdf content")

                # Create mock paper metadata
                mock_paper = Mock()
                mock_paper.title = f"Test Paper Title {i+1}"
                mock_paper.authors = [f"Author {i+1}A", f"Author {i+1}B"]
                mock_paper.paper_id = paper_id
                mock_paper.published = Mock()
                mock_paper.published.strftime.return_value = f"2024-01-{(i%30)+1:02d}"
                mock_papers.append(mock_paper)

            # Mock the get_paper_metadata function to return our test papers
            def mock_get_metadata(paper_id):
                # Find the matching mock paper
                for paper in mock_papers:
                    if paper.paper_id == paper_id:
                        return paper
                return None

            with patch('my_research_assistant.arxiv_downloader.get_paper_metadata', side_effect=mock_get_metadata):
                # Create chat interface
                chat = ChatInterface()
                runner = WorkflowRunner(llm=None, interface=None, file_locations=temp_locations)
                chat.workflow_runner = runner

                # Mock user input to exit pagination after first page
                with patch('rich.prompt.Prompt.ask', return_value='q'):
                    # Test list command with pagination
                    await chat.process_list_command()

                # Verify state machine was updated correctly
                assert chat.state_machine.current_state.value == "select-view"
                assert len(chat.state_machine.state_vars.last_query_set) == 15

                # Check that conversation history was updated
                assert len(chat.conversation_history) >= 1
                history_content = chat.conversation_history[-1]['content']
                assert "15 downloaded papers" in history_content


class TestSummaryCommandEnhancements:
    """Test enhanced summary command functionality."""

    @pytest.mark.asyncio
    async def test_summary_command_missing_summary_decline(self):
        """Test summary command when summary is missing and user declines to create."""
        from my_research_assistant.chat import ChatInterface
        from my_research_assistant.workflow import WorkflowRunner
        from my_research_assistant.file_locations import FileLocations
        from unittest.mock import patch, Mock
        import tempfile

        # Create temporary file locations for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_locations = FileLocations.get_locations(temp_dir)

            # Create chat interface
            chat = ChatInterface()
            runner = WorkflowRunner(llm=None, interface=None, file_locations=temp_locations)
            chat.workflow_runner = runner

            # Create a mock paper that exists but has no summary
            mock_paper = Mock()
            mock_paper.title = 'Test Paper Without Summary'
            mock_paper.paper_id = 'test.999'
            mock_paper.authors = ['Test Author']

            # Mock the paper resolution and summary loading
            with patch('my_research_assistant.paper_manager.resolve_paper_reference', return_value=(mock_paper, '')):
                with patch('my_research_assistant.paper_manager.load_paper_summary', return_value=(False, 'No summary found')):
                    with patch('rich.prompt.Confirm.ask', return_value=False):
                        # Test summary command with missing summary
                        await chat.process_summary_command('test.999')

                        # Verify state didn't change (user declined)
                        assert chat.state_machine.current_state.value == "initial"
                        assert chat.state_machine.state_vars.selected_paper is None

    @pytest.mark.asyncio
    async def test_summary_command_missing_summary_accept(self):
        """Test summary command when summary is missing and user accepts creation."""
        from my_research_assistant.chat import ChatInterface
        from my_research_assistant.workflow import WorkflowRunner
        from my_research_assistant.file_locations import FileLocations
        from unittest.mock import patch, Mock
        import tempfile

        # Create temporary file locations for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_locations = FileLocations.get_locations(temp_dir)

            # Create chat interface
            chat = ChatInterface()
            runner = WorkflowRunner(llm=None, interface=None, file_locations=temp_locations)
            chat.workflow_runner = runner

            # Create a mock paper that exists but has no summary
            mock_paper = Mock()
            mock_paper.title = 'Test Paper Without Summary'
            mock_paper.paper_id = '2107.03374v1'
            mock_paper.authors = ['Test Author']

            # Create mock processing result
            mock_result = Mock()
            mock_result.paper = mock_paper
            mock_result.summary = "Generated test summary content"

            # Mock the paper argument parsing, summary loading, and paper processing
            with patch('my_research_assistant.paper_manager.parse_paper_argument', return_value=(mock_paper, '')):
                with patch('my_research_assistant.paper_manager.load_paper_summary', return_value=(False, 'No summary found')):
                    with patch('rich.prompt.Confirm.ask', return_value=True):
                        with patch.object(runner, 'process_paper_selection', return_value=mock_result):
                            # Test summary command with missing summary
                            await chat.process_summary_command('2107.03374v1')

                            # Verify state transitioned to summarized
                            assert chat.state_machine.current_state.value == "summarized"
                            assert chat.state_machine.state_vars.selected_paper == mock_paper
                            assert chat.state_machine.state_vars.draft == "Generated test summary content"

    @pytest.mark.asyncio
    async def test_summary_command_existing_summary(self):
        """Test summary command when summary already exists."""
        from my_research_assistant.chat import ChatInterface
        from my_research_assistant.workflow import WorkflowRunner
        from my_research_assistant.file_locations import FileLocations
        from unittest.mock import patch, Mock
        import tempfile

        # Create temporary file locations for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_locations = FileLocations.get_locations(temp_dir)

            # Create chat interface
            chat = ChatInterface()
            runner = WorkflowRunner(llm=None, interface=None, file_locations=temp_locations)
            chat.workflow_runner = runner

            # Create a mock paper with existing summary
            mock_paper = Mock()
            mock_paper.title = 'Test Paper With Summary'
            mock_paper.paper_id = '2210.12345v1'
            mock_paper.authors = ['Test Author']

            existing_summary = "This is an existing summary content"

            # Mock the paper argument parsing and summary loading
            with patch('my_research_assistant.paper_manager.parse_paper_argument', return_value=(mock_paper, '')):
                with patch('my_research_assistant.paper_manager.load_paper_summary', return_value=(True, existing_summary)):
                    # Test summary command with existing summary
                    await chat.process_summary_command('2210.12345v1')

                    # Verify state transitioned to summarized with existing content
                    assert chat.state_machine.current_state.value == "summarized"
                    assert chat.state_machine.state_vars.selected_paper == mock_paper
                    assert chat.state_machine.state_vars.draft == existing_summary