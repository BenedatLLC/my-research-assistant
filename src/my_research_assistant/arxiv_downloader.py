"""Download papers from arxiv"""
from os.path import join, exists, basename
import os
import datetime
import logging
import json
import re
from typing import Optional
from pydantic import BaseModel
import arxiv
from .file_locations import FILE_LOCATIONS, FileLocations
from .project_types import PaperMetadata

CATEGORY_DATA=\
"""category_id,category_name,description
cs.AI,"Artificial Intelligence","Covers all areas of AI except Vision, Robotics, Machine Learning, Multiagent Systems, and Computation and Language (Natural Language Processing), which have separate subject areas. In particular, includes Expert Systems, Theorem Proving (although this may overlap with Logic in Computer Science), Knowledge Representation, Planning, and Uncertainty in AI. Roughly includes material in ACM Subject Classes I.2.0, I.2.1, I.2.3, I.2.4, I.2.8, and I.2.11."
cs.AR,"Hardware Architecture","Systems Organization. Roughly includes material in ACM Subject Class C.0, C.1, and C.5."
cs.CC,"Computational Complexity","Models of computation, complexity classes, structural complexity, complexity tradeoffs. Roughly includes material in ACM Subject Class F.1."
cs.CE,"Computational Engineering, Finance, and Science","Applications of computer science to the mathematical modeling of problems in science, engineering, and finance. General purpose application of supercomputers and distributed computing environments to solve specific problems. Does not include traditional numerical analysis or computational physics, which are part of the physics archive. Roughly includes material in ACM Subject Classes J.2, J.3, and J.4."
cs.CG,"Computational Geometry","Roughly includes material in ACM Subject Class I.3.5."
cs.CL,"Computation and Language","Natural Language Processing. Roughly includes material in ACM Subject Class I.2.7."
cs.CR,"Cryptography and Security","All aspects of cryptography and security. Roughly includes material in ACM Subject Classes D.4.6 and E.3."
cs.CV,"Computer Vision and Pattern Recognition","Image Processing, Computer Vision, Pattern Recognition, and Scene Understanding. Roughly includes material in ACM Subject Classes I.2.10, I.4, and I.5."
cs.CY,"Computers and Society","Impact of computers on society, computer ethics, information technology and public policy. Roughly includes material in ACM Subject Classes K.0, K.2, K.3, K.4, K.5, and K.7."
cs.DB,"Databases","Database Management, Datamining, and Data Processing. Roughly includes material in ACM Subject Classes H.2, H.3, and E.2."
cs.DC,"Distributed, Parallel, and Cluster Computing","Fault-tolerance, distributed algorithms, stability, parallel computation, memory consistency. Roughly includes material in ACM Subject Classes C.2.4, D.1.3, D.4.5, D.4.7, E.1."
cs.DL,"Digital Libraries","Design and analysis of algorithms and systems for digital libraries. Roughly includes material in ACM Subject Class H.3.7."
cs.DM,"Discrete Mathematics","Combinatorics, graph theory, applications of probability. Roughly includes material in ACM Subject Classes G.2 and G.3."
cs.DS,"Data Structures and Algorithms","Data structures and analysis of algorithms. Roughly includes material in ACM Subject Classes E.1, E.2, F.2."
cs.ET,"Emerging Technologies","Alternative information processing technologies and models, including quantum computing, biological computing, and nanoscale computing."
cs.FL,"Formal Languages and Automata Theory","Theory of formal languages, automata theory, computability theory. Roughly includes material in ACM Subject Class F.1.1, F.4.3."
cs.GL,"General Literature","General-interest literature, including introductory material, survey material, predictions for the future, biographies, and miscellaneous computer-science related material. Roughly includes material in ACM Subject Classes A.0, A.1, and A.2."
cs.GR,"Graphics","All aspects of computer graphics. Roughly includes material in ACM Subject Class I.3."
cs.GT,"Computer Science and Game Theory","Intersection of computer science and game theory, including games in artificial intelligence, multi-agent systems, and the Internet."
cs.HC,"Human-Computer Interaction","Human factors, user interfaces, collaborative computing. Roughly includes material in ACM Subject Classes H.1.2 and H.5."
cs.IR,"Information Retrieval","Indexing, ranking, and content analysis. Roughly includes material in ACM Subject Class H.3."
cs.IT,"Information Theory","Theoretical and experimental aspects of information theory and coding."
cs.LG,"Machine Learning","All aspects of machine learning research and applications."
cs.LO,"Logic in Computer Science","Finite model theory, logics of programs, modal and temporal logics, program verification, automated theorem proving. Roughly includes material in ACM Subject Classes D.2.4, F.3.1, F.4.0, F.4.1."
cs.MA,"Multiagent Systems","Distributed Artificial Intelligence, intelligent agents, multi-agent systems. Roughly includes material in ACM Subject Class I.2.11."
cs.MM,"Multimedia",""
cs.MS,"Mathematical Software",""
cs.NA,"Numerical Analysis",""
cs.NE,"Neural and Evolutionary Computing","Neural networks, connectionism, genetic algorithms, artificial life, adaptive behavior. Roughly includes material in ACM Subject Class C.1.3, I.2.6, I.5."
cs.NI,"Networking and Internet Architecture","Computer communication networks, network protocols, network services, network performance, internetworking. Roughly includes material in ACM Subject Class C.2."
cs.OH,"Other Computer Science","This is the classification for documents that do not fit in any other category."
cs.OS,"Operating Systems","Roughly includes material in ACM Subject Class D.4."
cs.PF,"Performance","Roughly includes material in ACM Subject Class D.4.8, K.6.2."
cs.PL,"Programming Languages","Compilers, interpreters, programming language semantics, programming language design. Roughly includes material in ACM Subject Classes D.3."
cs.RO,"Robotics","Roughly includes material in ACM Subject Class I.2.9."
cs.SC,"Symbolic Computation",""
cs.SD,"Sound",""
cs.SE,"Software Engineering","Requirements analysis, software design, verification, testing. Roughly includes material in ACM Subject Classes D.2."
cs.SI,"Social and Information Networks","Analysis of social and information networks, including their structure, evolution, and dynamics."
cs.SY,"Systems and Control","cs.SY is an alias for eess.SY. This section includes theoretical and experimental research covering all facets of automatic control systems. The section is focused on methods of control system analysis and design using tools of modeling, simulation and optimization. Specific areas of research include nonlinear, distributed, adaptive, stochastic and robust control in addition to hybrid and discrete event systems. Application areas include automotive and aerospace control systems, network control, biological systems, multiagent and cooperative control, robotics, reinforcement learning, sensor networks, control of cyber-physical and energy-related systems, and control of computing systems."
"""

def get_category_mappings() -> dict[str,str]:
    """Parse the category mappings"""
    import io
    import csv
    string_file = io.StringIO(CATEGORY_DATA)
    csv_reader = csv.reader(string_file)
    result = {}
    for row in csv_reader:
        assert len(row)>=2, f"Bad row:{row}"
        category_code = row[0]
        category_name = row[1]
        result[category_code] = category_name
    return result

def map_category(category_code:str, mappings:dict[str,str]) -> str:
    return mappings[category_code] if category_code in mappings else category_code


def get_paper_metadata(arxiv_id: str, file_locations:Optional[str]=None) -> PaperMetadata:
    """Retrieve paper metadata from arXiv without downloading the PDF.

    Parameters
    ----------
    arxiv_id : str
        The arXiv paper identifier (e.g., '2503.22738v1' or '2503.22738')
    file_locations: Optional[str]
        File location object used to obtain path for metadata cache directory.
        If not provided, defaults to file_locations.FILE_LOCATIONS, which is set
        based on the DOC_HOME environment variable.

    Returns
    -------
    PaperMetadata
        Paper metadata containing the following fields:
        - paper_id : str
            The arXiv paper identifier
        - title : str
            The paper title
        - published : datetime.datetime
            The publication date
        - updated : Optional[datetime.datetime]
            The last update date, if available
        - paper_abs_url : str
            URL to the paper's abstract page
        - paper_pdf_url : str
            URL to the paper's PDF
        - authors : list[str]
            List of author names
        - abstract : Optional[str]
            The paper's abstract text
        - categories : list[str]
            List of all arXiv categories the paper belongs to, with the primary first
        - doi: Optional[str]
            A URL for the resolved DOI to an external resource if present.
        - journal_ref: Optional[str]
            A journal reference if present.

    Raises
    ------
    Exception
        If no PDF URL is found for the specified paper ID
    """
    if file_locations is None:
        from .file_locations import FILE_LOCATIONS
        file_locations = FILE_LOCATIONS

    # Check for cached metadata first
    file_locations.ensure_paper_metadata_dir()
    cache_file = join(file_locations.paper_metadata_dir, f"{arxiv_id}.json")

    if exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            return PaperMetadata.model_validate(cached_data)
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Failed to load cached metadata for {arxiv_id}: {e}")
            # Continue to fetch from arXiv if cache is corrupted

    # Fetch from arXiv API
    client = arxiv.Client()
    search_by_id = arxiv.Search(id_list=[arxiv_id])
    result = next(client.results(search_by_id))
    paper_id = result.get_short_id()
    if result.pdf_url is None:
        raise Exception(f"No pdf url found for paper {arxiv_id}")

    mappings = get_category_mappings()
    primary: str = map_category(result.primary_category, mappings)
    other_categories: list[str] = [map_category(c, mappings) for c in result.categories
                                  if c != result.primary_category]
    all_categories = [primary] + other_categories

    metadata = PaperMetadata(
        paper_id=arxiv_id,
        title=result.title,
        published=result.published,
        updated=result.updated,
        paper_abs_url=result.entry_id,
        paper_pdf_url=result.pdf_url,
        authors=[a.name for a in result.authors],
        abstract=result.summary,
        categories=all_categories,
        doi=result.doi,
        journal_ref=result.journal_ref,
    )

    # Cache the metadata
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(metadata.model_dump(), f, indent=2, default=str)
    except (OSError, IOError) as e:
        logging.warning(f"Failed to cache metadata for {arxiv_id}: {e}")

    return metadata


def download_paper(paper_metadata: PaperMetadata, file_locations=None) -> str:
    """Download a paper's PDF to the local filesystem given its metadata.
    
    Parameters
    ----------
    paper_metadata : PaperMetadata
        The paper metadata containing download information
    file_locations : FileLocations, optional
        The file locations to use. If None, uses the global FILE_LOCATIONS.
        
    Returns
    -------
    str
        The local path where the PDF was downloaded
        
    Raises
    ------
    Exception
        If the PDF cannot be downloaded
    """
    if file_locations is None:
        from .file_locations import FILE_LOCATIONS
        file_locations = FILE_LOCATIONS
        
    client = arxiv.Client()
    search_by_id = arxiv.Search(id_list=[paper_metadata.paper_id])
    result = next(client.results(search_by_id))
    
    local_pdf_path = paper_metadata.get_local_pdf_path(file_locations)
    
    if not exists(local_pdf_path):
        file_locations.ensure_pdfs_dir()
        result.download_pdf(dirpath=file_locations.pdfs_dir, filename=basename(local_pdf_path))
        assert exists(local_pdf_path)
        logging.info(f"Downloaded '{paper_metadata.title}' to {local_pdf_path}")
    else:
        logging.info(f"PDF file for '{paper_metadata.title}' already exists at {local_pdf_path}")
    
    return local_pdf_path


def _deduplicate_arxiv_ids(arxiv_ids: list[str]) -> list[str]:
    """
    Deduplicate arXiv IDs by choosing the latest version when multiple versions exist.

    When multiple versions of the same paper are found (e.g., '2107.03374', '2107.03374v1',
    '2107.03374v2'), this function keeps only the latest version. IDs without a version
    number are treated as v0 (earliest version).

    Parameters
    ----------
    arxiv_ids : list[str]
        List of arXiv paper IDs, potentially with duplicates and multiple versions

    Returns
    -------
    list[str]
        Deduplicated list of arXiv IDs, containing only the latest version of each paper

    Examples
    --------
    >>> _deduplicate_arxiv_ids(['2107.03374', '2107.03374v1', '2107.03374v2'])
    ['2107.03374v2']

    >>> _deduplicate_arxiv_ids(['2308.03873', '2308.03873', '2412.19437v1'])
    ['2308.03873', '2412.19437v1']
    """
    if not arxiv_ids:
        return []

    # Pattern to extract base ID and version number
    # Modern IDs: YYMM.NNNNN or YYMM.NNNNNvN
    # Legacy IDs: archive-name/YYMMNNN (no version support)
    version_pattern = re.compile(r'^(.+?)(?:v(\d+))?$')

    # Group IDs by base ID
    id_groups: dict[str, list[tuple[str, int]]] = {}

    for arxiv_id in arxiv_ids:
        match = version_pattern.match(arxiv_id)
        if match:
            base_id = match.group(1)
            version_str = match.group(2)
            version_num = int(version_str) if version_str else 0

            if base_id not in id_groups:
                id_groups[base_id] = []
            id_groups[base_id].append((arxiv_id, version_num))

    # For each group, keep only the ID with the highest version number
    deduplicated = []
    for base_id, versions in id_groups.items():
        # Sort by version number (highest first), then by full ID for stability
        versions.sort(key=lambda x: (-x[1], x[0]))
        latest_id = versions[0][0]
        deduplicated.append(latest_id)

    return deduplicated


def _google_search_arxiv_papers(query: str) -> list[PaperMetadata]:
    """
    Search for papers using Google Custom Search + ArXiv API.

    This function performs a Google Custom Search to find ArXiv papers, deduplicates
    the results (choosing the latest version when multiple versions exist), and
    fetches full metadata from the ArXiv API.

    Parameters
    ----------
    query : str
        User's search query

    Returns
    -------
    list[PaperMetadata]
        Papers found via Google search (up to 10), with full metadata from ArXiv API

    Raises
    ------
    Exception
        If Google search fails or if all ArXiv API metadata fetches fail
    """
    from .google_search import google_search_arxiv

    # Call Google search to get up to 10 paper IDs
    paper_ids = google_search_arxiv(query, k=10)

    # Return early if no results
    if not paper_ids:
        return []

    # Deduplicate by choosing latest version
    deduplicated_ids = _deduplicate_arxiv_ids(paper_ids)

    # Fetch metadata for each deduplicated ID
    papers = []
    failed_ids = []

    for paper_id in deduplicated_ids:
        try:
            metadata = get_paper_metadata(paper_id)
            papers.append(metadata)
        except Exception as e:
            logging.warning(f"Failed to fetch metadata for {paper_id}: {e}")
            failed_ids.append(paper_id)

    # If all metadata fetches failed, raise exception
    if not papers and deduplicated_ids:
        raise Exception(
            f"Failed to fetch metadata for any papers. "
            f"Attempted IDs: {deduplicated_ids}, all failed."
        )

    return papers


def _arxiv_keyword_search(query:str, max_results:int) -> list[PaperMetadata]:
    """Find all matching papers up to the limit using the arxiv Search APIs.
    """
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results)
    metadata_results = []
    mappings = get_category_mappings()
    for result in client.results(search):
        paper_id = result.get_short_id()
        if result.pdf_url is None:
            raise Exception(f"No pdf url found for paper {paper_id}")
        primary: str = map_category(result.primary_category, mappings)
        other_categories: list[str] = [map_category(c, mappings) for c in result.categories
                                      if c != result.primary_category]
        all_categories = [primary] + other_categories

        metadata_results.append(PaperMetadata(
            paper_id=paper_id,
            title=result.title,
            published=result.published,
            updated=result.updated,
            paper_abs_url=result.entry_id,
            paper_pdf_url=result.pdf_url,
            authors=[a.name for a in result.authors],
            abstract=result.summary,
            categories=all_categories,
            doi=result.doi,
            journal_ref=result.journal_ref,
        ))
    return metadata_results


def search_arxiv_papers(query:str, k:int=1, candidate_limit:int=50) -> list[PaperMetadata]:
    """Search for papers using Google Custom Search (if configured) or ArXiv API (fallback).

    Then, rerank by computing embeddings for each of the search results and compare to the embedding of the original query
    string, using the LlamaIndex APIs. Return the paper metadata for the k closest matches, sorted by paper ID.

    Parameters
    ----------
    query: str
        Search text for finding papers. This can match to the title, paper id, abstract, authors, etc.
    k: int
        Maximum number of matches to return after reranking. Defaults to 1.
    candidate_limit: int
        Maximum number of candiate papers to return from the initial keyword search on Arxiv (ArXiv API only).

    Returns
    -------
    list[PaperMetadata]
        Metadata for the k closest matches, sorted by paper ID (ascending).
    """
    # Check if Google Custom Search is configured
    from . import google_search
    google_search_available = (
        google_search.API_KEY is not None and google_search.API_KEY != "" and
        google_search.SEARCH_ENGINE_ID is not None and google_search.SEARCH_ENGINE_ID != ""
    )

    if google_search_available:
        logging.debug("Using Google Custom Search...")
        candidates = _google_search_arxiv_papers(query)
    else:
        logging.debug("Google Custom Search not configured, using ArXiv API search...")
        candidates = _arxiv_keyword_search(query, max_results=candidate_limit)
    
    # If we have fewer candidates than requested, sort by paper ID and return all of them
    if len(candidates) <= k:
        # Sort by paper ID (ascending)
        return sorted(candidates, key=lambda p: p.paper_id)
    
    try:
        # Try to use LlamaIndex embeddings for semantic similarity
        from llama_index.core.embeddings import BaseEmbedding
        from llama_index.core.settings import Settings
        import numpy as np
        
        # Get the default embedding model from LlamaIndex settings
        embed_model = Settings.embed_model
        
        # Create embeddings for the query
        query_embedding = embed_model.get_text_embedding(query)
        
        # Create embeddings for each candidate paper
        # We'll embed the combination of title and abstract for better semantic matching
        candidate_embeddings = []
        for candidate in candidates:
            # Combine title and abstract for richer semantic representation
            text_to_embed = f"{candidate.title}"
            if candidate.abstract:
                text_to_embed += f" {candidate.abstract}"
            
            paper_embedding = embed_model.get_text_embedding(text_to_embed)
            candidate_embeddings.append(paper_embedding)
        
        # Compute cosine similarities between query and candidate embeddings
        similarities = []
        query_embedding_np = np.array(query_embedding)
        
        for paper_embedding in candidate_embeddings:
            paper_embedding_np = np.array(paper_embedding)
            
            # Compute cosine similarity
            dot_product = np.dot(query_embedding_np, paper_embedding_np)
            norm_query = np.linalg.norm(query_embedding_np)
            norm_paper = np.linalg.norm(paper_embedding_np)
            cosine_similarity = dot_product / (norm_query * norm_paper)
            similarities.append(cosine_similarity)
        
        # Sort candidates by similarity (highest first) and take top k
        similarity_indices = np.argsort(similarities)[::-1]  # Sort in descending order
        top_k_indices = similarity_indices[:k]

        # Get the top k candidates based on similarity scores
        reranked_candidates = [candidates[i] for i in top_k_indices]

        # Sort by paper ID (ascending) for consistent ordering
        return sorted(reranked_candidates, key=lambda p: p.paper_id)
        
    except Exception as e:
        # Fallback to simple text-based similarity if embeddings fail
        # (e.g., when OpenAI API key is not available)
        logging.warning(f"Embedding-based reranking failed ({e}), falling back to text-based similarity")
        
        # Simple text-based similarity using title and abstract keywords
        def text_similarity(text1: str, text2: str) -> float:
            """Compute simple text similarity based on shared words."""
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return 0.0
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union)  # Jaccard similarity
        
        # Compute text similarity scores
        similarities = []
        query_lower = query.lower()
        
        for candidate in candidates:
            # Combine title and abstract for comparison
            candidate_text = f"{candidate.title}"
            if candidate.abstract:
                candidate_text += f" {candidate.abstract}"
            
            similarity = text_similarity(query_lower, candidate_text.lower())
            similarities.append(similarity)
        
        # Sort candidates by similarity (highest first) and take top k
        similarity_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)
        top_k_indices = similarity_indices[:k]

        # Get the top k candidates based on similarity scores
        reranked_candidates = [candidates[i] for i in top_k_indices]

        # Sort by paper ID (ascending) for consistent ordering
        return sorted(reranked_candidates, key=lambda p: p.paper_id)
    
def get_downloaded_paper_ids(file_locations:FileLocations=FILE_LOCATIONS) -> list[str]:
    """Return the list of paper ids for papers whose pdfs have been downloaded"""
    return [filename[:-len('.pdf')]
            for filename in os.listdir(file_locations.pdfs_dir)
            if filename.endswith('.pdf')]



    
