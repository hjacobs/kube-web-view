import pykube
from .resource_registry import ResourceRegistry


class Cluster:
    def __init__(self, name: str, api):
        self.name = name
        self.api = api
        self.resource_registry = ResourceRegistry(api)


class ClusterNotFound(Exception):
    def __init__(self, cluster):
        self.cluster = cluster


class ClusterManager:
    def __init__(self, kubeconfig_path):
        self._clusters = {}

        # TODO: reload config, e.g. when kubeconfig changed
        try:
            api = pykube.HTTPClient(pykube.KubeConfig.from_service_account())
            cluster = Cluster("local", api)
            self._clusters[cluster.name] = cluster
        except:
            kubeconfig = pykube.KubeConfig.from_file(kubeconfig_path)

            for context in kubeconfig.contexts:
                # create a new KubeConfig with new "current context"
                context_config = pykube.KubeConfig(kubeconfig.doc, context)
                api = pykube.HTTPClient(context_config)
                cluster = Cluster(context, api)
                self._clusters[cluster.name] = cluster

    @property
    def clusters(self):
        return list(self._clusters.values())

    def get(self, cluster: str):
        obj = self._clusters.get(cluster)
        if not obj:
            raise ClusterNotFound(cluster)
        return obj
