import requests


def test_view_namespaced_resource(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(
        f"{url}/clusters/local/namespaces/default/deployments/kube-web-view"
    )
    response.raise_for_status()
    assert "application=kube-web-view" in response.text

    response = requests.get(
        f"{url}/clusters/local/namespaces/default/services/kube-web-view"
    )
    response.raise_for_status()
    assert "ClusterIP" in response.text
