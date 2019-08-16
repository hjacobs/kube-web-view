FROM python:3.7-alpine3.10

WORKDIR /

RUN pip3 install aiohttp

COPY cluster-registry.py /

ENTRYPOINT ["/usr/local/bin/python", "/cluster-registry.py"]
