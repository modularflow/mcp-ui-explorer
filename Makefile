.PHONY: help install install-dev test test-unit test-integration test-performance lint format clean build docs

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install the package"
	@echo "  install-dev      Install development dependencies"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  lint             Run all linting tools"
	@echo "  format           Format code with black and isort"
	@echo "  clean            Clean build artifacts"
	@echo "  build            Build the package"
	@echo "  docs             Generate documentation"
	@echo "  security         Run security checks"
	@echo "  pre-commit       Run pre-commit checks"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-test:
	pip install -e ".[test]"

install-lint:
	pip install -e ".[lint]"

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-performance:
	pytest tests/performance/ -v --benchmark-only

test-coverage:
	pytest --cov=src/mcp_ui_explorer --cov-report=html --cov-report=term

test-fast:
	pytest -x --ff

# Linting and formatting
lint: lint-black lint-isort lint-flake8 lint-mypy lint-pylint

lint-black:
	black --check --diff src/ tests/

lint-isort:
	isort --check-only --diff src/ tests/

lint-flake8:
	flake8 src/ tests/

lint-mypy:
	mypy src/mcp_ui_explorer

lint-pylint:
	pylint src/mcp_ui_explorer

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

# Security
security:
	bandit -r src/
	safety check

# Build and clean
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

build-check:
	python -m build
	twine check dist/*

# Documentation
docs:
	@echo "Documentation generation not yet implemented"

# Pre-commit checks (run before committing)
pre-commit: format lint test-unit security
	@echo "✅ Pre-commit checks passed!"

# CI simulation (run what CI will run)
ci: install-dev lint test security build-check
	@echo "✅ CI simulation completed!"

# Development setup
setup-dev: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make help' to see available commands"

# Quick development cycle
dev: format lint test-unit
	@echo "✅ Development cycle complete!"

# Release preparation
release-check: clean install-dev lint test security build-check
	@echo "✅ Release checks passed!"

# Performance profiling
profile:
	pytest tests/performance/ --benchmark-only --benchmark-json=benchmark.json
	@echo "Benchmark results saved to benchmark.json"

# Test with different Python versions (if available)
test-all-python:
	@echo "Testing with Python 3.10..."
	python3.10 -m pytest tests/unit/ || echo "Python 3.10 not available"
	@echo "Testing with Python 3.11..."
	python3.11 -m pytest tests/unit/ || echo "Python 3.11 not available"
	@echo "Testing with Python 3.12..."
	python3.12 -m pytest tests/unit/ || echo "Python 3.12 not available" 