.PHONY: clean test appjs docker push mock

IMAGE            ?= hjacobs/kube-web-view
GITDIFFHASH       = $(shell git diff | md5sum | cut -c 1-4)
VERSION          ?= $(shell git describe --tags --always --dirty=-dirty-$(GITDIFFHASH))
VERSIONPY         = $(shell echo $(VERSION) | cut -d- -f 1)
TAG              ?= $(VERSION)
TTYFLAGS          = $(shell test -t 0 && echo "-it")
OSNAME := $(shell uname | perl -ne 'print lc($$_)')

default: docker

.PHONY: poetry
poetry:
	poetry install

.PHONY: test
test: poetry lint test.unit test.e2e

.PHONY: lint
lint: 
	poetry run flake8
	poetry run black --check kube_web

.PHONY: test.unit
test.unit:
	poetry run coverage run --source=kube_web -m py.test tests/unit
	poetry run coverage report

.PHONY: test.e2e
test.e2e: docker
	env TEST_IMAGE=$(IMAGE):$(TAG) \
		poetry run pytest -v -r=a \
			--log-cli-level info \
			--log-cli-format '%(asctime)s %(levelname)s %(message)s' \
			--cluster-name kube-web-view-e2e \
			tests/e2e

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
	poetry run python3 -m kube_web --show-container-logs --debug "--object-links=ingresses=javascript:alert('{name}')" "--label-links=application=javascript:alert('Application label has value {label_value}')|eye|This is a link!" --preferred-api-versions=deployments=apps/v1

.PHONY: run.kind
run.kind:
	poetry run python3 -m kube_web --kubeconfig-path=$$(.pytest-kind/kube-web-view-e2e/kind get kubeconfig-path --name=kube-web-view-e2e) --debug --show-container-logs --search-default-resource-types=deployments,pods,configmaps --default-label-columns=pods=app "--default-hidden-columns=pods=Nominated Node" --exclude-namespaces=.*forbidden.*

.PHONY: mirror
mirror:
	git push --mirror git@github.com:hjacobs/kube-web-view.git

.PHONY: version
version:
	# poetry only accepts a narrow version format
	sed -i "s/^version = .*/version = \"${VERSIONPY}\"/" pyproject.toml
	sed -i "s/^version = .*/version = \"${VERSION}\"/" docs/conf.py
	sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/" kube_web/__init__.py
	sed -i "s/v=[0-9A-Za-z._-]*/v=${VERSION}/g" kube_web/templates/base.html
