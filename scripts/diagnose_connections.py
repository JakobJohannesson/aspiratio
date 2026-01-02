#!/usr/bin/env python3
"""
Diagnostic tool to test website connections and identify specific issues.
Helps identify which websites have DNS errors, timeouts, or HTTP blocking.
"""

import sys
import time
import requests
from urllib.parse import urlparse
import pandas as pd

# Import user agents from config
try:
    from aspiratio.config import get_user_agents
    USER_AGENTS = get_user_agents()
except (ImportError, ModuleNotFoundError):
    # Fallback if config not available
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

# Import connection error utilities
try:
    from aspiratio.common.connection_errors import categorize_connection_error, format_error_message
except (ImportError, ModuleNotFoundError):
    # Fallback if not available (shouldn't happen but just in case)
    categorize_connection_error = None
    format_error_message = None


def test_connection(url, user_agent=None, timeout=15):
    """
    Test connection to a URL and categorize the error type.
    
    Returns:
        dict: {
            'success': bool,
            'status_code': int or None,
            'error_type': str or None,  # 'dns', 'timeout', 'http_error', 'ssl', 'connection', None
            'error_message': str or None,
            'response_time': float or None (in seconds)
        }
    """
    result = {
        'success': False,
        'status_code': None,
        'error_type': None,
        'error_message': None,
        'response_time': None,
        'user_agent': user_agent[:50] if user_agent else None
    }
    
    if user_agent is None:
        user_agent = USER_AGENTS[0]
    
    headers = {'User-Agent': user_agent}
    start_time = time.time()
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        result['response_time'] = time.time() - start_time
        result['status_code'] = response.status_code
        
        if response.status_code == 200:
            result['success'] = True
        elif response.status_code == 403:
            result['error_type'] = 'http_403_blocked'
            result['error_message'] = 'HTTP 403 Forbidden - likely blocking requests'
        elif response.status_code == 404:
            result['error_type'] = 'http_404_not_found'
            result['error_message'] = 'HTTP 404 Not Found'
        else:
            result['error_type'] = 'http_error'
            result['error_message'] = f'HTTP {response.status_code}'
    
    except (requests.exceptions.Timeout, requests.exceptions.SSLError,
            requests.exceptions.ConnectionError) as e:
        result['response_time'] = time.time() - start_time
        
        # Use shared utility if available, otherwise fall back to inline logic
        if categorize_connection_error:
            error_type, error_msg, emoji = categorize_connection_error(e)
            result['error_type'] = error_type
            result['error_message'] = error_msg
        else:
            # Fallback implementation
            if isinstance(e, requests.exceptions.Timeout):
                result['error_type'] = 'timeout'
                result['error_message'] = f'Connection timed out after {timeout}s'
            elif isinstance(e, requests.exceptions.SSLError):
                result['error_type'] = 'ssl_error'
                result['error_message'] = f'SSL/TLS error: {str(e)[:100]}'
            else:  # ConnectionError
                error_str = str(e)
                if 'NameResolutionError' in error_str or 'Failed to resolve' in error_str:
                    result['error_type'] = 'dns_error'
                    result['error_message'] = 'DNS resolution failed - domain may be blocked or unreachable'
                elif 'Connection refused' in error_str:
                    result['error_type'] = 'connection_refused'
                    result['error_message'] = 'Connection refused by server'
                else:
                    result['error_type'] = 'connection_error'
                    result['error_message'] = f'Connection error: {error_str[:100]}'
    
    except Exception as e:
        result['response_time'] = time.time() - start_time
        result['error_type'] = 'unknown_error'
        result['error_message'] = f'{type(e).__name__}: {str(e)[:100]}'
    
    return result


def test_url_with_multiple_agents(url, timeout=15):
    """
    Test URL with multiple user agents to see if any succeed.
    
    Returns:
        dict: {
            'url': str,
            'domain': str,
            'best_result': dict,  # The best result from all attempts
            'all_results': list,  # All results from different user agents
            'recommendation': str  # What to do about this URL
        }
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    
    all_results = []
    successful_result = None
    
    print(f"\nTesting: {url}")
    print(f"Domain: {domain}")
    print("-" * 60)
    
    for i, user_agent in enumerate(USER_AGENTS, 1):
        print(f"  Attempt {i}/{len(USER_AGENTS)}: {user_agent[:50]}...")
        result = test_connection(url, user_agent, timeout)
        all_results.append(result)
        
        if result['success']:
            print(f"    ✓ Success! Status: {result['status_code']}, Time: {result['response_time']:.2f}s")
            successful_result = result
            break
        else:
            print(f"    ✗ Failed: {result['error_type']} - {result['error_message']}")
        
        time.sleep(0.5)  # Brief pause between attempts
    
    # Determine the best result and recommendation
    best_result = successful_result if successful_result else all_results[0]
    
    recommendation = ""
    if successful_result:
        recommendation = "✓ Working - at least one user agent succeeded"
    elif all_results[0]['error_type'] == 'dns_error':
        recommendation = "⚠ DNS resolution failed - domain may be blocked in this environment"
    elif all_results[0]['error_type'] == 'timeout':
        recommendation = "⚠ Connection timeout - may need increased timeout or is unreachable"
    elif all_results[0]['error_type'] in ['http_403_blocked', 'connection_refused']:
        recommendation = "⚠ Server blocking requests - may need different approach (Playwright)"
    elif all_results[0]['error_type'] == 'http_404_not_found':
        recommendation = "⚠ URL not found - may need updated IR URL"
    else:
        recommendation = f"⚠ {all_results[0]['error_type']} - needs investigation"
    
    print(f"\nRecommendation: {recommendation}")
    
    return {
        'url': url,
        'domain': domain,
        'best_result': best_result,
        'all_results': all_results,
        'recommendation': recommendation
    }


def diagnose_companies(csv_path='instrument_master.csv'):
    """
    Test all company IR URLs from the instrument master.
    
    Returns:
        pd.DataFrame: Summary of test results
    """
    # Load instrument master
    df = pd.read_csv(csv_path, sep='\t')
    
    results = []
    total = len(df)
    
    print("="*80)
    print("WEBSITE CONNECTION DIAGNOSTICS")
    print("="*80)
    print(f"Testing {total} company IR URLs...\n")
    
    for idx, row in df.iterrows():
        cid = row['CID']
        company = row['CompanyName']
        ir_url = row['investor_relations_url']
        
        print(f"\n[{idx+1}/{total}] {cid} - {company}")
        
        if pd.isna(ir_url) or not ir_url:
            print("  ⊘ No IR URL available")
            results.append({
                'CID': cid,
                'CompanyName': company,
                'IR_URL': None,
                'Status': 'no_url',
                'Error_Type': None,
                'Recommendation': 'Need to find IR URL'
            })
            continue
        
        test_result = test_url_with_multiple_agents(ir_url, timeout=15)
        
        results.append({
            'CID': cid,
            'CompanyName': company,
            'IR_URL': ir_url,
            'Domain': test_result['domain'],
            'Status': 'success' if test_result['best_result']['success'] else 'failed',
            'Error_Type': test_result['best_result']['error_type'],
            'Error_Message': test_result['best_result']['error_message'],
            'Response_Time': test_result['best_result']['response_time'],
            'Recommendation': test_result['recommendation']
        })
        
        # Brief pause between companies
        time.sleep(1)
    
    results_df = pd.DataFrame(results)
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    success_count = len(results_df[results_df['Status'] == 'success'])
    failed_count = len(results_df[results_df['Status'] == 'failed'])
    no_url_count = len(results_df[results_df['Status'] == 'no_url'])
    
    print(f"\nTotal companies: {total}")
    print(f"  ✓ Successful: {success_count}")
    print(f"  ✗ Failed: {failed_count}")
    print(f"  ⊘ No URL: {no_url_count}")
    
    if failed_count > 0:
        print("\nFailed connections by error type:")
        error_counts = results_df[results_df['Status'] == 'failed']['Error_Type'].value_counts()
        for error_type, count in error_counts.items():
            print(f"  - {error_type}: {count}")
        
        print("\nFailed companies:")
        failed_companies = results_df[results_df['Status'] == 'failed']
        for _, row in failed_companies.iterrows():
            print(f"  {row['CID']} - {row['CompanyName']}: {row['Error_Type']}")
    
    # Save results
    output_file = 'connection_diagnostics.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\nDetailed results saved to: {output_file}")
    
    return results_df


def main():
    """Entry point for console script."""
    # Check if specific URL provided
    if len(sys.argv) > 1:
        url = sys.argv[1]
        test_url_with_multiple_agents(url)
    else:
        # Test all companies
        diagnose_companies()


if __name__ == '__main__':
    main()
