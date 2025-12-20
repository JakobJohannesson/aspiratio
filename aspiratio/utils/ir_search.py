"""
Helpers for searching and validating investor relations URLs.
"""
def search_ir_url(company_name: str):
    """Search DuckDuckGo for investor relations page URL for a company using ddgs. Returns the top result URL or empty string."""
    from ddgs import DDGS
    query = f"{company_name} investor relations"
    print(f"Searching for IR URL with query: {query}")
    with DDGS() as ddgs:
        for r in ddgs.text(query):
            url = r.get('href') or r.get('url')
            if url:
                print(f"Top result URL: {url}")
                return url
    return ''

def validate_ir_url(url: str) -> bool:
    """Return True if URL contains investor relations keywords."""
    import re
    keywords = [r"investor", r"ir", r"investerare"]
    url_lc = url.lower()
    for kw in keywords:
        if re.search(kw, url_lc):
            return True
    return False
