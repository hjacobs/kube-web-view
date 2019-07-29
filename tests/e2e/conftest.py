import pykube
import yaml
import time
import threading
from tempfile import NamedTemporaryFile
import requests
import logging
from pytest import fixture
from pathlib import Path
import os
import subprocess

from subprocess import check_output, run, Popen


@fixture(scope="module")
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

    url = "http://localhost:8087/"
    proc = Popen(
        ["./kubectl", "port-forward", "service/kube-web-view", "8087:80"],
        env={"KUBECONFIG": kubeconfig},
    )
    logging.info(f"Waiting for port forward {url} ...")
    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()
        except:
            time.sleep(0.1)
        else:
            break

    yield {"url": url}
    proc.kill()


@fixture(scope="module")
def populated_cluster(cluster):
    return cluster
