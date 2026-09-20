# ai-RedAlert — simple UX layer. `make help` for everything.
COMPOSE = docker compose -f docker/docker-compose.yml
MICRO_MODEL ?= qwen2.5:3b
BARON_MODEL ?= hf.co/AlicanKiraz0/BaronLLM-v2-OffensiveSecurityLLM-Q8:Q8_0

.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

build: ## Build the toolkit image (Kali + offensive toolset)
	$(COMPOSE) build toolkit

shell: ## Drop into the toolkit shell (scope-aware)
	$(COMPOSE) run --rm toolkit bash

scope: ## Show the active scope allowlist inside the container
	$(COMPOSE) run --rm toolkit ra scope

llm-micro: ## Start the LLM sidecar with a small ~3B model (laptop)
	$(COMPOSE) --profile micro up -d ollama
	$(COMPOSE) exec ollama ollama pull $(MICRO_MODEL)
	@echo "micro model ready: $(MICRO_MODEL) — talk to it with 'ra-ai' in the toolkit shell"

llm-baron: ## Start the LLM sidecar with BaronLLM-v2 14B (workstation, 16GB+ RAM)
	$(COMPOSE) --profile baron up -d ollama
	$(COMPOSE) exec ollama ollama pull $(BARON_MODEL)
	@echo "BaronLLM ready — talk to it with 'ra-ai' in the toolkit shell"

llm-down: ## Stop the LLM sidecar
	$(COMPOSE) stop ollama || true

test: ## Run the scope-engine self-tests (no container needed)
	python3 tests/test_scope.py

own: ## Reclaim host ownership of engagement files (root-owned; tools need root)
	docker run --rm -v $(PWD)/engagements:/e ai-redalert:latest chown -R $(shell id -u):$(shell id -g) /e
	@echo "engagement files now owned by you"

down: ## Tear down the whole stack
	$(COMPOSE) down

clean: ## Remove the toolkit image
	docker image rm ai-redalert:latest 2>/dev/null || true

.PHONY: help build shell scope llm-micro llm-baron llm-down test own down clean
