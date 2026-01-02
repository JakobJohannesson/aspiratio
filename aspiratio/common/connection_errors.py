"""
Connection error utilities for categorizing and handling network errors.
Shared across the aspiratio codebase for consistent error handling.
"""
import requests


def categorize_connection_error(exception):
    """
    Categorize a connection exception into a specific error type.
    
    Args:
        exception: The exception object (typically a requests exception)
    
    Returns:
        tuple: (error_type: str, error_message: str, emoji: str)
        
    Error types:
        - 'timeout': Connection timed out
        - 'dns_error': DNS resolution failed
        - 'connection_refused': Server refused connection
        - 'connection_reset': Connection was reset
        - 'ssl_error': SSL/TLS certificate error
        - 'http_error': HTTP error status code
        - 'unknown': Other/unknown error
    """
    if isinstance(exception, requests.exceptions.Timeout):
        return ('timeout', 'Connection timed out', '⏱')
    
    if isinstance(exception, requests.exceptions.SSLError):
        error_msg = str(exception)[:100]
        return ('ssl_error', f'SSL/TLS error: {error_msg}', '🔒')
    
    if isinstance(exception, requests.exceptions.ConnectionError):
        error_str = str(exception)
        
        # Check for DNS resolution errors
        dns_error_indicators = ('NameResolutionError', 'Failed to resolve', 'getaddrinfo failed')
        if any(indicator in error_str for indicator in dns_error_indicators):
            return ('dns_error', 'DNS resolution failed - domain may be blocked or unreachable', '🌐')
        elif 'Connection refused' in error_str:
            return ('connection_refused', 'Connection refused by server', '🚫')
        elif 'Connection reset' in error_str:
            return ('connection_reset', 'Connection reset by server', '📡')
        else:
            return ('connection_error', f'Connection error: {error_str[:100]}', '📡')
    
    if isinstance(exception, requests.exceptions.HTTPError):
        status_code = exception.response.status_code if hasattr(exception, 'response') else None
        if status_code == 403:
            return ('http_403_blocked', 'HTTP 403 Forbidden - server blocking requests', '🚫')
        elif status_code == 404:
            return ('http_404_not_found', 'HTTP 404 Not Found', '❌')
        else:
            return ('http_error', f'HTTP error {status_code}', '❌')
    
    # Unknown error type
    return ('unknown_error', f'{type(exception).__name__}: {str(exception)[:100]}', '⚠')


def get_error_emoji(error_type):
    """Get emoji for an error type."""
    emoji_map = {
        'timeout': '⏱',
        'dns_error': '🌐',
        'connection_refused': '🚫',
        'connection_reset': '📡',
        'connection_error': '📡',
        'ssl_error': '🔒',
        'http_403_blocked': '🚫',
        'http_404_not_found': '❌',
        'http_error': '❌',
        'unknown_error': '⚠',
    }
    return emoji_map.get(error_type, '⚠')


def format_error_message(error_type, error_message, include_emoji=True):
    """
    Format an error message with optional emoji prefix.
    
    Args:
        error_type: The error type string
        error_message: The error message
        include_emoji: Whether to include emoji prefix
    
    Returns:
        str: Formatted error message
    """
    if include_emoji:
        emoji = get_error_emoji(error_type)
        return f"{emoji} {error_message}"
    return error_message
