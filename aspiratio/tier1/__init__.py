"""Tier 1: Traditional web scraping and IR search."""
from . import report_downloader
from . import mfn_search

# ir_search requires ddgs which may not be installed
try:
    from . import ir_search
    __all__ = ['report_downloader', 'ir_search', 'mfn_search']
except ImportError:
    __all__ = ['report_downloader', 'mfn_search']
