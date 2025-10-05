"""Define common types used across steps/tools.
"""

from typing import Optional
import datetime
from os.path import join
from pydantic import BaseModel, Field

class PaperMetadata(BaseModel):
    paper_id: str = Field(description="The arXiv paper identifier")
    title: str = Field(description="The paper title")
    published: datetime.datetime = Field(description="The publication date")
    updated: Optional[datetime.datetime] = Field(description="The last update date, if available")
    paper_abs_url: str = Field(description="URL to the paper's abstract page")
    paper_pdf_url: str = Field(description="URL to the paper's PDF")
    authors: list[str] = Field(description="List of author names")
    abstract: Optional[str] = Field(description="The paper's abstract text")
    categories: list[str] = Field(description="List of all arXiv categories the paper belongs to, with the primary first")
    doi: Optional[str] = Field(description="A URL for the resolved DOI to an external resource if present")
    journal_ref: Optional[str] = Field(description="A journal reference if present")
    
    def get_local_pdf_path(self, file_locations) -> str:
        """Get the local PDF path for this paper given file locations.
        
        Parameters
        ----------
        file_locations : FileLocations
            The file locations configuration
            
        Returns
        -------
        str
            The local path where the PDF should be stored
        """
        return join(file_locations.pdfs_dir, self.paper_id + '.pdf')
    
class SearchResult(BaseModel):
    """Results from a semantic search of the index."""
    paper_id: str = Field(description="id of the paper containing this chunk")
    pdf_filename: str = Field(description="name of pdf file containing paper")
    summary_filename: Optional[str] = Field(description="Filename of the summary, if present")
    paper_title: str = Field(description="Title of the paper")
    page: int = Field(description="Page number of chunk")
    chunk: str = Field(description="Chunk of text from paper")

    def get_local_pdf_path(self, file_locations) -> str:
        return join(file_locations.pdfs_dir, self.pdf_filename)
    
    def get_summary_path(self, file_locations) -> Optional[str]:
        if self.summary_filename is not None:
            return join(file_locations.summaries_dir, self.summary_filename)
        else:
            return None
    


