"""Builds a kubeconfig for the target EKS cluster and loads the Kubernetes client.

This mirrors what `aws eks update-kubeconfig` does: it writes a kubeconfig whose
user credential is an `exec` plugin that shells out to `aws eks get-token` to
mint short-lived tokens. The arguments are entirely server-side configuration
(cluster name / region from Settings) — never user-supplied — so this is not an
injection risk.
"""
import logging
import subprocess

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from app.config import get_settings

logger = logging.getLogger(__name__)

_api_client: client.ApiClient | None = None


def ensure_kubeconfig() -> None:
    settings = get_settings()
    cmd = [
        "aws",
        "eks",
        "update-kubeconfig",
        "--name",
        settings.eks_cluster_name,
        "--region",
        settings.aws_region,
        "--kubeconfig",
        settings.kubeconfig_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to generate kubeconfig via aws-cli: {result.stderr.strip()}"
        )
    logger.info("kubeconfig generated at %s", settings.kubeconfig_path)


def get_api_client() -> client.ApiClient:
    global _api_client
    if _api_client is None:
        settings = get_settings()
        try:
            config.load_kube_config(config_file=settings.kubeconfig_path)
        except ConfigException as exc:
            raise RuntimeError(
                "No usable kubeconfig — check EKS_CLUSTER_NAME/AWS_REGION and that "
                "'aws eks update-kubeconfig' succeeds on this host"
            ) from exc
        _api_client = client.ApiClient()
    return _api_client


def core_v1() -> client.CoreV1Api:
    return client.CoreV1Api(get_api_client())


def apps_v1() -> client.AppsV1Api:
    return client.AppsV1Api(get_api_client())


def custom_objects_v1() -> client.CustomObjectsApi:
    return client.CustomObjectsApi(get_api_client())


def exec_ws_client(namespace: str, name: str, container: str | None = None):
    """Opens an interactive `kubectl exec`-style session and returns the raw
    WSClient (kubernetes.stream.ws_client.WSClient) for bidirectional I/O.
    Caller is responsible for closing it.

    Uses a dedicated ApiClient rather than the shared singleton: `stream()`
    temporarily monkey-patches `ApiClient.request` on the instance it's given,
    and doing that on the shared client racing with concurrent REST calls
    (list/describe/etc. from other requests) can permanently corrupt it.
    """
    from kubernetes.stream import stream

    settings = get_settings()
    configuration = client.Configuration()
    config.load_kube_config(config_file=settings.kubeconfig_path, client_configuration=configuration)
    dedicated_core_v1 = client.CoreV1Api(client.ApiClient(configuration=configuration))

    command = ["/bin/sh", "-c", "clear; (bash || ash || sh)"]
    kwargs = {
        "command": command,
        "stderr": True,
        "stdin": True,
        "stdout": True,
        "tty": True,
        "_preload_content": False,
    }
    if container:
        kwargs["container"] = container
    return stream(dedicated_core_v1.connect_get_namespaced_pod_exec, name, namespace, **kwargs)

