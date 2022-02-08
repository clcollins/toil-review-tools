PROJECT := toil-review-tools
IMAGE := metrics
GIT_HASH := $(shell git rev-parse --short HEAD)

REGISTRY := localhost
IMAGE_REF := $(REGISTRY)/$(PROJECT)/$(IMAGE)
LATEST_IMAGE := $(shell podman images --filter "label=.metadata.project-name=$(PROJECT)" --no-trunc | awk '/latest/ {print $$3}')

TOKEN := $(shell yq read ~/.config/pagerduty/pd.yml authtoken)

# Run Options
LAYERS := 4 5
DAYS := 7

.PHONY: build build_binary build_image test_image tag_image run

all: build test_image tag_image

build: build_binary build_image

build_binary:
	@./venv-toil-review-tools/bin/pyinstaller --onefile metrics.py
	@./venv-toil-review-tools/bin/staticx dist/metrics dist/metrics_app

build_image:
	@podman build --tag $(IMAGE_REF):$(GIT_HASH) --label ".metadata.project-name=$(PROJECT)" .

test_image:
	@podman run --tty --rm $(IMAGE_REF):$(GIT_HASH)

tag_image:
	@podman tag $(IMAGE_REF):$(GIT_HASH) $(IMAGE_REF):latest


run:
	@podman run --tty --env PD_TOKEN=$(TOKEN) --rm $(LATEST_IMAGE) alerts --layers $(LAYERS) --days $(DAYS)
