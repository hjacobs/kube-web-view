import re
from pathlib import Path
from typing import Dict
from typing import List

from .cluster_discovery import OAuth2BearerTokenAuth
from .resource_registry import ResourceRegistry
from .selector import selector_matches

INVALID_CLUSTER_NAME_CHAR_PATTERN = re.compile("[^a-zA-Z0-9:_.-]")


def sanitize_cluster_name(name: str):
    """Replace all invalid characters with a colon (":")."""
    return INVALID_CLUSTER_NAME_CHAR_PATTERN.sub(":", name)


class Cluster:
    def __init__(
        self, name: str, api, labels: dict, spec: dict, preferred_api_versions: dict
    ):
        self.name = name
        self.api = api
        self.labels = labels or {}
        self.spec = spec or {}
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
        self._clusters: Dict[str, Cluster] = {}
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
                # the cluster name might contain invalid characters,
                # e.g. KubeConfig context names can contain slashes
                sanitized_name = sanitize_cluster_name(cluster.name)
                _clusters[sanitized_name] = Cluster(
                    sanitized_name,
                    cluster.api,
                    cluster.labels,
                    cluster.spec,
                    self.preferred_api_versions,
                )

        self._clusters = _clusters

    @property
    def clusters(self) -> List[Cluster]:
        self.reload()
        return list(self._clusters.values())

    def get(self, cluster: str) -> Cluster:
        obj = self._clusters.get(cluster)
        if not obj:
            raise ClusterNotFound(cluster)
        return obj
