"""
Utility functions for normalizing and matching company names.
"""
def normalize_name(name: str) -> str:
    """Normalize company name for matching (lowercase, strip punctuation, etc)."""
    import re
    # Lowercase, remove punctuation, replace & with 'and', collapse whitespace
    name = name.lower()
    name = name.replace('&', 'and')
    name = re.sub(r'[^a-z0-9 ]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def match_rows(omx_names, master_names):
    """Match OMXS30 names to instrument master names, return mapping and mismatches."""
    """
    Returns: (matches, mismatches)
    matches: list of (omx_name, master_name)
    mismatches: list of omx_name not found in master_names
    """
    norm_master = {normalize_name(n): n for n in master_names}
    matches = []
    mismatches = []
    for omx in omx_names:
        norm = normalize_name(omx)
        if norm in norm_master:
            matches.append((omx, norm_master[norm]))
        else:
            mismatches.append(omx)
    return matches, mismatches
