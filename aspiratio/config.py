"""
Configuration loader for Aspiratio project.
Provides centralized access to settings from config.yaml.
"""
import yaml
from pathlib import Path
from typing import Any, Dict, List

# Cache the config to avoid re-reading file
_config_cache = None

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml (default: project root)
    
    Returns:
        Dict with configuration settings
    """
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    if config_path is None:
        # Default: config.yaml in project root (two levels up from this file)
        # This file is at: aspiratio/config.py
        # Project root is: ./
        config_path = Path(__file__).parent.parent / 'config.yaml'
    
    with open(config_path, 'r') as f:
        _config_cache = yaml.safe_load(f)
    
    return _config_cache

def get(key_path: str, default: Any = None) -> Any:
    """
    Get configuration value using dot notation.
    
    Examples:
        get('validation.min_pages') -> 50
        get('download.max_retries') -> 3
        get('http.user_agents') -> [list of user agents]
    
    Args:
        key_path: Dot-separated path to config value
        default: Default value if key not found
    
    Returns:
        Configuration value or default
    """
    config = load_config()
    
    # Navigate through nested dict using dot notation
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value

# Convenience functions for common config access patterns

def get_user_agents() -> List[str]:
    """Get list of user agents for rotation."""
    return get('http.user_agents', [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    ])

def get_validation_params() -> Dict[str, int]:
    """Get validation parameters (min_pages, max_pages, etc.)"""
    return {
        'min_pages': get('validation.min_pages', 50),
        'max_pages': get('validation.max_pages', 500),
        'confidence_threshold': get('validation.confidence_threshold', 60),
        'max_pages_to_check': get('validation.max_pages_to_check', 5),
    }

def get_download_params() -> Dict[str, Any]:
    """Get download parameters (retries, timeouts, etc.)"""
    return {
        'max_retries': get('download.max_retries', 3),
        'max_consecutive_failures': get('download.max_consecutive_failures', 3),
        'max_depth': get('download.max_depth', 2),
        'enable_failsafe': get('download.enable_failsafe', True),
        'request_timeout': get('download.request_timeout', 30),
    }

def get_paths() -> Dict[str, str]:
    """Get all file paths."""
    return get('paths', {})

def get_target_years() -> List[int]:
    """Get list of target years."""
    return get('project.target_years', [2019, 2020, 2021, 2022, 2023, 2024])

def get_exclude_patterns() -> List[str]:
    """Get patterns to exclude from annual reports."""
    return get('validation.exclude_patterns', [])

def reload_config():
    """Force reload configuration from file."""
    global _config_cache
    _config_cache = None
    return load_config()
