.PHONY: install install-dev test lint format clean build

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[test,evaluation]"
	pre-commit install

# Development
test:
	pytest tests/

lint:
	ruff check ant_agent/
	ruff format --check ant_agent/

format:
	ruff format ant_agent/

clean:
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ build/ dist/ *.egg-info/

# Build
build:
	python -m build

# CLI
cli:
	python cli/main.py

# Setup example config
setup-config:
	cp ant_config.yaml.example ant_config.yaml
	@echo "Please edit ant_config.yaml with your API keys"