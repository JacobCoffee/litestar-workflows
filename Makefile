# Helper commands for the project

# -- Development

.PHONY: install
install:  ## Install the project using uv
	@echo "=> Installing the project"
	@uv venv -p python3.9 --seed
	@uv pip install -e .[dev-lint,dev-test]
	@echo "=> Done"

.PHONY: clean
clean: docs-clean  ## Clean up temporary build artifacts
	@echo "=> Cleaning working directory"
	@find . -name '*.egg-info' -exec rm -rf {} +
	@find . -name '*.egg' -exec rm -f {} +
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -rf {} +
	@find . -name '.ipynb_checkpoints' -exec rm -rf {} +
	@rm -rf .pytest_cache .ruff_cache .hypothesis build/ -rf dist/ .eggs/
	@rm -rf .coverage coverage.xml coverage.json htmlcov/ .pytest_cache tests/.pytest_cache tests/**/.pytest_cache .mypy_cache

# -- Documentation

.PHONY: docs-serve
docs-serve:  ## Serve the documentation
	@echo "=> Running the project documentation"
	@sphinx-autobuild docs docs/_build/ -j auto --watch litestar-workflows --watch docs --watch tests --watch CONTRIBUTING.rst --port 8001

.PHONY: docs-build
docs-clean:  ## Dump the existing built docs
	@echo "=> Cleaning documentation build assets"
	@rm -rf docs/_build
	@echo "=> Removed existing documentation build assets"

# -- Testing

.PHONY: infra
infra:  ## Start the infrastructure for testing
	@echo "=> Starting required infrastructure"
	@docker compose -f tests/docker-compose.yml up -d
	@echo "=> Done"

.PHONY: test
test: infra ## Run the test suite
	@echo "=> Running the test suite"
	@pytest tests
	@echo "=> Done"

