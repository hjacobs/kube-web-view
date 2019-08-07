from kube_web.kubernetes import parse_resource


def test_parse_resource():
    assert parse_resource("500m") == 0.5
