import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from kubernetes.client import ApiException

from app import rbac
from app.auth import decode_session_token
from app.auth import SESSION_COOKIE_NAME
from app.kube import core_v1

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_user_from_ws(websocket: WebSocket):
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        return decode_session_token(token)
    except Exception:
        return None


@router.websocket("/ws/{namespace}/pods/{name}/logs")
async def stream_pod_logs(websocket: WebSocket, namespace: str, name: str, container: str | None = None):
    user = _get_user_from_ws(websocket)
    if not user or not rbac.can_perform(user.groups, "get_pod_logs") or not rbac.can_access_namespace(
        user.groups, namespace
    ):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    loop = asyncio.get_event_loop()

    def _blocking_stream():
        try:
            return core_v1().read_namespaced_pod_log(
                name, namespace, container=container, follow=True, _preload_content=False, tail_lines=200
            )
        except ApiException as exc:
            raise RuntimeError(str(exc)) from exc

    try:
        resp = await loop.run_in_executor(None, _blocking_stream)
        for line in resp.stream(amt=1024, decode_content=True):
            await websocket.send_text(line if isinstance(line, str) else line.decode(errors="replace"))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 - surface stream errors to the client
        try:
            await websocket.send_text(f"[stream error] {exc}")
        finally:
            await websocket.close()
