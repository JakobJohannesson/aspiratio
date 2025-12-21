# Utils init - Compatibility layer
# Re-exports from tier-based structure for backward compatibility

# Tier 1: Traditional scraping
from aspiratio.tier1 import report_downloader, ir_search

# Tier 2: Playwright/JavaScript
from aspiratio.tier2 import playwright_downloader

# Common utilities
from aspiratio.common import io, name_match
