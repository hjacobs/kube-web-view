import datetime

from kube_web.jinja2_filters import age_color
from kube_web.jinja2_filters import pluralize
from kube_web.jinja2_filters import yaml


def test_yaml():
    assert yaml({}) == "{}\n"


def test_pluralize():
    assert pluralize("test") == "tests"
    assert pluralize("Ingress") == "Ingresses"
    assert pluralize("NetworkPolicy") == "NetworkPolicies"


def test_age_color():
    now = datetime.datetime.now()
    dt = now - datetime.timedelta(days=2)
    assert age_color(now, days=1) == "#00cf46"
    # older timestamps should be default bulma text color
    assert age_color(dt, days=1) == "#363636"
