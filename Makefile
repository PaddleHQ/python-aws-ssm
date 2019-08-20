.PHONY: format
format: ## Automatically format the .py files with Black and Isort
	poetry run isort --recursive .
	poetry run black .

.PHONY: lint
lint: ## Check the .py files with Mypy, Flake8 and Black
	poetry run flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	poetry run flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
	poetry run black --check .
	poetry run mypy --ignore-missing-imports --disallow-untyped-defs .

.PHONY: tests
tests: ## Run tests with pytest and create the coverage report
	poetry run pytest --cov=./ --cov-report=xml

.SILENT: help
help: ## Shows all available commands
	set -x
	echo "Usage: make [target]"
	echo ""
	echo "Available targets:"
	grep ':.* ##\ ' ${MAKEFILE_LIST} | awk '{gsub(":[^#]*##","\t"); print}' | column -t -c 2 -s $$'\t'| sort
