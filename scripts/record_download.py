#!/usr/bin/env python3
"""
Helper script to record annual report download paths using Playwright.

Usage:
    python scripts/record_download.py [company_id] [year]
    
Example:
    python scripts/record_download.py S1 2024
    
This will:
1. Look up the company's IR URL from coverage table
2. Launch Playwright codegen recorder
3. Open a browser for you to demonstrate the download
4. Save the recorded script to: aspiratio/utils/playwright_scripts/{company_id}_{year}.py
"""

import sys
import os
import subprocess
import pandas as pd

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/record_download.py [company_id] [year]")
        print("\nExamples:")
        print("  python scripts/record_download.py S1 2024")
        print("  python scripts/record_download.py S18 2023")
        print("\nAvailable companies:")
        
        # Show available companies
        coverage_path = 'coverage_table_updated.csv'
        if os.path.exists(coverage_path):
            df = pd.read_csv(coverage_path, sep='\t')
            incomplete = df[df['Priority'] != 'Complete ✓']
            
            for _, row in incomplete.head(20).iterrows():
                print(f"  {row['Company_Identifier']:6s} - {row['CompanyName']:30s} - Year {row['FiscalYear']}")
            
            if len(incomplete) > 20:
                print(f"  ... and {len(incomplete) - 20} more")
        
        sys.exit(1)
    
    company_id = sys.argv[1]
    year = int(sys.argv[2])
    
    # Load coverage table
    coverage_path = 'coverage_table_updated.csv'
    if not os.path.exists(coverage_path):
        print(f"Error: {coverage_path} not found")
        sys.exit(1)
    
    df = pd.read_csv(coverage_path, sep='\t')
    
    # Find the company and year
    match = df[(df['Company_Identifier'] == company_id) & (df['FiscalYear'] == year)]
    
    if match.empty:
        print(f"Error: No entry found for {company_id} - {year}")
        print("\nTip: Check available companies with: python scripts/record_download.py")
        sys.exit(1)
    
    row = match.iloc[0]
    company_name = row['CompanyName']
    ir_url = row['IR_URL']
    
    print(f"Recording download path for:")
    print(f"  Company: {company_name}")
    print(f"  ID: {company_id}")
    print(f"  Year: {year}")
    print(f"  IR URL: {ir_url}")
    print()
    
    # Create output directory
    output_dir = 'aspiratio/utils/playwright_scripts'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/{company_id}_{year}.py"
    
    print(f"Output will be saved to: {output_file}")
    print()
    print("=" * 60)
    print("INSTRUCTIONS:")
    print("=" * 60)
    print("1. A browser window will open with Playwright Inspector")
    print("2. Navigate to find the annual report for the selected year")
    print("3. Click on the download link or view the PDF")
    print("4. Close the browser when done")
    print("5. The script will be automatically saved")
    print()
    print("Launching Playwright recorder...")
    print("=" * 60)
    
    # Launch playwright codegen
    cmd = [
        'playwright', 'codegen',
        '--target', 'python-async',
        '--output', output_file,
        ir_url
    ]
    
    try:
        result = subprocess.run(cmd)
        
        if result.returncode == 0 and os.path.exists(output_file):
            # Check if file has content
            with open(output_file, 'r') as f:
                content = f.read()
            
            if len(content) > 100:
                print()
                print("=" * 60)
                print(f"✓ Recording saved successfully!")
                print(f"  Location: {output_file}")
                print(f"  Size: {len(content)} characters")
                print()
                print("Next steps:")
                print(f"  1. Review: cat {output_file}")
                print(f"  2. Share the script content so I can analyze it")
                print(f"  3. I'll help integrate it into the download system")
            else:
                print()
                print("Warning: Script file is empty or very short.")
                print("Make sure you performed some actions before closing the browser.")
        else:
            print()
            print("Recording was cancelled or failed.")
    
    except KeyboardInterrupt:
        print()
        print("Recording cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
