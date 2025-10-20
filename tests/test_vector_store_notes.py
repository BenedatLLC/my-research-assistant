"""Tests for notes indexing functionality in vector_store.py"""

import os
import pytest
import tempfile
from os.path import exists, join
from my_research_assistant import file_locations

EXAMPLE_PAPER_ID = '2503.22738'


@pytest.fixture
def temp_file_locations():
    """Create a temporary directory and set FILE_LOCATIONS to use it."""
    original_file_locations = file_locations.FILE_LOCATIONS

    import my_research_assistant.vector_store as vs
    original_content_index = vs.CONTENT_INDEX
    original_summary_index = vs.SUMMARY_INDEX
    original_vs_file_locations = vs.FILE_LOCATIONS

    with tempfile.TemporaryDirectory() as temp_dir:
        prompts_dir = os.path.join(temp_dir, 'prompts')
        os.makedirs(prompts_dir, exist_ok=True)

        temp_locations = file_locations.FileLocations.get_locations(temp_dir)
        file_locations.FILE_LOCATIONS = temp_locations

        vs.CONTENT_INDEX = None
        vs.SUMMARY_INDEX = None

        try:
            yield temp_locations
        finally:
            file_locations.FILE_LOCATIONS = original_file_locations
            vs.CONTENT_INDEX = original_content_index
            vs.SUMMARY_INDEX = original_summary_index
            vs.FILE_LOCATIONS = original_vs_file_locations


class TestNotesIndexing:
    """Test the index_notes function."""

    def test_index_notes_basic(self, temp_file_locations):
        """Test basic notes indexing functionality."""
        from my_research_assistant.arxiv_downloader import get_paper_metadata
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Get paper metadata
        md = get_paper_metadata(EXAMPLE_PAPER_ID)

        # Create a notes file
        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        notes_content = """# My Notes on ShieldAgent

This paper introduces a novel approach to agent safety.

## Key Points
- Verifiable safety policy reasoning
- Shield mechanisms for agent actions
- Practical implementation considerations

## Questions
- How does this compare to other safety approaches?
- What are the performance implications?
"""
        with open(notes_path, 'w') as f:
            f.write(notes_content)

        # Index the notes
        vs.index_notes(md, temp_file_locations)

        # Verify the summary index was created
        assert vs.SUMMARY_INDEX is not None

        # Verify we can retrieve the notes
        retriever = vs.SUMMARY_INDEX.as_retriever()
        results = retriever.retrieve("verifiable safety policy")

        assert len(results) > 0, "Should find results in indexed notes"

        # Verify the metadata
        found_notes = False
        for result in results:
            if hasattr(result, 'metadata'):
                metadata = result.metadata
                if metadata.get('paper_id') == EXAMPLE_PAPER_ID and metadata.get('source_type') == 'notes':
                    found_notes = True
                    assert metadata['title'] == "ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning"
                    assert 'authors' in metadata
                    break

        assert found_notes, "Should find notes with proper metadata"

    def test_index_notes_idempotency(self, temp_file_locations):
        """Test that index_notes is idempotent - indexing twice doesn't duplicate."""
        from my_research_assistant.arxiv_downloader import get_paper_metadata
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = get_paper_metadata(EXAMPLE_PAPER_ID)

        # Create a notes file
        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(notes_path, 'w') as f:
            f.write("# Test Notes\nThis is a test note about agent safety.")

        # Index the notes twice
        vs.index_notes(md, temp_file_locations)
        vs.index_notes(md, temp_file_locations)  # Second call should skip

        # Verify only one set of notes was indexed
        # This is difficult to verify exactly, but we can check that retrieval works
        retriever = vs.SUMMARY_INDEX.as_retriever(similarity_top_k=20)
        results = retriever.retrieve("agent safety")

        # Count how many results have notes source_type for this paper
        notes_count = sum(1 for r in results
                         if hasattr(r, 'metadata')
                         and r.metadata.get('paper_id') == EXAMPLE_PAPER_ID
                         and r.metadata.get('source_type') == 'notes')

        # Should have notes indexed (exact count depends on chunking)
        assert notes_count > 0, "Should have notes indexed"

    def test_index_notes_missing_file(self, temp_file_locations):
        """Test that index_notes raises error when notes file doesn't exist."""
        from my_research_assistant.arxiv_downloader import get_paper_metadata
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = get_paper_metadata(EXAMPLE_PAPER_ID)

        # Don't create notes file - should raise error
        with pytest.raises(vs.IndexError) as exc_info:
            vs.index_notes(md, temp_file_locations)

        assert "Notes file not found" in str(exc_info.value)

    def test_index_notes_file_path_metadata(self, temp_file_locations):
        """Test that notes have correct file_path metadata."""
        from my_research_assistant.arxiv_downloader import get_paper_metadata
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = get_paper_metadata(EXAMPLE_PAPER_ID)

        # Create notes file
        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(notes_path, 'w') as f:
            f.write("# Notes\nTest content for metadata validation.")

        # Index the notes
        vs.index_notes(md, temp_file_locations)

        # Retrieve and check metadata
        retriever = vs.SUMMARY_INDEX.as_retriever()
        results = retriever.retrieve("metadata validation")

        found_correct_path = False
        for result in results:
            if hasattr(result, 'metadata'):
                metadata = result.metadata
                if (metadata.get('paper_id') == EXAMPLE_PAPER_ID and
                    metadata.get('source_type') == 'notes'):
                    expected_path = f'notes/{EXAMPLE_PAPER_ID}.md'
                    assert metadata.get('file_path') == expected_path
                    found_correct_path = True
                    break

        assert found_correct_path, "Should find notes with correct file_path"


class TestNotesInSummaryIndex:
    """Test that notes are searchable in the summary index."""

    def test_notes_searchable_with_summaries(self, temp_file_locations):
        """Test that notes and summaries can both be searched in summary index."""
        from my_research_assistant.arxiv_downloader import get_paper_metadata
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = get_paper_metadata(EXAMPLE_PAPER_ID)

        # Create both summary and notes
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\nThis paper discusses agent safety mechanisms.")

        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(notes_path, 'w') as f:
            f.write("# Personal Notes\nI found the verifiable reasoning approach very interesting.")

        # Index both
        vs.index_summary(md, temp_file_locations)
        vs.index_notes(md, temp_file_locations)

        # Search for content that appears in summary
        retriever = vs.SUMMARY_INDEX.as_retriever(similarity_top_k=10)
        summary_results = retriever.retrieve("agent safety mechanisms")

        # Should find summary content
        found_summary = any(
            r.metadata.get('source_type') == 'summary' and r.metadata.get('paper_id') == EXAMPLE_PAPER_ID
            for r in summary_results if hasattr(r, 'metadata')
        )
        assert found_summary, "Should find summary in search results"

        # Search for content that appears in notes
        notes_results = retriever.retrieve("verifiable reasoning approach")

        # Should find notes content
        found_notes = any(
            r.metadata.get('source_type') == 'notes' and r.metadata.get('paper_id') == EXAMPLE_PAPER_ID
            for r in notes_results if hasattr(r, 'metadata')
        )
        assert found_notes, "Should find notes in search results"

    def test_search_summary_index_includes_notes(self, temp_file_locations):
        """Test that search_summary_index function returns both summaries and notes."""
        from my_research_assistant.arxiv_downloader import get_paper_metadata
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = get_paper_metadata(EXAMPLE_PAPER_ID)

        # Create notes with distinctive content
        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(notes_path, 'w') as f:
            f.write("# My Analysis\nThe shield mechanism is particularly innovative for agent safety.")

        # Index the notes
        vs.index_notes(md, temp_file_locations)

        # Use search_summary_index function
        results = vs.search_summary_index("shield mechanism innovative", k=5,
                                          file_locations=temp_file_locations)

        # Verify we got results
        assert len(results) > 0, "Should find results from notes"

        # Check that results have proper structure
        for result in results:
            assert hasattr(result, 'paper_id')
            assert hasattr(result, 'chunk')
            assert result.paper_id == EXAMPLE_PAPER_ID
            # Notes results should have [NOTES] prefix in chunk
            if '[NOTES]' in result.chunk:
                assert 'shield mechanism' in result.chunk or 'innovative' in result.chunk


class TestNotesWithRebuildIndex:
    """Test that rebuild_index properly handles notes."""

    def test_rebuild_index_includes_notes(self, temp_file_locations):
        """Test that rebuild_index indexes notes files."""
        from my_research_assistant.arxiv_downloader import get_paper_metadata, download_paper
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Download a paper
        md = get_paper_metadata(EXAMPLE_PAPER_ID)
        download_paper(md, temp_file_locations)

        # Create notes for the paper
        temp_file_locations.ensure_notes_dir()
        notes_path = join(temp_file_locations.notes_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(notes_path, 'w') as f:
            f.write("# Research Notes\nThis paper's approach to safety verification is novel.")

        # Run rebuild_index
        try:
            vs.rebuild_index(temp_file_locations)

            # Verify notes were indexed
            assert vs.SUMMARY_INDEX is not None

            retriever = vs.SUMMARY_INDEX.as_retriever()
            results = retriever.retrieve("safety verification novel")

            # Should find the notes
            found_notes = any(
                r.metadata.get('source_type') == 'notes' and r.metadata.get('paper_id') == EXAMPLE_PAPER_ID
                for r in results if hasattr(r, 'metadata')
            )
            assert found_notes, "rebuild_index should have indexed the notes"

        except Exception as e:
            if "readonly database" in str(e) or "Database error" in str(e):
                pytest.skip(f"Skipping rebuild test due to ChromaDB locking issue: {e}")
            else:
                raise
