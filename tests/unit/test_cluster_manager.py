from kube_web.cluster_manager import sanitize_cluster_name


def test_sanitize_cluster_name():
    assert sanitize_cluster_name("foo.bar") == "foo.bar"
    assert sanitize_cluster_name("my-cluster") == "my-cluster"
    assert sanitize_cluster_name("a b") == "a:b"
    assert sanitize_cluster_name("https://srcco.de") == "https:::srcco.de"


