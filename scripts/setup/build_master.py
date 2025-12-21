
"""
Script to build and validate the instrument master from omxs30_members.csv.
Matches by company name, raises error on mismatch.
"""
import sys
import os
# Ensure repo root is in sys.path for aspiratio imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
import pandas as pd
from aspiratio.utils.name_match import normalize_name, match_rows
from aspiratio.utils.io import read_tsv, write_tsv

def main():
    import sys
    import os
    # Ensure repo root is in sys.path for aspiratio imports
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    omx_path = os.path.join(repo_root, 'omxs30_members.csv')
    master_path = os.path.join(repo_root, 'instrument_master.csv')
    # Load CSVs
    omx_df = read_tsv(omx_path)
    master_df = read_tsv(master_path)
    # Get company names
    omx_names = omx_df.iloc[:, 0].tolist()  # Assume first column is name
    master_names = master_df.iloc[:, 0].tolist()  # Assume first column is name
    # Match
    matches, mismatches = match_rows(omx_names, master_names)
    if mismatches:
        print(f"Error: The following OMXS30 members are missing in instrument master:\n{mismatches}")
        sys.exit(1)
    print(f"All OMXS30 members matched in instrument master. Total: {len(matches)}")
    # Optionally, write validated master (no changes yet)
    out_path = 'instrument_master_validated.csv'
    write_tsv(master_df, out_path)
    print(f"Validated master written to {out_path}")

if __name__ == "__main__":
    main()
