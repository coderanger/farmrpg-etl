.PHONY: test
test:
	python -m pytest

.PHONY: run
run:
	python -m farmrpg_etl

.PHONY: makemigrations
makemigrations:
	alembic revision --autogenerate -m "${MESSAGE}"

.PHONY: migrations
migrations: makemigrations

.PHONY: migrate
migrate:
	alembic upgrade head
