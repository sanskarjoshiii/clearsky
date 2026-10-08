# ClearSky monorepo commands (macOS/Linux). On Windows use:  .\make.ps1 <target>
UV ?= uv
SAM ?= sam
CHAT_ARGS ?= --local --debug
BACKEND := cd backend &&

.PHONY: help install lint format test cov layer build validate deploy gen-seed seed chat book-all firms check-aws

help:
	@echo "install lint format test build validate deploy gen-seed seed chat book-all firms check-aws"

install:
	$(BACKEND) $(UV) sync

lint:
	$(BACKEND) $(UV) run ruff check src tests scripts
	$(BACKEND) $(UV) run ruff format --check src tests scripts
	$(BACKEND) $(UV) run mypy

format:
	$(BACKEND) $(UV) run ruff check --fix src tests scripts
	$(BACKEND) $(UV) run ruff format src tests scripts

test:
	$(BACKEND) $(UV) run pytest

cov:
	$(BACKEND) $(UV) run pytest --cov=clearsky --cov-report=term-missing:skip-covered

# Dependencies are resolved and installed for the Lambda target (Linux arm64, Python 3.12) into a layer,
# so host-only packages (e.g. pywin32 on Windows) never leak in and SAM only copies our source.
LAMBDA_PLATFORM := --python-version 3.12 --python-platform aarch64-manylinux_2_28
layer:
	$(BACKEND) $(UV) pip compile pyproject.toml $(LAMBDA_PLATFORM) --no-header --no-annotate --quiet -o requirements-lambda.txt
	rm -rf infra/.layer
	$(BACKEND) $(UV) pip install -r requirements-lambda.txt --target ../infra/.layer/python $(LAMBDA_PLATFORM) --only-binary :all: --quiet

build: layer
	cd infra && $(SAM) build

validate:
	cd infra && $(SAM) validate --lint

# Deploys to AWS (creates paid resources). Needs explicit approval:  make deploy CONFIRM=yes
deploy: build
	@if [ "$(CONFIRM)" != "yes" ]; then echo "Refusing to deploy without CONFIRM=yes (team approval required)."; exit 1; fi
	cd infra && $(SAM) deploy

gen-seed:
	$(BACKEND) $(UV) run python scripts/gen_seed.py --seed 42

# Loads seed into the tables named by TABLE_PREFIX (deployed stack). Deletes existing items first.
seed: gen-seed
	$(BACKEND) $(UV) run python scripts/seed_dynamo.py --reset --set-clock

chat:
	$(BACKEND) $(UV) run python scripts/chat_cli.py $(CHAT_ARGS)

book-all:
	$(BACKEND) $(UV) run python scripts/book_all.py --local --dry-run

firms:
	$(BACKEND) $(UV) run python scripts/fetch_firms.py --apply-seed

check-aws:
	$(BACKEND) $(UV) run python scripts/check_aws.py
