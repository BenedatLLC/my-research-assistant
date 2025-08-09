"""Define common types used across steps/tools.
"""

from typing import Optional
import datetime
from os.path import join
from pydantic import BaseModel

class PaperMetadata(BaseModel):
    paper_id: str
    title: str
    published: datetime.datetime
    updated: Optional[datetime.datetime]
    paper_abs_url: str
    paper_pdf_url: str
    authors : list[str]
    abstract: Optional[str]
    categories: list[str]
    doi: Optional[str]
    journal_ref: Optional[str]
    default_pdf_filename: str
    
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
