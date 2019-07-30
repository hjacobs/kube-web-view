.PHONY: clean test appjs docker push mock

IMAGE            ?= hjacobs/kube-web-view
GITDIFFHASH       = $(shell git diff | md5sum | cut -c 1-4)
VERSION          ?= $(shell git describe --tags --always --dirty=-dirty-$(GITDIFFHASH))
TAG              ?= $(VERSION)
TTYFLAGS          = $(shell test -t 0 && echo "-it")
OSNAME := $(shell uname | perl -ne 'print lc($$_)')

default: docker

clean:
	rm -f ./kind ./kubectl

kind:
	curl -Lo ./kind https://github.com/kubernetes-sigs/kind/releases/download/v0.4.0/kind-$(OSNAME)-amd64
	chmod +x ./kind

kubectl:
	curl -LO https://storage.googleapis.com/kubernetes-release/release/$$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/$(OSNAME)/amd64/kubectl
	chmod +x ./kubectl


.PHONY: test
test: test.unit test.e2e

.PHONY: test.unit
test.unit:
	poetry run black --check kube_web
	poetry run coverage run --source=kube_web -m py.test tests/unit
	poetry run coverage report

.PHONY: test.e2e
test.e2e: kind kubectl docker
	env TEST_KIND=./kind TEST_KUBECTL=./kubectl TEST_IMAGE=$(IMAGE):$(TAG) \
		poetry run pytest -v -r=a \
			--log-cli-level info \
			--log-cli-format '%(asctime)s %(levelname)s %(message)s' \
			tests/e2e $(PYTEST_OPTIONS)

.PHONY: clean.e2e
clean.e2e:
	./kind delete cluster --name=kube-web-view-e2e

docker: 
	docker build --build-arg "VERSION=$(VERSION)" -t "$(IMAGE):$(TAG)" .
	@echo 'Docker image $(IMAGE):$(TAG) can now be used.'

push: docker
	docker push "$(IMAGE):$(TAG)"
	docker tag "$(IMAGE):$(TAG)" "$(IMAGE):latest"
	docker push "$(IMAGE):latest"

mock:
	docker run $(TTYFLAGS) -p 8080:8080 "$(IMAGE):$(TAG)" --mock

.PHONY: docs
docs:
	poetry run sphinx-build docs docs/_build

.PHONY: run
run:
	poetry run python3 -m kube_web --show-container-logs

.PHONY: run.kind
run.kind:
	poetry run python3 -m kube_web --kubeconfig-path=$$(./kind get kubeconfig-path --name=kube-web-view-e2e)

.PHONY: mirror
mirror:
	git push --mirror git@github.com:hjacobs/kube-web-view.git
