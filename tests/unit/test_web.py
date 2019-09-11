from kube_web.web import generate_name_from_spec


def test_generate_name_from_spec():
    assert generate_name_from_spec("a.b") == "A B"
    assert generate_name_from_spec(" a.b ") == "A B"
    assert generate_name_from_spec(" a[1].containers[*].Image ") == "A 1 Containers Image"
    assert generate_name_from_spec("metadata.annotations.\"foo\"") == "Metadata Annotations Foo"
