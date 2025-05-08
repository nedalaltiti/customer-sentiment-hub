# Makefile for Customer Sentiment Hub

.PHONY: setup install test lint format clean build docs serve

# Default Python interpreter
PYTHON := python

# Get project name from pyproject.toml
PROJECT_NAME := customer_sentiment_hub

# Set up virtual environment and install dependencies
setup:
	poetry install

# Install for development
install:
	poetry install --with dev

# Run tests
test:
	poetry run pytest

# Run tests with coverage
test-cov:
	poetry run pytest --cov=$(PROJECT_NAME) --cov-report=xml --cov-report=term

# Run linters
lint:
	poetry run isort src tests
	poetry run black src tests
	poetry run pylint src
	poetry run mypy src

# Format code
format:
	poetry run isort src tests
	poetry run black src tests

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build package
build:
	poetry build

# Generate documentation
docs:
	mkdir -p docs
	poetry run pdoc --html --output-dir docs/ src/$(PROJECT_NAME)

# Serve documentation locally
serve-docs:
	poetry run pdoc --http : src/$(PROJECT_NAME)

# Run the CLI application
run:
	poetry run sentiment-hub analyze

# Install pre-commit hooks
pre-commit:
	poetry run pre-commit install