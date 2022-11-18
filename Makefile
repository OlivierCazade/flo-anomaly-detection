VERSION ?= main
IMAGE_TAG_BASE ?=
IMG ?= $(IMAGE_TAG_BASE):$(VERSION)

NAMESPACE ?= netobserv

# Image building tool (docker / podman)
ifndef OCI_BIN
ifeq (,$(shell which podman 2>/dev/null))
OCI_BIN=docker
else
OCI_BIN=podman
endif
endif


.PHONY: image-build
image-build:
	$(OCI_BIN) build --build-arg BUILD_VERSION="${BUILD_VERSION}" -t ${IMG} .

.PHONY: image-push
image-push:
	$(OCI_BIN) push ${IMG}

.PHONY: deploy
deploy:
	sed 's|%DOCKER_IMG%|$(IMG)|g' deploy.yaml > /tmp/deployment.yaml
	kubectl apply -f /tmp/deployment.yaml -n "${NAMESPACE}"
