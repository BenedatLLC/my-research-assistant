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
    default_pdf_filename: str = Field(description="The default filename for the PDF, will be used by get_local_pdf_path()")
    
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
        return join(file_locations.pdfs_dir, self.default_pdf_filename)
