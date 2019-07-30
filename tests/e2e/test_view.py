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


def test_cluster_not_found(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(
        f"{url}/clusters/no-such-cluster/namespaces/default/deployments/kube-web-view"
    )
    assert response.status_code == 404
    assert "cluster not found" in response.text


def test_object_not_found(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(
        f"{url}/clusters/local/namespaces/default/deployments/no-such-deploy"
    )
    assert response.status_code == 404
    assert "object does not exist" in response.text


def test_logs(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(
        f"{url}/clusters/local/namespaces/default/deployments/kube-web-view",
        headers={'User-Agent': 'TEST-LOGS-USER-AGENT'}
    )
    response.raise_for_status()
    response = requests.get(
        f"{url}/clusters/local/namespaces/default/deployments/kube-web-view/logs"
    )
    response.raise_for_status()
    assert "TEST-LOGS-USER-AGENT" in response.text
