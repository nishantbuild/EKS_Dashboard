"""Curated, safe Kubernetes actions. No shell/kubectl exec — pure API calls.

Every function validates its inputs and talks to the Kubernetes API via the
official client, so there is no command-injection surface.
"""
import re
from datetime import datetime, timezone

from kubernetes.client import ApiException

from app.kube import apps_v1, core_v1, custom_objects_v1

_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


def _validate_name(value: str, field: str) -> None:
    if not value or len(value) > 253 or not _NAME_RE.match(value):
        raise ValueError(f"Invalid {field}: {value!r}")


def list_namespaces() -> list[str]:
    return [ns.metadata.name for ns in core_v1().list_namespace().items]


def list_pods(namespace: str) -> list[dict]:
    _validate_name(namespace, "namespace")
    pods = core_v1().list_namespaced_pod(namespace)
    return [
        {
            "name": p.metadata.name,
            "status": p.status.phase,
            "node": p.spec.node_name,
            "restarts": sum(cs.restart_count for cs in (p.status.container_statuses or [])),
            "started": p.status.start_time.isoformat() if p.status.start_time else None,
        }
        for p in pods.items
    ]


def describe_pod(namespace: str, name: str) -> dict:
    _validate_name(namespace, "namespace")
    _validate_name(name, "pod name")
    try:
        pod = core_v1().read_namespaced_pod(name, namespace)
    except ApiException as exc:
        raise LookupError(f"Pod not found: {exc.reason}") from exc
    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "labels": pod.metadata.labels,
        "status": pod.status.phase,
        "containers": [c.name for c in pod.spec.containers],
        "conditions": [
            {"type": c.type, "status": c.status, "message": c.message}
            for c in (pod.status.conditions or [])
        ],
    }


def get_pod_logs(namespace: str, name: str, container: str | None = None, tail_lines: int = 200) -> str:
    _validate_name(namespace, "namespace")
    _validate_name(name, "pod name")
    tail_lines = max(1, min(tail_lines, 5000))
    try:
        return core_v1().read_namespaced_pod_log(
            name, namespace, container=container, tail_lines=tail_lines, timestamps=True
        )
    except ApiException as exc:
        raise LookupError(f"Could not fetch logs: {exc.reason}") from exc


def delete_pod(namespace: str, name: str) -> None:
    _validate_name(namespace, "namespace")
    _validate_name(name, "pod name")
    try:
        core_v1().delete_namespaced_pod(name, namespace)
    except ApiException as exc:
        raise LookupError(f"Could not delete pod: {exc.reason}") from exc


def list_deployments(namespace: str) -> list[dict]:
    _validate_name(namespace, "namespace")
    deployments = apps_v1().list_namespaced_deployment(namespace)
    return [
        {
            "name": d.metadata.name,
            "replicas": d.spec.replicas,
            "available": d.status.available_replicas or 0,
            "updated": d.status.updated_replicas or 0,
        }
        for d in deployments.items
    ]


def describe_deployment(namespace: str, name: str) -> dict:
    _validate_name(namespace, "namespace")
    _validate_name(name, "deployment name")
    try:
        d = apps_v1().read_namespaced_deployment(name, namespace)
    except ApiException as exc:
        raise LookupError(f"Deployment not found: {exc.reason}") from exc
    return {
        "name": d.metadata.name,
        "namespace": d.metadata.namespace,
        "replicas": d.spec.replicas,
        "available": d.status.available_replicas or 0,
        "images": [c.image for c in d.spec.template.spec.containers],
    }


def scale_deployment(namespace: str, name: str, replicas: int) -> None:
    _validate_name(namespace, "namespace")
    _validate_name(name, "deployment name")
    if not (0 <= replicas <= 100):
        raise ValueError("replicas must be between 0 and 100")
    try:
        apps_v1().patch_namespaced_deployment_scale(
            name, namespace, {"spec": {"replicas": replicas}}
        )
    except ApiException as exc:
        raise LookupError(f"Could not scale deployment: {exc.reason}") from exc


def restart_deployment(namespace: str, name: str) -> None:
    """Equivalent of `kubectl rollout restart deployment/<name>`."""
    _validate_name(namespace, "namespace")
    _validate_name(name, "deployment name")
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "eks-dashboard/restartedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        }
    }
    try:
        apps_v1().patch_namespaced_deployment(name, namespace, patch)
    except ApiException as exc:
        raise LookupError(f"Could not restart deployment: {exc.reason}") from exc


def list_services(namespace: str) -> list[dict]:
    _validate_name(namespace, "namespace")
    services = core_v1().list_namespaced_service(namespace)
    return [
        {
            "name": s.metadata.name,
            "type": s.spec.type,
            "cluster_ip": s.spec.cluster_ip,
            "ports": [{"port": p.port, "target_port": str(p.target_port)} for p in (s.spec.ports or [])],
        }
        for s in services.items
    ]


def list_events(namespace: str) -> list[dict]:
    _validate_name(namespace, "namespace")
    events = core_v1().list_namespaced_event(namespace)
    return [
        {
            "type": e.type,
            "reason": e.reason,
            "message": e.message,
            "object": f"{e.involved_object.kind}/{e.involved_object.name}",
            "last_seen": e.last_timestamp.isoformat() if e.last_timestamp else None,
        }
        for e in events.items
    ]


def _parse_cpu(value: str) -> float:
    """Returns millicores as a float, e.g. "250m" -> 250, "1" -> 1000."""
    if value.endswith("n"):
        return int(value[:-1]) / 1_000_000
    if value.endswith("u"):
        return int(value[:-1]) / 1_000
    if value.endswith("m"):
        return int(value[:-1])
    return float(value) * 1000


_MEMORY_UNITS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}


def _parse_memory(value: str) -> float:
    """Returns bytes as a float, e.g. "128Mi" -> 134217728."""
    for suffix, multiplier in _MEMORY_UNITS.items():
        if value.endswith(suffix):
            return float(value[: -len(suffix)]) * multiplier
    return float(value)


def list_pod_metrics(namespace: str) -> list[dict]:
    """CPU/memory usage per pod, backed by the cluster's metrics-server
    (same data source as `kubectl top pods`).
    """
    _validate_name(namespace, "namespace")
    try:
        data = custom_objects_v1().list_namespaced_custom_object(
            group="metrics.k8s.io", version="v1beta1", namespace=namespace, plural="pods"
        )
    except ApiException as exc:
        if exc.status == 404:
            raise LookupError(
                "metrics-server data not available yet (pod just started, or metrics-server not installed)"
            ) from exc
        raise LookupError(f"Could not fetch metrics: {exc.reason}") from exc

    results = []
    for item in data.get("items", []):
        cpu_m = sum(_parse_cpu(c["usage"]["cpu"]) for c in item.get("containers", []))
        mem_bytes = sum(_parse_memory(c["usage"]["memory"]) for c in item.get("containers", []))
        results.append(
            {
                "name": item["metadata"]["name"],
                "cpu_millicores": round(cpu_m, 1),
                "memory_mib": round(mem_bytes / 1024**2, 1),
            }
        )
    return results
