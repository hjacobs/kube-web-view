from kube_web.main import parse_args


def test_parse_clusters():
    args = parse_args(["--clusters=foo=https://foo;bar=https://bar"])
    assert args.clusters == {"foo": "https://foo", "bar": "https://bar"}


def test_parse_sidebar_resource_types():
    args = parse_args(["--sidebar-resource-types=Main=nodes,pods;CRDs=foos,bars"])
    assert args.sidebar_resource_types == {
        "Main": ["nodes", "pods"],
        "CRDs": ["foos", "bars"],
    }


def test_parse_default_custom_columns():
    args = parse_args(
        [
            "--default-custom-columns=pods=A=metadata.name;B=spec;;deployments=Strategy=spec.strategy"
        ]
    )
    assert args.default_custom_columns == {
        "pods": "A=metadata.name;B=spec",
        "deployments": "Strategy=spec.strategy",
    }
