all: test


lint:
	pre-commit run --all-files

test: lint
	pytest tests
