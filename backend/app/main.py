"""SimGuard — Main FastAPI application.

Security hardening:
- Rate limiting via slowapi (60 req/min global, 10 req/min on fraud endpoints)
- Max payload size enforcement
- CORS restricted to configured origins
- No secrets in code — all via env vars
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import get_settings
from .database import engine, Base
from .models import transaction, fraud_alert  # register models
from .api import transactions, fraud, dashboard, verification
from .websocket import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    logger.info("SimGuard started — database tables ready")
    yield
    logger.info("SimGuard shutting down")


app = FastAPI(
    title="SimGuard API",
    description="Real-time SIM Swap Fraud Prevention for Mobile Money",
    version="1.0.0",
    lifespan=lifespan,
    # Disable default docs in production
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

# ── Middlewares ───────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_payload_size(request: Request, call_next):
    """Reject requests with oversized bodies."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_payload_size:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Payload too large. Max {settings.max_payload_size // 1024} KB."}
        )
    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(transactions.router)
app.include_router(fraud.router)
app.include_router(dashboard.router)
app.include_router(verification.router)


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; clients only receive broadcasts
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "simguard", "version": "1.0.0"}


@app.get("/")
def root():
    return {"message": "SimGuard API — Real-time SIM Swap Fraud Prevention"}

# At top with other imports
from .api import transactions, fraud, dashboard, verification, demo

# With other routers
app.include_router(demo.router)