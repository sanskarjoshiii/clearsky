# clearsky monorepo commands (macOS/Linux). On Windows use:  .\make.ps1 <target>
UV ?= uv
SAM ?= sam
CHAT_ARGS ?= --local --debug
BACKEND := cd backend &&

.PHONY: help install lint format test cov layer build dev dev-cloud dashboard e2e validate deploy web-deploy gen-seed seed chat book-all firms check-aws

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

# Dashboard on S3 + CloudFront (stack clearsky-dev-web, infra/web.yaml). VITE_* come from the backend stack outputs.
STACK ?= clearsky-dev
REGION ?= ap-south-1
out = $$(aws cloudformation describe-stacks --stack-name $(1) --region $(REGION) --query "Stacks[0].Outputs[?OutputKey=='$(2)'].OutputValue" --output text)
web-deploy:
	cd dashboard && npm ci && \
	  VITE_AUTH_MODE=cognito VITE_AWS_REGION=$(REGION) \
	  VITE_API_URL=$(call out,$(STACK),ApiUrl) \
	  VITE_USER_POOL_ID=$(call out,$(STACK),UserPoolId) \
	  VITE_USER_POOL_CLIENT_ID=$(call out,$(STACK),UserPoolClientId) \
	  npm run build
	aws s3 sync dashboard/dist s3://$(call out,$(STACK)-web,SiteBucketName) --delete --cache-control "public,max-age=31536000,immutable" --exclude index.html
	aws s3 cp dashboard/dist/index.html s3://$(call out,$(STACK)-web,SiteBucketName)/index.html --cache-control "no-cache"
	aws cloudfront create-invalidation --distribution-id $(call out,$(STACK)-web,DistributionId) --paths "/index.html" "/" --query Invalidation.Id --output text
	@echo "Dashboard: $(call out,$(STACK)-web,SiteUrl)"

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

# Local full stack: API (mock DynamoDB + seed + WhatsApp simulator + dev login) and the dashboard
dev:
	$(BACKEND) $(UV) run python scripts/dev_server.py

# Same, but real WhatsApp: WA_* from .env, replies go out through Meta. Expose it with `ngrok http 8787`
# and use <ngrok url>/webhook/whatsapp as Meta's callback URL (SETUP_GUIDE §7.0).
dev-cloud:
	$(BACKEND) WA_MODE=cloud AWS_PROFILE=$${AWS_PROFILE:-clearsky} $(UV) run python scripts/dev_server.py

dashboard:
	cd dashboard && npm install && npm run dev

e2e:
	cd dashboard && npm run typecheck && npm test && npx playwright test
