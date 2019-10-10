import logging
import time
from os import environ
from pathlib import Path
from urllib.parse import urljoin

import requests
from box import Box
from pykube import HTTPClient, KubeConfig
from requests.auth import AuthBase


class OAuth2BearerTokenAuth(AuthBase):
    """Dynamic authentication loading OAuth Bearer token from file
    (potentially mounted from a Kubernetes secret)"""

    def __init__(self, token_path: Path):
        self.token_path = token_path

    def __call__(self, request):
        if "Authorization" in request.headers:
            # do not overwrite any existing Authorization header
            return request

        token = environ.get('oauth_token')
        if not token:
            with self.token_path.open() as fd:
                token = fd.read().strip()
        request.headers["Authorization"] = f"Bearer {token}"
        return request


class Cluster:
    def __init__(self, name: str, api: HTTPClient, labels: dict = None, config: dict = None):
        self.name = name
        self.api = api
        self.labels = labels or {}
        self.config = config or {}


class StaticClusterDiscoverer:
    def __init__(self, clusters: dict):
        self._clusters = []

        for cluster_name, url in clusters.items():
            config = KubeConfig.from_url(url)
            client = HTTPClient(config)
            cluster = Cluster(cluster_name, client)
            self._clusters.append(cluster)

    def get_clusters(self):
        return self._clusters


class ServiceAccountNotFound(Exception):
    pass


class ServiceAccountClusterDiscoverer:
    def __init__(self):
        self._clusters = []

        try:
            config = KubeConfig.from_service_account()
        except FileNotFoundError:
            # we are not running inside a cluster
            raise ServiceAccountNotFound()

        client = HTTPClient(config)
        cluster = Cluster("local", client)
        self._clusters.append(cluster)

    def get_clusters(self):
        return self._clusters


class ClusterRegistryDiscoverer:
    def __init__(
        self,
        cluster_registry_url: str,
        oauth2_bearer_token_path: Path,
        label_keys: list,
        config_keys: list,
        cache_lifetime=60,
    ):
        self._url = cluster_registry_url
        self._oauth2_bearer_token_path = oauth2_bearer_token_path
        self._label_keys = label_keys
        self._config_keys = config_keys
        self._cache_lifetime = cache_lifetime
        self._last_cache_refresh = 0
        self._clusters = []
        self._session = requests.Session()
        if self._oauth2_bearer_token_path:
            self._session.auth = OAuth2BearerTokenAuth(self._oauth2_bearer_token_path)

    def refresh(self):
        try:
            response = self._session.get(
                urljoin(self._url, "/kubernetes-clusters"), timeout=10
            )
            response.raise_for_status()
            clusters = []
            for row in response.json()["items"]:
                # only consider "ready" clusters
                if row.get("lifecycle_status", "ready") == "ready":
                    config = KubeConfig.from_url(row["api_server_url"])
                    client = HTTPClient(config)
                    client.session.auth = OAuth2BearerTokenAuth(
                        self._oauth2_bearer_token_path
                    )

                    def parse_map(keys: list):
                        result = {}
                        if keys:
                            box = Box(row)
                            for key in keys:
                                try:
                                    result[key.replace("_", "-").split('.')[-1]] = eval(f'box.{key}', {'box': box})
                                except KeyError:
                                    pass

                        return result

                    clusters.append(Cluster(row["alias"], client,
                                            parse_map(self._label_keys), parse_map(self._config_keys)))
            self._clusters = clusters
            self._last_cache_refresh = time.time()
        except:
            logger.exception(f"Failed to refresh from cluster registry {self._url}")

    def get_clusters(self):
        now = time.time()
        if now - self._last_cache_refresh > self._cache_lifetime:
            self.refresh()
        return self._clusters


class KubeconfigDiscoverer:
    def __init__(self, kubeconfig_path: Path, contexts: set):
        self._path = kubeconfig_path
        self._contexts = contexts

    def get_clusters(self):
        # Kubernetes Python client expects "vintage" string path
        config_file = str(self._path) if self._path else None
        config = KubeConfig.from_file(config_file)
        for context in config.contexts:
            if self._contexts and context not in self._contexts:
                # filter out
                continue
            # create a new KubeConfig with new "current context"
            context_config = KubeConfig(config.doc, context)
            client = HTTPClient(context_config)
            cluster = Cluster(context, client)
            yield cluster


class MockDiscoverer:
    def get_clusters(self):
        for i in range(3):
            yield Cluster(f"mock-cluster-{i}", client=None)
