"""Tests for search functionality in vector_store.py - summary and filtered search."""

import os
import pytest
import tempfile
from os.path import join
from unittest.mock import patch, MagicMock
from my_research_assistant import file_locations
from my_research_assistant.project_types import PaperMetadata
import datetime

EXAMPLE_PAPER_ID = '2503.22738'
EXAMPLE_PAPER_ID_2 = '2503.00237'


def create_mock_metadata(paper_id: str, title: str | None = None) -> PaperMetadata:
    """Create a mock PaperMetadata object for testing."""
    if title is None:
        title = f"Test Paper {paper_id}"
    return PaperMetadata(
        paper_id=paper_id,
        title=title,
        published=datetime.datetime(2025, 3, 1),
        updated=None,
        paper_abs_url=f"http://arxiv.org/abs/{paper_id}",
        paper_pdf_url=f"http://arxiv.org/pdf/{paper_id}.pdf",
        authors=["Test Author"],
        categories=["cs.AI"],
        abstract="Test abstract for paper.",
        doi=None,
        journal_ref=None
    )


def create_minimal_pdf(file_locations, paper_id: str):
    """Create a minimal test PDF file."""
    file_locations.ensure_pdfs_dir()
    pdf_path = join(file_locations.pdfs_dir, f"{paper_id}.pdf")
    # Create a minimal valid PDF
    with open(pdf_path, 'wb') as f:
        f.write(b'%PDF-1.4\n')
        f.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
        f.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
        f.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n')
        f.write(b'4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 100 Td (Test content) Tj ET\nendstream\nendobj\n')
        f.write(b'xref\n0 5\n')
        f.write(b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n')
    return pdf_path


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

        # Clear ChromaDB shared system state before resetting indexes
        try:
            import chromadb.api.shared_system_client as shared_system
            if hasattr(shared_system.SharedSystemClient, '_identifier_to_system'):
                # Properly shut down any existing systems before clearing
                for system in list(shared_system.SharedSystemClient._identifier_to_system.values()):
                    try:
                        system.stop()
                    except Exception:
                        pass
                shared_system.SharedSystemClient._identifier_to_system.clear()
        except Exception:
            pass  # Ignore if ChromaDB internals changed

        vs.CONTENT_INDEX = None
        vs.SUMMARY_INDEX = None

        try:
            yield temp_locations
        finally:
            # Clean up ChromaDB state before restoring
            vs.CONTENT_INDEX = None
            vs.SUMMARY_INDEX = None

            try:
                import chromadb.api.shared_system_client as shared_system
                if hasattr(shared_system.SharedSystemClient, '_identifier_to_system'):
                    # Properly shut down any existing systems before clearing
                    for system in list(shared_system.SharedSystemClient._identifier_to_system.values()):
                        try:
                            system.stop()
                        except Exception:
                            pass
                    shared_system.SharedSystemClient._identifier_to_system.clear()
            except Exception:
                pass

            file_locations.FILE_LOCATIONS = original_file_locations
            vs.CONTENT_INDEX = original_content_index
            vs.SUMMARY_INDEX = original_summary_index
            vs.FILE_LOCATIONS = original_vs_file_locations


@pytest.fixture
def mock_pdf_operations():
    """Mock expensive PDF operations to speed up tests."""
    from llama_index.core.schema import Document

    def mock_download_paper(metadata, file_locs):
        """Mock download - just create a minimal PDF."""
        return create_minimal_pdf(file_locs, metadata.paper_id)

    def mock_load_data(pdf_path):
        """Mock PDF text extraction - return LlamaIndex Document objects."""
        # Extract paper_id from path
        paper_id = pdf_path.split('/')[-1].replace('.pdf', '')

        # Return simple test documents
        return [
            Document(
                text=f"""# Test Paper {paper_id}

## Abstract
This is a test paper about agent safety and verification mechanisms.

## Introduction
We discuss shielding agents via verifiable safety policy reasoning.
""",
                metadata={"page": 0}
            ),
            Document(
                text="""## Methods
Novel safety verification mechanism for LLM agents.

## Conclusion
Practical implementation with formal guarantees.
""",
                metadata={"page": 1}
            )
        ]

    # Create a mock reader class
    mock_reader = MagicMock()
    mock_reader.load_data = mock_load_data

    def mock_llama_markdown_reader():
        return mock_reader

    with patch('my_research_assistant.arxiv_downloader.download_paper', side_effect=mock_download_paper), \
         patch('my_research_assistant.vector_store.pymupdf4llm.LlamaMarkdownReader', side_effect=mock_llama_markdown_reader):
        yield


class TestSearchSummaryIndex:
    """Test the search_summary_index function."""

    def test_search_summary_index_basic(self, temp_file_locations):
        """Test basic summary index search functionality."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Use mock metadata
        md = create_mock_metadata(EXAMPLE_PAPER_ID, "ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning")

        # Create and index a summary
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        summary_content = """# ShieldAgent: Shielding Agents via Verifiable Safety Policy Reasoning

## Summary
This paper introduces ShieldAgent, a framework for ensuring agent safety through verifiable policy reasoning.

## Key Contributions
- Novel safety verification mechanism
- Practical implementation for LLM agents
- Formal guarantees for safety properties
"""
        with open(summary_path, 'w') as f:
            f.write(summary_content)

        vs.index_summary(md, temp_file_locations)

        # Search the summary index
        results = vs.search_summary_index("safety verification mechanism", k=3,
                                          file_locations=temp_file_locations)

        assert len(results) > 0, "Should find results in summary index"
        assert len(results) <= 3, "Should respect k parameter"

        # Verify result structure
        for result in results:
            assert hasattr(result, 'paper_id')
            assert hasattr(result, 'chunk')
            assert hasattr(result, 'paper_title')
            assert result.paper_id == EXAMPLE_PAPER_ID
            assert '[SUMMARY]' in result.chunk  # Should be prefixed with source type

    def test_search_summary_index_with_k_parameter(self, temp_file_locations):
        """Test that k parameter controls result count."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        # Create a longer summary
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\n\n" + "\n\n".join([
                f"Section {i}: Discussion of agent safety mechanisms and verification approaches."
                for i in range(10)
            ]))

        vs.index_summary(md, temp_file_locations)

        # Test different k values
        results_k1 = vs.search_summary_index("agent safety", k=1, file_locations=temp_file_locations)
        results_k5 = vs.search_summary_index("agent safety", k=5, file_locations=temp_file_locations)

        assert len(results_k1) <= 1
        assert len(results_k5) <= 5

    def test_search_summary_index_no_database_error(self, temp_file_locations):
        """Test that search_summary_index raises error when no database exists."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations
        vs.SUMMARY_INDEX = None

        with pytest.raises(vs.IndexError) as exc_info:
            vs.search_summary_index("any query", file_locations=temp_file_locations)

        assert "No existing ChromaDB found" in str(exc_info.value)

    def test_search_summary_index_with_mmr(self, temp_file_locations):
        """Test summary search with MMR enabled."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        # Create summary
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\nAgent safety verification methods and approaches.")

        vs.index_summary(md, temp_file_locations)

        # Search with MMR enabled (may fall back to default)
        results = vs.search_summary_index("safety verification", k=3,
                                          file_locations=temp_file_locations,
                                          use_mmr=True)

        assert isinstance(results, list)
        assert len(results) <= 3

    def test_search_summary_index_with_similarity_cutoff(self, temp_file_locations):
        """Test summary search with similarity filtering."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        # Create summary
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\nDiscussion of ShieldAgent framework.")

        vs.index_summary(md, temp_file_locations)

        # Search with high similarity cutoff
        results_high_cutoff = vs.search_summary_index("ShieldAgent framework", k=5,
                                                      file_locations=temp_file_locations,
                                                      similarity_cutoff=0.7)

        # Search with low similarity cutoff
        results_low_cutoff = vs.search_summary_index("ShieldAgent framework", k=5,
                                                     file_locations=temp_file_locations,
                                                     similarity_cutoff=0.3)

        # High cutoff may filter out more results
        assert isinstance(results_high_cutoff, list)
        assert isinstance(results_low_cutoff, list)


class TestSearchContentIndexFiltered:
    """Test the search_content_index_filtered function."""

    def test_filtered_search_basic(self, temp_file_locations, mock_pdf_operations):
        """Test basic filtered search functionality."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        # Use mock metadata and operations
        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        # Mock download and index
        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        # Search with paper ID filter
        results = vs.search_content_index_filtered(
            "agent safety",
            paper_ids=[EXAMPLE_PAPER_ID],
            k=3,
            file_locations=temp_file_locations
        )

        assert len(results) > 0, "Should find results when filtering to existing paper"
        assert len(results) <= 3, "Should respect k parameter"

        # All results should be from the filtered paper
        for result in results:
            assert result.paper_id == EXAMPLE_PAPER_ID

    def test_filtered_search_excludes_other_papers(self, temp_file_locations, mock_pdf_operations):
        """Test that filtering excludes papers not in the filter list."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        # Search with a different paper ID (not indexed)
        results = vs.search_content_index_filtered(
            "agent",
            paper_ids=["9999.99999"],  # Non-existent paper
            k=5,
            file_locations=temp_file_locations
        )

        # Should return no results or empty list
        assert len(results) == 0, "Should not find results for non-existent paper ID"

    def test_filtered_search_multiple_papers(self, temp_file_locations, mock_pdf_operations):
        """Test filtered search with multiple paper IDs."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        # Search with multiple paper IDs (one exists, one doesn't)
        results = vs.search_content_index_filtered(
            "agent",
            paper_ids=[EXAMPLE_PAPER_ID, "9999.99999"],
            k=5,
            file_locations=temp_file_locations
        )

        # Should only return results from the existing paper
        assert all(r.paper_id == EXAMPLE_PAPER_ID for r in results)

    def test_filtered_search_with_similarity_cutoff(self, temp_file_locations, mock_pdf_operations):
        """Test filtered search with similarity filtering."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        # Search with similarity cutoff
        results = vs.search_content_index_filtered(
            "shielding agents verifiable",
            paper_ids=[EXAMPLE_PAPER_ID],
            k=5,
            file_locations=temp_file_locations,
            similarity_cutoff=0.6
        )

        assert isinstance(results, list)
        # Results should be high quality matches
        if len(results) > 0:
            assert all(r.paper_id == EXAMPLE_PAPER_ID for r in results)

    def test_filtered_search_no_database_error(self, temp_file_locations):
        """Test that filtered search raises error when no database exists."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations
        vs.CONTENT_INDEX = None

        with pytest.raises(vs.IndexError) as exc_info:
            vs.search_content_index_filtered("query", paper_ids=["test"], file_locations=temp_file_locations)

        assert "No existing ChromaDB found" in str(exc_info.value)

    def test_filtered_search_result_structure(self, temp_file_locations, mock_pdf_operations):
        """Test that filtered search returns properly structured results."""
        import my_research_assistant.vector_store as vs
        from my_research_assistant.project_types import SearchResult

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        results = vs.search_content_index_filtered(
            "agent",
            paper_ids=[EXAMPLE_PAPER_ID],
            k=2,
            file_locations=temp_file_locations
        )

        assert len(results) > 0

        for result in results:
            assert isinstance(result, SearchResult)
            assert hasattr(result, 'paper_id')
            assert hasattr(result, 'pdf_filename')
            assert hasattr(result, 'paper_title')
            assert hasattr(result, 'page')
            assert hasattr(result, 'chunk')
            assert isinstance(result.page, int)
            assert len(result.chunk) > 0


class TestSearchWithMMRAndDiversity:
    """Test MMR and manual diversity strategies."""

    def test_search_index_mmr_fallback(self, temp_file_locations, mock_pdf_operations):
        """Test that search_index handles MMR failures gracefully."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        # Try search with MMR (may fall back to manual diversity)
        results = vs.search_index("agent safety", k=5, file_locations=temp_file_locations,
                                  use_mmr=True, similarity_cutoff=0.5)

        assert isinstance(results, list)
        assert len(results) <= 5

    def test_search_without_mmr(self, temp_file_locations, mock_pdf_operations):
        """Test search with MMR disabled (uses hybrid mode)."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        # Search without MMR
        results = vs.search_index("agent safety", k=5, file_locations=temp_file_locations,
                                  use_mmr=False)

        assert isinstance(results, list)
        assert len(results) <= 5


class TestSearchEdgeCases:
    """Test edge cases and error handling in search functions."""

    def test_search_summary_index_empty_results(self, temp_file_locations):
        """Test summary search with query unlikely to match."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        # Create summary
        temp_file_locations.ensure_summaries_dir()
        summary_path = join(temp_file_locations.summaries_dir, f"{EXAMPLE_PAPER_ID}.md")
        with open(summary_path, 'w') as f:
            f.write("# Summary\nDiscussion of agent safety.")

        vs.index_summary(md, temp_file_locations)

        # Search for completely unrelated content
        results = vs.search_summary_index("quantum computing blockchain cryptocurrency",
                                          k=5, file_locations=temp_file_locations)

        # Should handle gracefully
        assert isinstance(results, list)

    def test_filtered_search_empty_paper_list(self, temp_file_locations, mock_pdf_operations):
        """Test filtered search with empty paper ID list."""
        import my_research_assistant.vector_store as vs

        vs.FILE_LOCATIONS = temp_file_locations

        md = create_mock_metadata(EXAMPLE_PAPER_ID)

        from my_research_assistant.arxiv_downloader import download_paper
        download_paper(md, temp_file_locations)
        vs.index_file(md, temp_file_locations)

        # Search with empty filter list
        results = vs.search_content_index_filtered(
            "agent",
            paper_ids=[],
            k=5,
            file_locations=temp_file_locations
        )

        # Should return empty results
        assert len(results) == 0
