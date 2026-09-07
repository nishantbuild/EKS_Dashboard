import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.kube import ensure_kubeconfig
from app.routers import api, audit_router, auth_router, ws_exec, ws_logs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EKS Dashboard API")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Without this, an unhandled error (e.g. cluster unreachable) drops the
    # connection before CORS headers are attached, which browsers report as
    # a confusing CORS error instead of the real 5xx failure.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=502, content={"detail": f"Upstream error: {exc}"})

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(api.router)
app.include_router(audit_router.router)
app.include_router(ws_logs.router)
app.include_router(ws_exec.router)


@app.on_event("startup")
def on_startup():
    try:
        ensure_kubeconfig()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not generate kubeconfig at startup: %s", exc)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
