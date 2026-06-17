.PHONY: install lint test run docker-up

install:
	pip install ".[dev]"

lint:
	ruff check .

test:
	pytest

run:
	uvicorn app.main:app --reload

docker-up:
	docker compose up --build
