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


def test_list_namespaces(session):
    response = session.get("/clusters/local/namespaces")
    response.raise_for_status()
    check_links(response, session)
    namespace_urls = list(
        a.attrs["href"] for a in response.html.find("main table td a")
    )
    assert "/clusters/local/namespaces/default" in namespace_urls
    # we excluded the forbidden namespace via --exclude-namespaces
    assert "/clusters/local/namespaces/my-forbidden-namespace" not in namespace_urls


def test_list_namespaced_resources(session):
    response = session.get("/clusters/local/namespaces/default/deployments")
    response.raise_for_status()
    check_links(response, session)
    assert "application=kube-web-view" in response.text
    assert "kube-web-view-container" in response.text


def test_list_namespaced_resources_forbidden(session):
    response = session.get(
        "/clusters/local/namespaces/my-forbidden-namespace/deployments"
    )
    assert response.status_code == 403


def test_list_namespaced_resources_filter_out_forbidden(session):
    response = session.get("/clusters/local/namespaces/_all/deployments")
    response.raise_for_status()
    deployment_urls = list(
        a.attrs["href"] for a in response.html.find("main table td a")
    )
    assert (
        "/clusters/local/namespaces/default/deployments/kube-web-view"
        in deployment_urls
    )
    # we excluded the forbidden namespace via --exclude-namespaces
    assert (
        "/clusters/local/namespaces/my-forbidden-namespace/deployment-in-forbbiden-ns"
        not in deployment_urls
    )


def test_list_pods_with_node_links(session):
    response = session.get("/clusters/local/namespaces/default/pods")
    response.raise_for_status()
    check_links(response, session)
    links = response.html.find("html table td a")
    assert (
        "/clusters/local/nodes/kube-web-view-e2e-control-plane"
        == links[1].attrs["href"]
    )


def test_list_pods_with_limit(session):
    response = session.get("/clusters/local/namespaces/default/pods")
    response.raise_for_status()
    check_links(response, session)
    rows = response.html.find("table tbody tr")
    # verify that we actually have more than one pod in total
    assert len(rows) > 1

    response = session.get("/clusters/local/namespaces/default/pods?limit=1")
    response.raise_for_status()
    check_links(response, session)
    rows = response.html.find("table tbody tr")
    # check that the "limit" parameter works
    assert len(rows) == 1


def test_list_pods_with_metrics(session):
    response = session.get("/clusters/local/namespaces/default/pods?join=metrics")
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table th")
    # note: pods have an extra "Links" column (--object-links)
    assert ths[-4].text == "CPU Usage"
    assert ths[-3].text == "Memory Usage"


def test_list_pods_with_custom_columns(session):
    response = session.get(
        "/clusters/local/namespaces/default/pods?customcols=Images=spec.containers[*].image"
    )
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table thead th")
    # note: pods have an extra "Links" column (--object-links)
    assert ths[-3].text == "Images"

    rows = response.html.find("main table tbody tr")
    for row in rows:
        cells = row.find("td")
        assert cells[-3].text.startswith("['hjacobs/")


def test_list_pods_with_custom_column_auto_name(session):
    response = session.get(
        "/clusters/local/namespaces/default/pods?customcols=spec.containers[*].image"
    )
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table thead th")
    # note: pods have an extra "Links" column (--object-links)
    assert ths[-3].text == "Spec Containers Image"

    rows = response.html.find("main table tbody tr")
    for row in rows:
        cells = row.find("td")
        assert cells[-3].text.startswith("['hjacobs/")


def test_list_pods_with_multiple_custom_columns(session):
    # note that the semicolon must be urlencoded as %3B!
    response = session.get(
        "/clusters/local/namespaces/_all/deployments?customcols=A=metadata.namespace%3BB=metadata.name"
    )
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table thead th")
    assert ths[-3].text == "A"
    assert ths[-2].text == "B"

    rows = response.html.find("main table tbody tr")
    for row in rows:
        cells = row.find("td")
        # namespace
        assert cells[-3].text == cells[0].text
        # name
        assert cells[-2].text == cells[1].text


def test_list_secrets_with_custom_columns(session):
    response = session.get(
        "/clusters/local/namespaces/_all/secrets?customcols=Data=data"
    )
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table thead th")
    assert ths[-2].text == "Data"

    rows = response.html.find("main table tbody tr")
    for row in rows:
        cells = row.find("td")
        # make sure that we cannot extract secret data via custom columns
        assert cells[-2].text == "**SECRET-CONTENT-HIDDEN-BY-KUBE-WEB-VIEW**"


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


def test_hide_columns(session):
    response = session.get("/clusters/local/namespaces/default/deployments")
    response.raise_for_status()
    ths = response.html.find("main table thead th")
    assert len(ths) == 9
    assert ths[5].text == "Containers"
    assert ths[6].text == "Images"

    response = session.get(
        "/clusters/local/namespaces/default/deployments?hidecols=Containers,Images"
    )
    response.raise_for_status()
    ths = response.html.find("main table thead th")
    assert len(ths) == 7
    assert ths[5].text == "Selector"
    assert ths[6].text == "Created"


def test_filter_pods_with_custom_columns(session):
    """
    Test that filtering on custom columns works
    """
    response = session.get(
        "/clusters/local/namespaces/default/pods?customcols=Images=spec.containers[*].image&filter=hjacobs/"
    )
    response.raise_for_status()
    check_links(response, session)
    ths = response.html.find("main table thead th")
    # note: pods have an extra "Links" column (--object-links)
    assert ths[-3].text == "Images"

    rows = response.html.find("main table tbody tr")
    for row in rows:
        cells = row.find("td")
        assert cells[-3].text.startswith("['hjacobs/")
