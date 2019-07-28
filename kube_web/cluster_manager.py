import pykube
from .resource_registry import ResourceRegistry


class Cluster:
    def __init__(self, name: str, api):
        self.name = name
        self.api = api
        self.resource_registry = ResourceRegistry(api)


class ClusterManager:
    def __init__(self, kubeconfig_path):
        self._clusters = {}

        try:
            api = pykube.HTTPClient(pykube.KubeConfig.from_service_account())
            cluster = Cluster("local", api)
        except:
            kubeconfig = pykube.KubeConfig.from_file(kubeconfig_path)
            api = pykube.HTTPClient(kubeconfig)
            cluster = Cluster(kubeconfig.current_context, api)

        self._clusters[cluster.name] = cluster

    @property
    def clusters(self):
        return list(self._clusters.values())

    def get(self, cluster: str):
        return self._clusters.get(cluster)
