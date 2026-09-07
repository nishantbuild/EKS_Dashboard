from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app import actions, rbac
from app.audit import record
from app.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api", tags=["api"])


def _authorize(user: CurrentUser, action: str, namespace: str | None = None) -> None:
    if not rbac.can_perform(user.groups, action):
        record(user.email, action, {"namespace": namespace}, "denied", "action not permitted")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action not permitted")
    if namespace and not rbac.can_access_namespace(user.groups, namespace):
        record(user.email, action, {"namespace": namespace}, "denied", "namespace not permitted")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Namespace not permitted")


@router.get("/namespaces")
def get_namespaces(user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "list_namespaces")
    allowed = rbac.allowed_namespaces(user.groups)
    all_ns = actions.list_namespaces()
    result = all_ns if allowed == "*" else [n for n in all_ns if n in allowed]
    record(user.email, "list_namespaces", {}, "ok")
    return result


@router.get("/{namespace}/pods")
def get_pods(namespace: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "list_pods", namespace)
    result = actions.list_pods(namespace)
    record(user.email, "list_pods", {"namespace": namespace}, "ok")
    return result


@router.get("/{namespace}/pods/{name}")
def get_pod(namespace: str, name: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "describe_pod", namespace)
    try:
        result = actions.describe_pod(namespace, name)
    except LookupError as exc:
        record(user.email, "describe_pod", {"namespace": namespace, "name": name}, "error", str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(user.email, "describe_pod", {"namespace": namespace, "name": name}, "ok")
    return result


@router.get("/{namespace}/pods/{name}/logs")
def get_pod_logs(
    namespace: str,
    name: str,
    container: str | None = None,
    tail_lines: int = Query(default=200, le=5000, ge=1),
    user: CurrentUser = Depends(get_current_user),
):
    _authorize(user, "get_pod_logs", namespace)
    try:
        logs = actions.get_pod_logs(namespace, name, container, tail_lines)
    except LookupError as exc:
        record(user.email, "get_pod_logs", {"namespace": namespace, "name": name}, "error", str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(user.email, "get_pod_logs", {"namespace": namespace, "name": name}, "ok")
    return {"logs": logs}


@router.delete("/{namespace}/pods/{name}")
def delete_pod(namespace: str, name: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "delete_pod", namespace)
    try:
        actions.delete_pod(namespace, name)
    except LookupError as exc:
        record(user.email, "delete_pod", {"namespace": namespace, "name": name}, "error", str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(user.email, "delete_pod", {"namespace": namespace, "name": name}, "ok")
    return {"ok": True}


@router.get("/{namespace}/deployments")
def get_deployments(namespace: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "list_deployments", namespace)
    result = actions.list_deployments(namespace)
    record(user.email, "list_deployments", {"namespace": namespace}, "ok")
    return result


@router.get("/{namespace}/deployments/{name}")
def get_deployment(namespace: str, name: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "describe_deployment", namespace)
    try:
        result = actions.describe_deployment(namespace, name)
    except LookupError as exc:
        record(user.email, "describe_deployment", {"namespace": namespace, "name": name}, "error", str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(user.email, "describe_deployment", {"namespace": namespace, "name": name}, "ok")
    return result


class ScaleRequest(BaseModel):
    replicas: int = Field(ge=0, le=100)


@router.post("/{namespace}/deployments/{name}/scale")
def scale_deployment(
    namespace: str, name: str, payload: ScaleRequest, user: CurrentUser = Depends(get_current_user)
):
    _authorize(user, "scale_deployment", namespace)
    try:
        actions.scale_deployment(namespace, name, payload.replicas)
    except LookupError as exc:
        record(user.email, "scale_deployment", {"namespace": namespace, "name": name}, "error", str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(
        user.email,
        "scale_deployment",
        {"namespace": namespace, "name": name, "replicas": payload.replicas},
        "ok",
    )
    return {"ok": True}


@router.post("/{namespace}/deployments/{name}/restart")
def restart_deployment(namespace: str, name: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "restart_deployment", namespace)
    try:
        actions.restart_deployment(namespace, name)
    except LookupError as exc:
        record(user.email, "restart_deployment", {"namespace": namespace, "name": name}, "error", str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record(user.email, "restart_deployment", {"namespace": namespace, "name": name}, "ok")
    return {"ok": True}


@router.get("/{namespace}/services")
def get_services(namespace: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "list_services", namespace)
    result = actions.list_services(namespace)
    record(user.email, "list_services", {"namespace": namespace}, "ok")
    return result


@router.get("/{namespace}/events")
def get_events(namespace: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "list_events", namespace)
    result = actions.list_events(namespace)
    record(user.email, "list_events", {"namespace": namespace}, "ok")
    return result


@router.get("/{namespace}/metrics/pods")
def get_pod_metrics(namespace: str, user: CurrentUser = Depends(get_current_user)):
    _authorize(user, "view_metrics", namespace)
    try:
        result = actions.list_pod_metrics(namespace)
    except LookupError:
        # metrics-server not ready yet (e.g. pod just started) — soft-fail
        # so the UI just shows an empty/loading state instead of an error toast.
        result = []
    record(user.email, "view_metrics", {"namespace": namespace}, "ok")
    return result
