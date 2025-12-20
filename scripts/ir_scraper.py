
"""
Script to search for investor relations URLs for each company and update the master CSV.
"""
import sys
import os
# Ensure repo root is in sys.path for aspiratio imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
import pandas as pd
from aspiratio.utils.ir_search import search_ir_url, validate_ir_url
from aspiratio.utils.io import read_tsv, write_tsv

def main():
    import sys
    import time
    import os
    # Simple CLI: use validated master as input, output to new file
    master_path = 'instrument_master_validated.csv'
    out_path = 'instrument_master_ir.csv'
    rate = 0.1  # seconds between requests
    # Load master
    master_df = read_tsv(master_path)
    # For each company, search and validate IR URL
    ir_urls = []
    for idx, row in master_df.iterrows():
        name = row.iloc[0]
        print(f"Searching IR URL for: {name}")
        url = search_ir_url(name)
        if url and validate_ir_url(url):
            ir_urls.append(url)
        else:
            ir_urls.append('')
        time.sleep(rate)
    # Update DataFrame
    master_df['investor_relations_url'] = ir_urls
    write_tsv(master_df, out_path)
    print(f"IR URLs written to {out_path}")

if __name__ == "__main__":
    main()
