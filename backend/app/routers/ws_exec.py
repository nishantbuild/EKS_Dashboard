"""Interactive pod terminal (like `kubectl exec -it <pod> -- sh`) over WebSocket.

Gated behind the "exec_pod" RBAC action since it grants much more power than
the read-only/curated actions — treat it like shell access to the pod.
"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app import rbac
from app.audit import record
from app.auth import SESSION_COOKIE_NAME, decode_session_token
from app.kube import exec_ws_client

logger = logging.getLogger(__name__)
router = APIRouter()

STDIN_CHANNEL = 0
STDOUT_CHANNEL = 1
STDERR_CHANNEL = 2
RESIZE_CHANNEL = 4


def _get_user_from_ws(websocket: WebSocket):
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        return decode_session_token(token)
    except Exception:
        return None


@router.websocket("/ws/{namespace}/pods/{name}/exec")
async def pod_exec(websocket: WebSocket, namespace: str, name: str, container: str | None = None):
    user = _get_user_from_ws(websocket)
    if (
        not user
        or not rbac.can_perform(user.groups, "exec_pod")
        or not rbac.can_access_namespace(user.groups, namespace)
    ):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    loop = asyncio.get_event_loop()
    record(user.email, "exec_pod", {"namespace": namespace, "name": name}, "started")

    try:
        ws_client = await loop.run_in_executor(None, exec_ws_client, namespace, name, container)
    except Exception as exc:  # noqa: BLE001
        record(user.email, "exec_pod", {"namespace": namespace, "name": name}, "error", str(exc))
        await websocket.send_text(f"\r\n[failed to start session: {exc}]\r\n")
        await websocket.close()
        return

    def _read_output() -> str | None:
        if not ws_client.is_open():
            return None
        ws_client.update(timeout=1)
        out = ws_client.read_stdout(timeout=1) or ""
        err = ws_client.read_stderr(timeout=1) or ""
        return out + err

    async def pump_output():
        try:
            while ws_client.is_open():
                chunk = await loop.run_in_executor(None, _read_output)
                if chunk:
                    await websocket.send_text(chunk)
                await asyncio.sleep(0.03)
        except (WebSocketDisconnect, RuntimeError):
            # RuntimeError: browser already closed the socket (e.g. dev-mode
            # double-mount) between our is_open() check and send_text().
            pass

    async def pump_input():
        try:
            while True:
                data = await websocket.receive_text()
                await loop.run_in_executor(None, ws_client.write_stdin, data)
        except WebSocketDisconnect:
            pass

    try:
        await asyncio.gather(pump_output(), pump_input())
    except WebSocketDisconnect:
        pass
    finally:
        await loop.run_in_executor(None, ws_client.close)
        record(user.email, "exec_pod", {"namespace": namespace, "name": name}, "ended")
