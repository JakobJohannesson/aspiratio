# Configuration System - Usage Guide

## Overview

The project now has centralized configuration in `config.yaml`. This makes it easy to tune parameters without editing code.

## Quick Start

### Basic Usage

```python
from aspiratio.config import get, get_validation_params, get_download_params

# Get specific value using dot notation
min_pages = get('validation.min_pages')  # Returns 50
max_retries = get('download.max_retries')  # Returns 3

# Get group of related settings
validation = get_validation_params()
# {'min_pages': 50, 'max_pages': 500, 'confidence_threshold': 60, ...}

download = get_download_params()
# {'max_retries': 3, 'max_consecutive_failures': 3, ...}
```

### Common Patterns

```python
from aspiratio.config import (
    get_user_agents,
    get_target_years,
    get_exclude_patterns,
    get_paths
)

# Get user agents for rotation
user_agents = get_user_agents()
random_agent = random.choice(user_agents)

# Get target years
years = get_target_years()  # [2019, 2020, 2021, 2022, 2023, 2024]

# Get exclude patterns for validation
exclude = get_exclude_patterns()  # ["q1|q2|q3|q4", "quarter", ...]

# Get file paths
paths = get_paths()
coverage_file = paths['coverage_table']  # "coverage_table_updated.csv"
```

## Migration Examples

### Before (Hard-coded)

```python
# In validate_reports.py
MIN_PAGES = 50
MAX_PAGES = 500

def validate_pdf(pdf_path):
    if page_count < MIN_PAGES:
        return False
```

### After (Config-driven)

```python
from aspiratio.config import get_validation_params

def validate_pdf(pdf_path):
    params = get_validation_params()
    if page_count < params['min_pages']:
        return False
```

### Before (Hard-coded user agents)

```python
# In report_downloader.py
USER_AGENTS = [
    "Mozilla/5.0 ...",
    "Mozilla/5.0 ...",
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)
```

### After (Config-driven)

```python
from aspiratio.config import get_user_agents
import random

def get_random_user_agent():
    return random.choice(get_user_agents())
```

## Benefits

1. **Easy Tuning**: Change `min_pages` from 50 → 40 in one place
2. **Environment-Specific**: Different configs for dev/prod
3. **Documentation**: config.yaml serves as living documentation
4. **Type Safety**: Config loader provides defaults
5. **Validation**: Can add schema validation later

## Configuration Sections

### `project.*`
- Project metadata and target specifications

### `paths.*`
- All file paths (inputs, outputs, directories)

### `download.*`
- Download behavior (retries, timeouts, rate limiting)

### `http.*`
- HTTP settings (user agents, timeouts)

### `validation.*`
- PDF validation criteria and weights

### `playwright.*`
- Browser automation settings

### `ir_search.*`
- IR URL discovery configuration

## Advanced Usage

### Override Config Path

```python
from aspiratio.config import load_config

# Load from custom location
config = load_config('/path/to/custom_config.yaml')
```

### Force Reload

```python
from aspiratio.config import reload_config

# Reload config (e.g., after editing config.yaml)
reload_config()
```

### Company-Specific Overrides

```python
from aspiratio.config import get

# Check if company has override
overrides = get(f'company_overrides.{company_id}', {})
min_pages = overrides.get('min_pages', get('validation.min_pages'))
```

## Next Steps

The configuration system is ready to use. To migrate existing code:

1. Import config functions instead of hard-coded constants
2. Replace literals with `get()` calls
3. Test that behavior is unchanged
4. Enjoy easy tuning! 🎯

## Future Enhancements

- [ ] Add schema validation (using `jsonschema` or `pydantic`)
- [ ] Support environment variables (e.g., `ASPIRATIO_MAX_RETRIES`)
- [ ] Add config CLI: `aspiratio config set validation.min_pages 40`
- [ ] Profile-based configs (dev, prod, test)
