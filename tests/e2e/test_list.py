import time

from .utils import check_links


def test_list_clusters(session):
    response = session.get("/clusters")
    response.raise_for_status()
    assert "/clusters/local" in response.text


def test_list_clusters_filter(session):
    response = session.get("/clusters?filter=no-such-cluster")
    response.raise_for_status()
    assert "/clusters/local" not in response.text
    assert "No clusters found." in response.text


def test_list_cluster_resource_type_not_found(session):
    response = session.get("/clusters/local/foobars")
    assert response.status_code == 404
    assert (
        "Cluster resource type 'foobars' not found"
        in response.html.find("main", first=True).text
    )


def test_list_cluster_resources(session):
    response = session.get("/clusters/local/nodes")
    response.raise_for_status()
    check_links(response, session)
    title = response.html.find("h1", first=True)
    assert title.text == "Nodes"
    assert "/clusters/local/nodes/kube-web-view-e2e-control-plane" in response.text


def test_list_node_metrics(session):
    response = session.get("/clusters/local/nodes?join=metrics")
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table th")
    assert ths[-3].text == "CPU Usage"
    assert ths[-2].text == "Memory Usage"


def test_list_cluster_resources_in_all_clusters(session):
    response = session.get("/clusters/_all/nodes")
    response.raise_for_status()
    check_links(response, session)
    assert "/clusters/local/nodes/kube-web-view-e2e-control-plane" in response.text


def test_list_cluster_resources_in_multiple_clusters(session):
    # fake multiple clusters by specifying the same cluster twice..
    # this is a bit fake as we only have one cluster in e2e..
    response = session.get("/clusters/local,local/nodes")
    response.raise_for_status()
    # TODO: fix broken link and remove the ignore option
    check_links(response, session, ignore=["/clusters/local,local"])
    first_col_heading = response.html.find("main th", first=True)
    assert first_col_heading.text == "Cluster"
    assert "/clusters/local/nodes/kube-web-view-e2e-control-plane" in response.text


def test_list_namespaced_resources(session):
    response = session.get("/clusters/local/namespaces/default/deployments")
    response.raise_for_status()
    check_links(response, session)
    assert "application=kube-web-view" in response.text
    assert "kube-web-view-container" in response.text


def test_list_pods_with_node_links(session):
    response = session.get("/clusters/local/namespaces/default/pods")
    response.raise_for_status()
    check_links(response, session)
    links = response.html.find("html table td a")
    assert (
        "/clusters/local/nodes/kube-web-view-e2e-control-plane"
        == links[1].attrs["href"]
    )


def test_list_pods_with_metrics(session):
    response = session.get("/clusters/local/namespaces/default/pods?join=metrics")
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table th")
    # note: pods have an extra "Links" column (--object-links)
    assert ths[-4].text == "CPU Usage"
    assert ths[-3].text == "Memory Usage"


def test_list_namespaced_resource_type_not_found(session):
    response = session.get("/clusters/local/namespaces/default/foobars")
    assert response.status_code == 404
    assert (
        "Namespaced resource type 'foobars' not found"
        in response.html.find("main", first=True).text
    )


def test_list_namespaced_resources_in_all_clusters(session):
    response = session.get("/clusters/_all/namespaces/_all/deployments")
    response.raise_for_status()
    assert (
        "/clusters/local/namespaces/default/deployments/kube-web-view" in response.text
    )


def test_list_multiple_namespaced_resources(session):
    response = session.get("/clusters/local/namespaces/default/deployments,services")
    response.raise_for_status()
    check_links(response, session)
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
        "/clusters/local/namespaces/default/deployments?download=tsv&selector=application=kube-web-view"
    )
    response.raise_for_status()
    lines = response.text.split("\n")
    assert lines[0].startswith("Namespace")
    assert lines[1].startswith("default\tkube-web-view")


def test_download_tsv_for_multiple_clusters(session):
    # this is a bit fake as we only have one e2e cluster..
    response = session.get(
        "/clusters/local,local/namespaces/default/deployments?download=tsv&selector=application=kube-web-view"
    )
    response.raise_for_status()
    lines = response.text.split("\n")
    # the TSV should have a "Cluster" column for multi-cluster TSV
    assert lines[0].startswith("Cluster")
    assert lines[1].startswith("local\tdefault\tkube-web-view")


def test_list_resources_in_all_namespaces(session):
    response = session.get("/clusters/local/namespaces/_all/deployments")
    response.raise_for_status()
    check_links(response, session)
    assert "application=kube-web-view" in response.text
    # deployments in kube-system are also listed:
    assert "/namespaces/kube-system/deployments/coredns" in response.text


def test_list_resources_in_all_clusters(session):
    response = session.get("/clusters/_all/namespaces/default/deployments")
    response.raise_for_status()
    # TODO: fix the broken link and remove the ignore
    check_links(response, session, ignore=["/clusters/_all/namespaces/default"])
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


def test_list_pods_filter_status_notequal(session):
    response = session.get(
        "/clusters/local/namespaces/default/pods?filter=Status!=Running"
    )
    response.raise_for_status()
    check_links(response, session)
    links = response.html.find("html table td a")
    assert "/clusters/local/namespaces/default/pods/wrong-container-image-" in " ".join(
        l.attrs["href"] for l in links
    )


def test_cluster_resource_types(session):
    response = session.get("/clusters/local/_resource-types")
    response.raise_for_status()
    check_links(response, session)
    assert "APIService" in response.text
    assert "CustomResourceDefinition" in response.text


def test_namespaced_resource_types(session):
    response = session.get("/clusters/local/namespaces/default/_resource-types")
    response.raise_for_status()
    check_links(response, session)
    assert "PersistentVolumeClaim" in response.text


def test_label_columns(session):
    response = session.get(
        "/clusters/local/namespaces/default/pods?labelcols=my-pod-label"
    )
    response.raise_for_status()
    check_links(response, session)
    assert "my-pod-label-value" in response.text


def test_download_sort_link(session):
    response = session.get("/clusters/local/namespaces/default/pods?sort=Status")
    response.raise_for_status()
    link = response.html.find("h1 a", first=True)
    assert (
        "/clusters/local/namespaces/default/pods?sort=Status&download=tsv"
        == link.attrs["href"]
    )


def test_object_links(session):
    response = session.get("/clusters/local/namespaces/default/pods")
    response.raise_for_status()
    link = response.html.find("main table a.button", first=True)
    assert link.attrs["href"].startswith("#cluster=local;namespace=default;name=")
