"""Test ABB download specifically."""
from aspiratio.utils.report_downloader import download_company_reports

print(f"\n{'='*60}")
print(f"Testing: ABB")
print(f"{'='*60}\n")

result = download_company_reports(
    cid='S1',
    company_name='ABB Ltd',
    ir_url='https://global.abb/group/en/investors/annual-reporting-suite#download',
    years=[2019, 2020, 2021, 2022, 2023, 2024],
    output_dir='companies'
)

print(f"\n{'='*60}")
print(f"Summary for ABB:")
print(f"{'='*60}")
for year in sorted(result['details'].keys(), reverse=True):
    details = result['details'][year]
    status_symbol = {'downloaded': '✓', 'error': '✗', 'not_found': '?', 'exists': '⊙'}. get(details['status'], '·')
    print(f"{status_symbol} {year}: {details['status']}")
    if details['status'] == 'downloaded':
        print(f"    {details.get('pages', 'N/A')} pages, {details.get('size_mb', 0):.1f} MB - {details.get('title', '')[:60]}")
    elif details['status'] == 'error':
        print(f"    {details.get('error', 'Unknown')[:80]}")
