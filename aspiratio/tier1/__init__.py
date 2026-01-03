"""Tier 1: Traditional web scraping and IR search."""
from . import report_downloader
from . import wget_search

# ir_search requires ddgs which may not be installed
try:
    from . import ir_search
    __all__ = ['report_downloader', 'ir_search', 'wget_search']
except ImportError:
    __all__ = ['report_downloader', 'wget_search']
