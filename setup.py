"""
Setup configuration for forest-change-framework.

This file configures the package for distribution and installation.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="forest-change-framework",
    version="0.1.0",
    author="Flavio Cordari",
    author_email="flaviocordari@uniroma1.it",
    description="A modular, extensible framework for forest change detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bitwiseops/forest-change-framework",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyyaml>=6.0",
        "click>=8.0",
        "typing-extensions>=4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "mypy>=1.0",
            "flake8>=6.0",
            "isort>=5.0",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "forest-change-framework=forest_change_framework.cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
