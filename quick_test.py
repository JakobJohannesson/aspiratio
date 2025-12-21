"""
Quick test: Download reports for 2-3 validated companies only.
"""
import sys
import os

repo_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, repo_root)

from aspiratio.utils.io import read_tsv
from aspiratio.utils.report_downloader import download_company_reports

def main():
    master_path = os.path.join(repo_root, 'instrument_master.csv')
    df = read_tsv(master_path)
    
    # Filter for validated companies
    if 'validated' in df.columns:
        df['validated'] = df['validated'].fillna(False).astype(bool)
        valid_df = df[df['validated'] == True].copy()
    else:
        valid_df = df[df['investor_relations_url'].notna()].copy()
    
    # Test with just first 2 companies
    test_df = valid_df.head(2)
    
    print(f"Testing with {len(test_df)} companies:\n")
    
    for idx, row in test_df.iterrows():
        print(f"  - {row['CompanyName']} ({row['CID']}): {row['investor_relations_url']}")
    
    print("\n" + "="*60 + "\n")
    
    years = [2023, 2024]  # Just recent years for testing
    
    for idx, row in test_df.iterrows():
        result = download_company_reports(
            cid=row['CID'],
            company_name=row['CompanyName'],
            ir_url=row['investor_relations_url'],
            years=years,
            output_dir=os.path.join(repo_root, 'companies')
        )
        print()

if __name__ == "__main__":
    main()
