import time
import requests


def test_list_clusters(session):
    response = session.get("/clusters")
    response.raise_for_status()
    assert "/clusters/local" in response.text


def test_list_cluster_resource_type_not_found(session):
    response = session.get("/clusters/local/foobars")
    assert response.status_code == 404
    assert "Resource type not found" in response.text


def test_list_cluster_resources(session):
    response = session.get("/clusters/local/nodes")
    response.raise_for_status()
    title = response.html.find('h1', first=True)
    assert title.text == 'Nodes'
    assert "/clusters/local/nodes/kube-web-view-e2e-control-plane" in response.text


def test_list_cluster_resources_in_all_clusters(session):
    response = session.get("/clusters/_all/nodes")
    response.raise_for_status()
    assert "/clusters/local/nodes/kube-web-view-e2e-control-plane" in response.text


def test_list_namespaced_resources(session):
    response = session.get("/clusters/local/namespaces/default/deployments")
    response.raise_for_status()
    assert "application=kube-web-view" in response.text
    assert "kube-web-view-container" in response.text


def test_list_multiple_namespaced_resources(session):
    response = session.get(
        "/clusters/local/namespaces/default/deployments,services"
    )
    response.raise_for_status()
    assert "application=kube-web-view" in response.text
    assert "kube-web-view-container" in response.text
    assert "ClusterIP" in response.text


def test_download_nodes_tsv(session):
    response = session.get("/clusters/local/nodes?download=tsv")
    response.raise_for_status()
    lines = response.text.split("\n")
    assert lines[0].startswith("Name")
    assert lines[1].startswith("kube-web-view")


def test_download_tsv(session):
    response = session.get(
        "/clusters/local/namespaces/default/deployments?download=tsv"
    )
    response.raise_for_status()
    lines = response.text.split("\n")
    assert lines[0].startswith("Namespace")
    assert lines[1].startswith("default\tkube-web-view")


def test_list_resources_in_all_namespaces(session):
    response = session.get("/clusters/local/namespaces/_all/deployments")
    response.raise_for_status()
    assert "application=kube-web-view" in response.text
    # deployments in kube-system are also listed:
    assert "/namespaces/kube-system/deployments/coredns" in response.text


def test_list_resources_in_all_clusters(session):
    response = session.get("/clusters/_all/namespaces/default/deployments")
    response.raise_for_status()
    assert "application=kube-web-view" in response.text


def test_list_pods_wrong_container_image(session):
    for i in range(10):
        response = session.get(
            "/clusters/local/namespaces/default/pods?selector=e2e=wrong-container-image"
        )
        response.raise_for_status()
        if "ImagePullBackOff" in response.text or "ErrImagePull" in response.text:
            break
        else:
            time.sleep(1)
    assert "ImagePullBackOff" in response.text or "ErrImagePull" in response.text
    assert "has-text-danger" in response.text


def test_cluster_resource_types(session):
    response = session.get("/clusters/local/_resource-types")
    response.raise_for_status()
    assert "APIService" in response.text
    assert "CustomResourceDefinition" in response.text


def test_namespaced_resource_types(session):
    response = session.get("/clusters/local/namespaces/default/_resource-types")
    response.raise_for_status()
    assert "PersistentVolumeClaim" in response.text


def test_label_columns(session):
    response = session.get(
        "/clusters/local/namespaces/default/pods?labelcols=my-pod-label"
    )
    response.raise_for_status()
    assert "my-pod-label-value" in response.text


def test_download_sort_link(session):
    response = session.get("/clusters/local/namespaces/default/pods?sort=Status")
    response.raise_for_status()
    assert "?download=tsv&sort=Status" in response.text
