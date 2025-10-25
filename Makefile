.PHONY: help install install-dev test test-cov lint format clean docs build

help:
	@echo "Forest Change Framework - Available Commands"
	@echo "============================================"
	@echo ""
	@echo "Installation:"
	@echo "  make install         Install package in editable mode"
	@echo "  make install-dev     Install package with dev dependencies"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test            Run unit and integration tests"
	@echo "  make test-cov        Run tests with coverage report"
	@echo "  make lint            Run linters (flake8, mypy)"
	@echo "  make format          Format code (black, isort)"
	@echo ""
	@echo "Documentation & Build:"
	@echo "  make docs            Build documentation"
	@echo "  make build           Build distribution packages"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           Remove build artifacts and caches"
	@echo ""

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=src/forest_change_framework --cov-report=html --cov-report=term-missing

lint:
	@echo "Running flake8..."
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	@echo "Running mypy..."
	mypy src/forest_change_framework --ignore-missing-imports

format:
	@echo "Running isort..."
	isort src/ tests/
	@echo "Running black..."
	black src/ tests/

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	@echo "Cleaning Python cache..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Cleaning test cache..."
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	@echo "Cleaning docs..."
	rm -rf docs/_build/
	@echo "Clean complete!"

docs:
	@echo "Building documentation..."
	cd docs && sphinx-build -b html . _build
	@echo "Documentation built in docs/_build/html/"

build: clean
	@echo "Building distribution packages..."
	python -m pip install --upgrade build
	python -m build
	@echo "Build complete! Packages in dist/"
