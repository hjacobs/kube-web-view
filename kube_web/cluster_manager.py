from .resource_registry import ResourceRegistry


class Cluster:
    def __init__(self, name: str, api):
        self.name = name
        self.api = api
        self.resource_registry = ResourceRegistry(api)


class ClusterManager:
    def __init__(self):
        pass

    def get(self, cluster: str):
        api = None
        return Cluster(cluster, api)
