.DEFAULT_GOAL := help
.PHONY: help init venv requirements test start lint update homeassistant-install homeassistant-update

HAS_APK := $(shell command -v apk 2>/dev/null)
HAS_APT := $(shell command -v apt 2>/dev/null)
PYTHON_BIN := $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3)
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest

help: ## Shows help message.
	@printf "\033[1m%s\033[36m %s\033[0m \n\n" "Development environment for" "wienerlinien";
	@awk 'BEGIN {FS = ":.*##";} /^[a-zA-Z_-]+:.*?##/ { printf " \033[36m make %-25s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST);
	@echo

init: homeassistant-install requirements

venv:
	@if [ ! -x "$(PYTHON)" ] || [ "$$("$(PYTHON)" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)" != "$$("$(PYTHON_BIN)" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" ]; then \
		rm -rf $(VENV); \
		"$(PYTHON_BIN)" -m venv $(VENV); \
	fi

requirements: venv
ifdef HAS_APK
	apk add libxml2-dev libxslt-dev
endif
ifdef HAS_APT
	sudo apt update && sudo apt install libxml2-dev libxslt-dev
endif
	$(PIP) --disable-pip-version-check install -U pip setuptools wheel
	$(PIP) --disable-pip-version-check install -r requirements.txt

test: requirements ## Run tests in the local virtualenv
	$(PYTEST)

start: ## Start the HA with the integration
	@bash .devcontainer/integration_start;

lint: ## Run linters
	pre-commit install-hooks --config .github/pre-commit-config.yaml;
	pre-commit run --hook-stage manual --all-files --config .github/pre-commit-config.yaml;

update: ## Pull master from custom-components/wienerlinien
	git pull upstream master;

homeassistant-install: venv ## Install the latest dev version of Home Assistant
	$(PIP) --disable-pip-version-check install -U pip setuptools wheel
	$(PIP) --disable-pip-version-check \
		install --upgrade git+https://github.com/home-assistant/home-assistant.git@dev;

homeassistant-update: homeassistant-install ## Alias for 'homeassistant-install'
