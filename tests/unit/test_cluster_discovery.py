from pathlib import Path
from kube_web.cluster_discovery import KubeconfigDiscoverer


def test_load_kubeconfig_wrong_ca_path(tmpdir):
    """
    Test that a wrong ca path will skip the context
    """
    path = Path(str(tmpdir)) / "test.yaml"
    with path.open("w") as fd:
        fd.write(
            """
contexts:
 - context:
     cluster: testcluster
     user: testuser
   name: test
 - context:
     cluster: testcluster2
     user: testuser
   name: test2
clusters:
 - name: testcluster2
   cluster:
     server: https://localhost:999
 - name: testcluster
   cluster:
     server: https://localhost:999
     certificate-authority: /non/existing/path/ca.crt
        """
        )
    discoverer = KubeconfigDiscoverer(path)
    clusters = list(discoverer.get_clusters())
    assert len(clusters) == 1
    assert clusters[0].name == "test2"
