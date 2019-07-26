FROM python:3.7-alpine3.10

WORKDIR /

RUN pip3 install poetry

COPY poetry.lock /
COPY pyproject.toml /

RUN apk update && \
    apk add python3-dev gcc musl-dev zlib-dev libffi-dev openssl-dev && \
    poetry config settings.virtualenvs.create false && \
    poetry install --no-interaction --no-dev --no-ansi && \
    rm -fr /usr/local/lib/python3.7/site-packages/pip && \
    rm -fr /usr/local/lib/python3.7/site-packages/setuptools && \
    apk del python3-dev gcc musl-dev zlib-dev libffi-dev openssl-dev && \
    rm -rf /var/cache/apk/* /root/.cache /tmp/* 

FROM python:3.7-alpine3.10

WORKDIR /

COPY --from=0 /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages

COPY kube_web /kube_web

ARG VERSION=dev
RUN sed -i "s/__version__ = .*/__version__ = '${VERSION}'/" /kube_web/__init__.py

ENTRYPOINT ["/usr/local/bin/python", "-m", "kube_web"]
