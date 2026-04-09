PYTHON ?= python3
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
export PYTHONPATH := $(abspath $(ROOT)/..)
CONFIG ?= config.yaml

# JSON ключ сервисного аккаунта в корне репозитория (override: make run GOOGLE_CREDENTIALS_FILE=...)
GOOGLE_CREDENTIALS_FILE ?= $(ROOT)/sixth-module-492820-f9-d76cdceb4abf

ifndef GOOGLE_SERVICE_ACCOUNT_JSON
ifneq ($(wildcard $(GOOGLE_CREDENTIALS_FILE)),)
export GOOGLE_SERVICE_ACCOUNT_JSON := $(shell cat '$(GOOGLE_CREDENTIALS_FILE)')
endif
endif

.PHONY: help run once install now

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

run: ## Start orchestrator (poll loop); креды: GOOGLE_CREDENTIALS_FILE или env GOOGLE_SERVICE_ACCOUNT_JSON
	cd $(ROOT) && $(PYTHON) task_orchestrator.py --config $(CONFIG)

once: ## Один проход; креды как у run
	cd $(ROOT) && $(PYTHON) task_orchestrator.py --config $(CONFIG) --once

install: ## pip install -r requirements.txt
	cd $(ROOT) && $(PYTHON) -m pip install -r requirements.txt
