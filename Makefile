# Default target
help:
	@echo ""
	@echo "Available targets:"
	@echo "  make build                   Build the Docker image for the tool"
	@echo "  make run SERVER=...          Run the tool interactively (prints certs to stdout)"
	@echo "  make save SERVER=...         Save the certificate bundle to ./ldaps_bundle.crt"
	@echo "  make test                    Run pytest inside the container (optional, if tests are present)"
	@echo "  make help                    Show this help message"
	@echo ""

# Explicit targets
.PHONY: help build run save test

IMAGE_NAME = ldaps-cert-tool

build:
	@docker build -t $(IMAGE_NAME) .

run:
	@docker run --rm $(IMAGE_NAME) --server $(SERVER) --debug

save:
	@docker run --rm -v $(PWD):/out $(IMAGE_NAME) --server $(SERVER) --output /out/ldaps_bundle.crt

test:
	@docker run --rm --entrypoint "" $(IMAGE_NAME) python -m pytest -v
