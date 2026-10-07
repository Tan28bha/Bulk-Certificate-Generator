from fastapi import FastAPI

from app.api.routes.certificates import router as certificates_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router

app = FastAPI(
    title="Bulk Certificate Generator",
    version="1.0.0",
    description="API for bulk certificate generation and tracking.",
)

app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(certificates_router)


@app.get("/")
def root():
    return {
        "name": "Bulk Certificate Generator",
        "version": "1.0.0",
        "docs": "/docs",
    }
