"""
Aspiratio - Automated annual report downloader for OMXS30 companies.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "readme.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f 
                       if line.strip() and not line.startswith('#')]

setup(
    name="aspiratio",
    version="0.1.0",
    author="Jakob Johannesson",
    description="Automated annual report downloader for OMXS30 companies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jakobjohannesson/aspiratio",
    packages=find_packages(exclude=["tests*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            # Main workflow commands
            'aspiratio-download=scripts.download_reports:main',
            'aspiratio-validate=scripts.validate_reports:main',
            'aspiratio-retry=scripts.redownload_failed:main',
            'aspiratio-update=scripts.update_coverage_table:main',
            
            # Diagnostic tools
            'aspiratio-diagnose=scripts.diagnose_connections:main',
            
            # Setup tools
            'aspiratio-build-master=scripts.setup.build_master:main',
            'aspiratio-find-ir=scripts.setup.ir_scraper:main',
        ],
    },
    package_data={
        'aspiratio': ['*.yaml', '*.yml'],
    },
    include_package_data=True,
)
