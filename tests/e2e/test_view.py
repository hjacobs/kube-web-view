import requests


def test_view(populated_cluster):
    proxy_url = populated_cluster["proxy_url"]
    response = requests.get(
        f"{proxy_url}/api/v1/namespaces/default/services/kube-web-view/proxy/clusters/default/namespaces/default/deployments/kube-web-view"
    )
    response.raise_for_status()
    assert "application=kube-web-view" in response.text
