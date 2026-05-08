.DEFAULT_GOAL := help
PYTHON        := python3
PIP           := pip3

.PHONY: help install up down seed bronze-silver silver-gold test lint reset

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*##"}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:        ## Install lakehouse-common in editable mode
	$(PIP) install -e ./common[dev] --quiet

up:             ## Start Docker Compose (PySpark + Jupyter)
	docker compose up -d
	@echo "Jupyter available at http://localhost:8888  |  Spark UI at http://localhost:4040"

down:           ## Stop Docker Compose
	docker compose down

seed:           ## Generate sample CSVs in data/local/bronze/
	ENV=local $(PYTHON) scripts/seed_local_data.py

bronze-silver:  ## Run Bronze→Silver Spark job locally
	ENV=local $(PYTHON) -m processing.bronze_to_silver.job

silver-gold:    ## Run Silver→Gold Spark job locally
	ENV=local $(PYTHON) -m processing.silver_to_gold.job

test:           ## Run unit tests (no Spark cluster required)
	pytest tests/unit -v --tb=short

lint:           ## Run ruff linter
	ruff check . --fix

reset:          ## Wipe local silver/gold/quarantine/dq_results for a clean run
	ENV=local $(PYTHON) scripts/reset_local_lakehouse.py
