import yaml

from .utils import check_links


def test_view_namespace(session):
    response = session.get("/clusters/local/namespaces/default")
    response.raise_for_status()
    title = response.html.find("title", first=True)
    assert title.text == "default (Namespace) - Kubernetes Web View"


def test_view_namespace_trailing_slash(session):
    response = session.get("/clusters/local/namespaces/default/")
    response.raise_for_status()
    title = response.html.find("title", first=True)
    assert title.text == "default (Namespace) - Kubernetes Web View"


def test_view_namespace_forbidden(session):
    response = session.get("/clusters/local/namespaces/my-forbidden-namespace")
    assert response.status_code == 403


def test_view_namespaced_resource(session):
    response = session.get(
        "/clusters/local/namespaces/default/deployments/kube-web-view"
    )
    response.raise_for_status()
    assert "application=kube-web-view" in response.text

    response = session.get("/clusters/local/namespaces/default/services/kube-web-view")
    response.raise_for_status()
    assert "ClusterIP" in response.text


def test_view_namespaced_resource_forbidden(session):
    response = session.get(
        "/clusters/local/namespaces/my-forbidden-namespace/deployments/kube-web-view"
    )
    assert response.status_code == 403


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


def test_node_shows_pods(session):
    response = session.get("/clusters/local/nodes/kube-web-view-e2e-control-plane")
    response.raise_for_status()
    links = response.html.find("main table a")
    # check that our kube-web-view pod (dynamic name) is linked from the node page
    assert "/clusters/local/namespaces/default/pods/kube-web-view-" in " ".join(
        l.attrs["href"] for l in links
    )


def test_owner_links(session):
    response = session.get(
        "/clusters/local/namespaces/default/pods?selector=application=kube-web-view"
    )
    response.raise_for_status()
    pod_link = response.html.find("main table td a", first=True)
    url = pod_link.attrs["href"]
    assert url.startswith("/clusters/local/namespaces/default/pods/kube-web-view-")
    response = session.get(url)
    response.raise_for_status()
    check_links(response, session)

    links = response.html.find("main a")
    found_link = None
    for link in links:
        if link.text.endswith(" (ReplicaSet)"):
            found_link = link
            break
    assert found_link is not None
    assert found_link.attrs["href"].startswith(
        "/clusters/local/namespaces/default/replicasets/kube-web-view-"
    )


def test_object_links(session):
    response = session.get(
        "/clusters/local/namespaces/default/pods?selector=application=kube-web-view"
    )
    response.raise_for_status()
    pod_link = response.html.find("main table td a", first=True)
    url = pod_link.attrs["href"]
    assert url.startswith("/clusters/local/namespaces/default/pods/kube-web-view-")
    response = session.get(url)
    response.raise_for_status()
    check_links(response, session)

    link = response.html.find("main h1 a.is-primary", first=True)
    assert link.attrs["href"].startswith(
        "#cluster=local;namespace=default;name=kube-web-view-"
    )


def test_link_added_by_prerender_hook(session):
    response = session.get("/clusters/local/namespaces/default/deployments/kube-web-view")
    response.raise_for_status()
    check_links(response, session)

    link = response.html.find("main h1 a.is-link", first=True)
    assert link.attrs["href"].startswith(
        "#this-is-a-custom-link"
    )
