# Bulk Certificate Generator

Backend API for bulk certificate generation.

## Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- Redis
- Celery
- ReportLab
- Pytest
- Docker

## Phase 1

This initial version contains:

- FastAPI application
- PostgreSQL service
- Redis service
- Celery worker service
- Application configuration
- Database engine/session foundation
- `/health` endpoint
- Initial test

## Run with Docker

```bash
docker compose up --build
```

API docs:

http://localhost:8000/docs

Health:

http://localhost:8000/health

## Run locally

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it and install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then start PostgreSQL and Redis.

Run API:

```bash
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest
```
