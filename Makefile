.PHONY: help run migrate test lint format docker-up docker-down shell seed clean

help:
	@echo "Available commands:"
	@echo "  make run         - Run Django development server"
	@echo "  make migrate     - Run database migrations"
	@echo "  make test        - Run test suite with pytest and coverage report"
	@echo "  make lint        - Check code quality with flake8, black, and isort"
	@echo "  make format      - Automatically format code with black, isort, and autoflake"
	@echo "  make docker-up   - Start services using Docker Compose"
	@echo "  make docker-down - Stop services using Docker Compose"
	@echo "  make shell       - Open Django interactive shell"
	@echo "  make seed        - Seed database with demo data (merchants, customers, orders, payments, refunds, wallets)"
	@echo "  make clean       - Remove cached bytecode and test artifacts"

run:
	python manage.py runserver 0.0.0.0:8000

migrate:
	python manage.py makemigrations
	python manage.py migrate

test:
	python -m pytest --cov=apps --cov-report=term-missing

lint:
	python -m isort --check-only apps tests config
	python -m black --check apps tests config
	python -m flake8 --config=.flake8 apps tests config

format:
	python -m autoflake --remove-all-unused-imports --in-place --recursive apps tests config
	python -m isort --profile black apps tests config
	python -m black apps tests config

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down -v

shell:
	python manage.py shell

seed:
	python manage.py seed_data

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
