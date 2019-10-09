# Kubernetes Web View

[![Build Status](https://travis-ci.com/hjacobs/kube-web-view.svg?branch=master)](https://travis-ci.com/hjacobs/kube-web-view)
[![Documentation Status](https://readthedocs.org/projects/kube-web-view/badge/?version=latest)](https://kube-web-view.readthedocs.io/en/latest/?badge=latest)
![GitHub tag (latest SemVer)](https://img.shields.io/github/tag/hjacobs/kube-web-view)
![Docker Pulls](https://img.shields.io/docker/pulls/hjacobs/kube-web-view.svg)
![License](https://img.shields.io/github/license/hjacobs/kube-web-view)
![CalVer](https://img.shields.io/badge/calver-YY.MM.MICRO-22bfda.svg)

Kubernetes Web View allows to list and view all Kubernetes resources (incl. CRDs) with permalink-friendly URLs in a plain-HTML frontend.
This tool was mainly developed to provide a web-version of `kubectl` for troubleshooting and supporting colleagues.
See the [Kubernetes Web View Documentation](https://kube-web-view.readthedocs.io/) and [try out the live demo](https://kube-web-view.demo.j-serv.de/).

Goals:

* handling of any API resource: both core Kubernetes and CRDs
* permalink-friendly URL paths for giving links to colleagues (e.g. to help troubleshoot)
* option to work with multiple clusters
* allow listing different resource types on the same page (e.g. deployments and CRDs with same label)
* replicate some of the common `kubectl` features, e.g. `-l` (label selector) and `-L` (label columns)
* simple HTML, only add JavaScript where it adds value
* pluggable links, e.g. to link to other tools based on resource properties like labels (monitoring, reports, ..)
* optional: editing resources as YAML manifests (`kubectl edit`)

Non-goals:

* application management
* reporting/visualization
* fancy UI (JS/SPA)

## Quickstart

This will run Kubernetes Web View locally with your existing Kubeconfig:

```
docker run -it -p 8080:8080 -u $(id -u) -v $HOME/.kube:/.kube hjacobs/kube-web-view
```

Open http://localhost:8080/ in your browser to see the UI.

## Deploying into your cluster

This will deploy a single Pod with Kubernetes Web View into your cluster:

```
kubectl apply -f deploy/
kubectl port-forward service/kube-web-view 8080:80
```

Open http://localhost:8080/ in your browser to see the UI.


## Running tests

This requires Python 3.7 and [poetry](https://poetry.eustace.io/) and will run unit tests and end-to-end tests with [Kind](https://github.com/kubernetes-sigs/kind):

```
make test
```

It is also possible to run static and unit tests in docker env (`make test` is equal to `make poetry lint test.unit docker`)

```
docker run -it -v $PWD:/src -w /src python:3.7 /bin/bash -c "pip3 install poetry; make poetry lint test.unit"
make docker
```

The end-to-end (e2e) tests will bootstrap a new Kind cluster via [pytest-kind](https://pypi.org/project/pytest-kind/), you can keep the cluster and run Kubernetes Web View for development against it:

```
PYTEST_ADDOPTS=--keep-cluster make test
make run.kind
```


## Building the Docker image

```
make
```


## Developing Locally

To start the Python web server locally with the default kubeconfig (`~/.kube/config`):

```
make run
```
