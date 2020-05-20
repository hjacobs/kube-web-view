from pathlib import Path
from unittest.mock import MagicMock

from kube_web.cluster_discovery import KubeconfigDiscoverer
from kube_web.main import main
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


def test_use_kubeconfig_path_if_passed(monkeypatch, tmpdir):
    def get_app(cluster_manager, config):
        # make sure we use the passed kubeconfig
        assert isinstance(cluster_manager.discoverer, KubeconfigDiscoverer)
        return None

    monkeypatch.setattr("aiohttp.web.run_app", lambda *args, port, handle_signals: None)
    monkeypatch.setattr("kube_web.main.get_app", get_app)

    kubeconfig_path = Path(str(tmpdir)) / "my-kubeconfig"
    with kubeconfig_path.open("w") as fd:
        fd.write("{contexts: []}")

    # fake successful service account discovery ("in-cluster")
    monkeypatch.setattr("kube_web.main.ServiceAccountClusterDiscoverer", MagicMock())
    main([f"--kubeconfig-path={kubeconfig_path}"])
