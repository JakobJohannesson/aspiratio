
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
    master_path = 'instrument_master.csv'
    out_path = 'instrument_master.csv'
    rate = 0.1  # seconds between requests
    # Load master
    master_df = read_tsv(master_path)
    # Only search for companies that are not validated
    ir_urls = master_df['investor_relations_url'].tolist()
    for idx, row in master_df.iterrows():
        name = row.iloc[0]
        ccy = row['CCY'] if 'CCY' in row else ''
        is_validated = row['validated'] if 'validated' in row else False
        # Handle NaN or empty strings which are truthy but should be False
        if pd.isna(is_validated) or is_validated == '' or is_validated is False:
            is_validated = False
        else:
            is_validated = bool(is_validated)
        
        if is_validated:
            continue

        search_name = name
        if ccy == 'SEK':
            import re
            # Remove existing share class if present to avoid "Investor B AB"
            clean_name = re.sub(r'\s+[abc]$', '', name, flags=re.IGNORECASE)
            search_name = f"{clean_name} AB"

        print(f"Searching IR URL for: {search_name}")
        url = search_ir_url(search_name)
        if url and validate_ir_url(url):
            ir_urls[idx] = url
        else:
            ir_urls[idx] = ''
        time.sleep(rate)
    # Update DataFrame
    master_df['investor_relations_url'] = ir_urls
    write_tsv(master_df, out_path)
    print(f"IR URLs written to {out_path}")

if __name__ == "__main__":
    main()
