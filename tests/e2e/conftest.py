import yaml
from tempfile import NamedTemporaryFile
import logging
from pytest import fixture
from pathlib import Path
import os
from functools import partial

from requests_html import HTMLSession

kind_cluster_name = "kube-web-view-e2e"


@fixture(scope="session")
def cluster(kind_cluster) -> dict:
    docker_image = os.getenv("TEST_IMAGE")
    kind_cluster.load_docker_image(docker_image)

    logging.info("Deploying kube-web-view ...")
    deployment_manifests_path = Path(__file__).parent / "deployment.yaml"

    kubectl = kind_cluster.kubectl

    with NamedTemporaryFile(mode="w+") as tmp:
        with deployment_manifests_path.open() as f:
            resources = list(yaml.safe_load_all(f))
        dep = resources[-1]
        assert (
            dep["kind"] == "Deployment" and dep["metadata"]["name"] == "kube-web-view"
        )
        dep["spec"]["template"]["spec"]["containers"][0]["image"] = docker_image
        yaml.dump_all(documents=resources, stream=tmp)
        kubectl("apply", "-f", tmp.name)

    logging.info("Deploying other test resources ...")
    kubectl("apply", "-f", str(Path(__file__).parent / "test-resources.yaml"))

    logging.info("Waiting for rollout ...")
    kubectl("rollout", "status", "deployment/kube-web-view")

    with kind_cluster.port_forward("service/kube-web-view", 80) as port:
        url = f"http://localhost:{port}/"
        yield {"url": url}


@fixture(scope="session")
def populated_cluster(cluster):
    return cluster


@fixture(scope="session")
def session(populated_cluster):

    url = populated_cluster["url"].rstrip("/")

    s = HTMLSession()

    def new_request(prefix, f, method, url, *args, **kwargs):
        return f(method, prefix + url, *args, **kwargs)

    s.request = partial(new_request, url, s.request)
    return s
