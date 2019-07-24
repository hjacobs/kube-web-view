import pykube
import yaml
import threading
from tempfile import NamedTemporaryFile
import requests
import logging
from pytest import fixture
from pathlib import Path
import os

from subprocess import check_output, run


@fixture(scope="class")
def cluster() -> dict:
    kind = "./kind"
    cluster_name = "kube-web-view-e2e"

    cluster_exists = False
    out = check_output([kind, "get", "clusters"], encoding="utf-8")
    for name in out.splitlines():
        if name == cluster_name:
            cluster_exists = True

    if not cluster_exists:
        logging.info(f"Creating cluster {cluster_name!r} (usually ~1.5m) ...")
        run(
            [kind, "create", "cluster", "--name", cluster_name, "--wait", "2m"],
            check=True,
        )

    kubeconfig = check_output(
        [kind, "get", "kubeconfig-path", "--name", cluster_name], encoding="utf-8"
    ).strip()

    def kubectl(*args: str, **kwargs):
        return run(
            ["./kubectl", *args], check=True, env={"KUBECONFIG": kubeconfig}, **kwargs
        )

    docker_image = os.getenv("TEST_IMAGE")
    logging.info("Loading Docker image in cluster (usually ~5s) ...")
    run(
        [kind, "load", "docker-image", "--name", cluster_name, docker_image], check=True
    )

    logging.info("Deploying kube-web-view ...")
    deployment_manifests_path = Path(__file__).parent / "deployment.yaml"

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

    logging.info("Waiting for rollout ...")
    kubectl("rollout", "status", "deployment/kube-web-view")

    def proxy():
        kubectl("proxy", "--port=8011")

    proxy_url = "http://localhost:8011/"
    threading.Thread(target=proxy, daemon=True).start()
    logging.info(f"Waiting for proxy {proxy_url} ...")
    while True:
        try:
            response = requests.get(proxy_url)
            response.raise_for_status()
        except:
            pass
        else:
            break

    return {"proxy_url": proxy_url}


@fixture(scope="class")
def populated_cluster(cluster):
    return cluster
