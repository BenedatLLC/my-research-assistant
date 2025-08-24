"""Locations of the various data we are storing
"""

import os
from os.path import isdir, abspath, expanduser, join
from typing import NamedTuple, Optional

class ConfigError(Exception):
    pass


class FileLocations(NamedTuple):
    doc_home: str
    index_dir: str
    summaries_dir: str
    images_dir: str
    pdfs_dir: str
    extracted_paper_text_dir: str

    def ensure_index_dir(self):
        if not isdir(self.index_dir):
            os.mkdir(self.index_dir)

    def ensure_summaries_dir(self):
        if not isdir(self.summaries_dir):
            os.mkdir(self.summaries_dir)

    def ensure_pdfs_dir(self):
        if not isdir(self.pdfs_dir):
            os.mkdir(self.pdfs_dir)

    def ensure_images_dir(self):
        if not isdir(self.images_dir):
            self.ensure_summaries_dir() # a child under the summaries
            os.mkdir(self.images_dir)

    def ensure_extracted_paper_text_dir(self):
        if not isdir(self.extracted_paper_text_dir):
            os.mkdir(self.extracted_paper_text_dir)

    @staticmethod
    def get_locations(doc_home:Optional[str]=None) -> 'FileLocations':
        """Get the file locations either from the specified location or
        from the DOC_HOME environment variable. Either way, that directory
        must exist, but the children do not have to exist."""
        if doc_home is not None:
            use_doc_home = doc_home
        elif 'DOC_HOME' in os.environ:
            use_doc_home = os.environ['DOC_HOME']
        else:
            raise ConfigError("Need to set the envronment variable DOC_HOME.")
        use_doc_home = abspath(expanduser(use_doc_home))
        if not isdir(use_doc_home):
            raise ConfigError(f"DOC_HOME path {use_doc_home} does not exist or is not a directory")
        summaries_dir = join(use_doc_home, 'summaries')
        return FileLocations(
            doc_home=use_doc_home,
            index_dir=join(use_doc_home, 'index'),
            summaries_dir=summaries_dir,
            images_dir=join(summaries_dir, 'images'),
            pdfs_dir=join(use_doc_home, 'pdfs'),
            extracted_paper_text_dir=join(use_doc_home, 'extracted_paper_text')
        )


FILE_LOCATIONS=FileLocations.get_locations()

