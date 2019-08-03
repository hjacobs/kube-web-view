import yaml


def test_view_namespaced_resource(session):
    response = session.get(
        "/clusters/local/namespaces/default/deployments/kube-web-view"
    )
    response.raise_for_status()
    assert "application=kube-web-view" in response.text

    response = session.get("/clusters/local/namespaces/default/services/kube-web-view")
    response.raise_for_status()
    assert "ClusterIP" in response.text


def test_cluster_not_found(session):
    response = session.get(
        "/clusters/no-such-cluster/namespaces/default/deployments/kube-web-view"
    )
    assert response.status_code == 404
    assert "cluster not found" in response.text


def test_object_not_found(session):
    response = session.get(
        "/clusters/local/namespaces/default/deployments/no-such-deploy"
    )
    assert response.status_code == 404
    assert "object does not exist" in response.text


def test_logs(session):
    response = session.get(
        "/clusters/local/namespaces/default/deployments/kube-web-view",
        headers={"User-Agent": "TEST-LOGS-USER-AGENT"},
    )
    response.raise_for_status()
    response = session.get(
        "/clusters/local/namespaces/default/deployments/kube-web-view/logs"
    )
    response.raise_for_status()
    assert "TEST-LOGS-USER-AGENT" in response.text


def test_hide_secret_contents(session):
    response = session.get("/clusters/local/namespaces/default/secrets/test-secret")
    response.raise_for_status()
    # echo 'secret-content' | base64
    assert "c2VjcmV0LWNvbnRlbnQK" not in response.text
    assert "**SECRET-CONTENT-HIDDEN-BY-KUBE-WEB-VIEW**" in response.text


def test_download_yaml(session):
    response = session.get(
        "/clusters/local/namespaces/default/deployments/kube-web-view?download=yaml"
    )
    response.raise_for_status()
    data = yaml.safe_load(response.text)
    assert data["kind"] == "Deployment"
    assert data["metadata"]["name"] == "kube-web-view"


def test_download_secret_yaml(session):
    response = session.get(
        "/clusters/local/namespaces/default/secrets/test-secret?download=yaml"
    )
    response.raise_for_status()
    data = yaml.safe_load(response.text)
    assert data["kind"] == "Secret"
    assert data["metadata"]["name"] == "test-secret"
    assert data["data"]["my-secret-key"] == "**SECRET-CONTENT-HIDDEN-BY-KUBE-WEB-VIEW**"
