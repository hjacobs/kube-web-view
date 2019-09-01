from .resource_registry import ResourceRegistry
from .selector import selector_matches

from .cluster_discovery import OAuth2BearerTokenAuth

from pathlib import Path


class Cluster:
    def __init__(self, name: str, api, labels: dict, preferred_api_versions: dict):
        self.name = name
        self.api = api
        self.labels = labels or {}
        self.resource_registry = ResourceRegistry(api, preferred_api_versions)


class ClusterNotFound(Exception):
    def __init__(self, cluster):
        self.cluster = cluster


class ClusterManager:
    def __init__(
        self,
        discoverer,
        selector: dict,
        cluster_auth_token_path: Path,
        preferred_api_versions: dict,
    ):
        self._clusters = {}
        self.discoverer = discoverer
        self.selector = selector
        self.cluster_auth_token_path = cluster_auth_token_path
        self.preferred_api_versions = preferred_api_versions
        self.reload()

    def reload(self):
        _clusters = {}
        for cluster in self.discoverer.get_clusters():
            if selector_matches(self.selector, cluster.labels):
                if self.cluster_auth_token_path:
                    # overwrite auth mechanism with dynamic access token (loaded from file)
                    cluster.api.session.auth = OAuth2BearerTokenAuth(
                        self.cluster_auth_token_path
                    )
                _clusters[cluster.name] = Cluster(
                    cluster.name,
                    cluster.api,
                    cluster.labels,
                    self.preferred_api_versions,
                )

        self._clusters = _clusters

    @property
    def clusters(self):
        return list(self._clusters.values())

    def get(self, cluster: str):
        obj = self._clusters.get(cluster)
        if not obj:
            raise ClusterNotFound(cluster)
        return obj
