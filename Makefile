all: test


flake:
	flake8 aiohttp_cors tests setup.py

test: flake
	pytest tests
