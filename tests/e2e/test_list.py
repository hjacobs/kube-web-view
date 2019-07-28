import requests


def test_list_namespaced_resources(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(f"{url}/clusters/local/namespaces/default/deployments")
    response.raise_for_status()
    assert "application=kube-web-view" in response.text
    assert "kube-web-view-container" in response.text
