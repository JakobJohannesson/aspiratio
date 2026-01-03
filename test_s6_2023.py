#!/usr/bin/env python3
"""Test script for Atlas Copco 2023 download"""
import asyncio
from aspiratio.tier2.playwright_downloader import download_atlas_copco_report
from pathlib import Path

async def main():
    output_dir = Path('companies/S6')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Testing Atlas Copco 2023 download...")
    result = await download_atlas_copco_report(2023, output_dir)
    print(f'\nResult: {result}')
    
    if result['success']:
        # Check file exists
        if result['path']:
            file_path = Path(result['path'])
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"✓ File downloaded: {file_path}")
                print(f"✓ Size: {size_mb:.2f} MB")
            else:
                print(f"✗ File not found: {file_path}")
    else:
        print(f"✗ Download failed: {result['error']}")

if __name__ == '__main__':
    asyncio.run(main())
