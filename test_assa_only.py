"""Test ASSA ABLOY download with direct URL pattern."""
from aspiratio.utils.report_downloader import download_company_reports

print(f"\n{'='*60}")
print(f"Testing: ASSA ABLOY")
print(f"{'='*60}\n")

result = download_company_reports(
    cid='S1',
    company_name='ASSA ABLOY',
    ir_url='https://www.assaabloy.com/group/en/investors/reports-presentations/annual-reports',
    years=[2019, 2020, 2021, 2022, 2023, 2024],
    output_dir='companies'
)

print(f"\n{'='*60}")
print(f"Results for ASSA ABLOY:")
print(f"{'='*60}")
print(f"Milestones: {result['milestones']}")
print(f"Downloaded: {result['downloaded']}")
print(f"Not Found: {result['not_found']}")
print(f"Errors: {result['errors']}")
print(f"\nDetails:")
for year in sorted(result['details'].keys(), reverse=True):
    details = result['details'][year]
    print(f"  {year}: {details['status']}")
    if details['status'] == 'downloaded':
        print(f"    - {details.get('pages', 'N/A')} pages, {details.get('size_mb', 'N/A'):.2f} MB")
        print(f"    - {details.get('title', 'N/A')}")
    elif details['status'] == 'error':
        print(f"    - Error: {details.get('error', 'Unknown')}")
