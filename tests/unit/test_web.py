import re

from kube_web.web import generate_name_from_spec
from kube_web.web import is_allowed_namespace


def test_generate_name_from_spec():
    assert generate_name_from_spec("a.b") == "A B"
    assert generate_name_from_spec(" a.b ") == "A B"
    assert (
        generate_name_from_spec(" a[1].containers[*].Image ") == "A 1 Containers Image"
    )
    assert (
        generate_name_from_spec('metadata.annotations."foo"')
        == "Metadata Annotations Foo"
    )


def test_is_allowed_namespace():
    assert is_allowed_namespace("a", [], [])
    assert is_allowed_namespace("a", [re.compile("a")], [])
    assert is_allowed_namespace("a", [], [re.compile("b")])
    assert not is_allowed_namespace("a", [re.compile("b")], [])
    assert not is_allowed_namespace("a", [], [re.compile("a")])

    assert not is_allowed_namespace("default-foo", [re.compile("default")], [])
