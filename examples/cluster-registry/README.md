# Example Cluster Registry

```
docker build -t cluster-registry .
docker run -it -p 8081:8081 cluster-registry
curl http://localhost:8081/kubernetes-clusters
```
