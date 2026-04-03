from setuptools import setup, find_packages
from pathlib import Path

requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f
                        if line.strip() and not line.startswith("#")]

setup(
    name="aspiratio",
    version="0.2.0",
    author="Jakob Johannesson",
    description="Automated annual report downloader for Nordic companies",
    packages=find_packages(exclude=["tests*", "dashboard*"]),
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "aspiratio-download=scripts.download:main",
            "aspiratio-init=scripts.init_manifest:main",
        ],
    },
)
