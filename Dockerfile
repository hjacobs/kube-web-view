FROM python:3.8-slim

WORKDIR /

RUN pip3 install poetry

COPY poetry.lock /
COPY pyproject.toml /

# fake package to make Poetry happy (we will install the actual contents in the later stage)
RUN mkdir /kube_web && touch /kube_web/__init__.py && touch /README.md

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-dev --no-ansi

FROM python:3.8-slim

WORKDIR /

# copy pre-built packages to this image
COPY --from=0 /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

# now copy the actual code we will execute (poetry install above was just for dependencies)
COPY kube_web /kube_web

ARG VERSION=dev

# replace build version in package and
# add build version to static asset links to break browser cache
# see also "version" in Makefile
RUN sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/" /kube_web/__init__.py && \
    sed -i "s/v=[0-9A-Za-z._-]*/v=${VERSION}/g" /kube_web/templates/base.html

ENTRYPOINT ["/usr/local/bin/python", "-m", "kube_web"]
