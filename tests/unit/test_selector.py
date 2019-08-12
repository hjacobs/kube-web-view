from kube_web.selector import parse_selector, selector_matches


def test_parse_selector():
    assert parse_selector("a=1") == {"a": "1"}


def test_selector_matches():
    assert selector_matches({"a!": ["1", "2"]}, {"a": "3"})
    assert not selector_matches({"a!": ["1", "2"]}, {"a": "1"})
    assert not selector_matches({"a!": ["1", "2"]}, {"a": "2"})
