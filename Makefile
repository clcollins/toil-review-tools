CONTAINER_SUBSYS=podman

PROJECT := toil-review-tools
IMAGE := metrics
GIT_HASH := $(shell git rev-parse --short HEAD)

REGISTRY := localhost
IMAGE_REF := $(REGISTRY)/$(PROJECT)/$(IMAGE)
LATEST_IMAGE := $(shell $(CONTAINER_SUBSYS) images --filter "label=.metadata.project-name=$(PROJECT)" --no-trunc | awk '/latest/ {print $$3}')

TOKEN := $(shell yq read ~/.config/pagerduty/pd.yml authtoken)

# Run Options
LAYERS := 4 5
DAYS := 7

.PHONY: build build_binary build_image test_image tag_image run

all: build_image test_image tag_image

build: build_binary

build_binary:
	@./venv-$(PROJECT)/bin/pyinstaller --onefile metrics.py
	@./venv-$(PROJECT)/bin/staticx dist/metrics dist/metrics_app

build_image:
	@$(CONTAINER_SUBSYS) build --tag $(IMAGE_REF):$(GIT_HASH) --label ".metadata.project-name=$(PROJECT)" .

test_image:
	@$(CONTAINER_SUBSYS) run --tty --rm $(IMAGE_REF):$(GIT_HASH)

tag_image:
	@$(CONTAINER_SUBSYS) tag $(IMAGE_REF):$(GIT_HASH) $(IMAGE_REF):latest

test:
	python -m unittest

run:
	@$(CONTAINER_SUBSYS) run --tty --env PD_TOKEN=$(TOKEN) --rm $(LATEST_IMAGE) all --layers $(LAYERS) --days $(DAYS)

freeze:
	@./venv-$(PROJECT)/bin/pip3 freeze > requirements.txt