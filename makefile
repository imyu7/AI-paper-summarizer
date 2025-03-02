.PHONY: lint
lint: ## run lint with poetry (ruff, mypy)
	poetry run ruff format src
	poetry run ruff check --fix src
	poetry run mypy src --explicit-package-bases


.PHONY: test
test: ## run tests with poetry
	poetry run pytest tests