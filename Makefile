# ai-RedAlert — simple UX layer. `make help` for everything.
# Set GPU=1 to layer the NVIDIA override (needs nvidia-container-toolkit on the host):
#   GPU=1 make shell        GPU=1 make llm-baron
COMPOSE = docker compose -f docker/docker-compose.yml $(if $(GPU),-f docker/docker-compose.gpu.yml)
COMPOSE_VPN = docker compose --env-file .env.vpn -f docker/docker-compose.yml -f docker/docker-compose.vpn.yml $(if $(GPU),-f docker/docker-compose.gpu.yml)
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

gpu-check: ## Verify the host GPU is visible to Docker (for hashcat/LLM accel)
	docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi || \
	  echo "No GPU visible — install nvidia-container-toolkit, or run CPU-only (default)."

test: ## Run the scope-engine self-tests (no container needed)
	python3 tests/test_scope.py

own: ## Reclaim host ownership of engagement files (root-owned; tools need root)
	docker run --rm -v $(PWD)/engagements:/e ai-redalert:latest chown -R $(shell id -u):$(shell id -g) /e
	@echo "engagement files now owned by you"

vpn-up: ## Bring up the VPN egress (gluetun) and confirm the external exit IP
	@test -f .env.vpn || { echo "Missing .env.vpn — cp .env.vpn.example .env.vpn and fill it in."; exit 1; }
	$(COMPOSE_VPN) up -d gluetun
	@echo "waiting for the tunnel to come up..."; \
	for i in $$(seq 1 20); do \
	  ip=$$(docker run --rm --network=container:redalert-gluetun ai-redalert:latest curl -s --max-time 6 https://api.ipify.org 2>/dev/null); \
	  if [ -n "$$ip" ]; then echo "\033[32m✓ VPN egress IP: $$ip\033[0m  (your scans now originate here)"; exit 0; fi; \
	  sleep 3; \
	done; \
	echo "\033[31m✗ Could not confirm a VPN exit IP — tunnel not up. Check .env.vpn creds / provider status.\033[0m"; \
	docker logs --tail 20 redalert-gluetun; exit 1

shell-vpn: vpn-up ## Toolkit shell whose traffic egresses via the VPN (fail-closed)
	$(COMPOSE_VPN) run --rm toolkit bash

vpn-status: ## Show the current VPN egress status / exit IP
	@docker ps --filter name=redalert-gluetun --format "gluetun: {{.Status}}" || true
	@docker run --rm --network=container:redalert-gluetun ai-redalert:latest curl -s --max-time 6 https://api.ipify.org 2>/dev/null \
	  && echo "  <- current exit IP" || echo "VPN not up (no exit IP)."

vpn-down: ## Tear down the VPN egress
	$(COMPOSE_VPN) down

down: ## Tear down the whole stack
	$(COMPOSE) down

clean: ## Remove the toolkit image
	docker image rm ai-redalert:latest 2>/dev/null || true

.PHONY: help build shell scope llm-micro llm-baron llm-down gpu-check test own vpn-up shell-vpn vpn-status vpn-down down clean
