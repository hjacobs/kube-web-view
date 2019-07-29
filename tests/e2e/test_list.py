import requests


def test_list_namespaced_resources(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(f"{url}/clusters/local/namespaces/default/deployments")
    response.raise_for_status()
    assert "application=kube-web-view" in response.text
    assert "kube-web-view-container" in response.text


def test_list_multple_namespaced_resources(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(
        f"{url}/clusters/local/namespaces/default/deployments,services"
    )
    response.raise_for_status()
    assert "application=kube-web-view" in response.text
    assert "kube-web-view-container" in response.text
    assert "ClusterIP" in response.text


def test_download_tsv(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(
        f"{url}/clusters/local/namespaces/default/deployments?download=tsv"
    )
    response.raise_for_status()
    lines = response.text.split("\n")
    assert lines[0].startswith("Namespace")
    assert lines[1].startswith("default\tkube-web-view")
