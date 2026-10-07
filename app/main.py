from fastapi import FastAPI

from app.api.routes.health import router as health_router

app = FastAPI(
    title="Bulk Certificate Generator",
    version="1.0.0",
    description="API for bulk certificate generation and tracking.",
)

app.include_router(health_router)


@app.get("/")
def root():
    return {
        "name": "Bulk Certificate Generator",
        "version": "1.0.0",
        "docs": "/docs",
    }
