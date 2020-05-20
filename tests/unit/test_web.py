import re

from kube_web.web import is_allowed_namespace


def test_is_allowed_namespace():
    assert is_allowed_namespace("a", [], [])
    assert is_allowed_namespace("a", [re.compile("a")], [])
    assert is_allowed_namespace("a", [], [re.compile("b")])
    assert not is_allowed_namespace("a", [re.compile("b")], [])
    assert not is_allowed_namespace("a", [], [re.compile("a")])

    assert not is_allowed_namespace("default-foo", [re.compile("default")], [])
