from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.health import check_database

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    database_ok = check_database(db)

    redis_ok = False
    try:
        redis_client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        redis_ok = bool(redis_client.ping())
        redis_client.close()
    except Exception:
        redis_ok = False

    ready = database_ok and redis_ok

    body = {
        "status": "ready" if ready else "not_ready",
        "dependencies": {
            "database": "ok" if database_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }

    return JSONResponse(
        status_code=200 if ready else 503,
        content=body,
    )
