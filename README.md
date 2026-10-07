# Bulk Certificate Generator 🎓⚡

A high-performance, asynchronous RESTful API for generating personalized PDF certificates in bulk. Built with **FastAPI**, **PostgreSQL**, **Celery**, **Redis**, and **ReportLab**, this service is engineered for reliability, failure isolation, idempotency, and concurrent processing.

---

## 📑 Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Project Setup](#-project-setup)
  - [Option A: Docker Compose (Recommended)](#option-a-docker-compose-recommended)
  - [Option B: Local Environment Setup](#option-b-local-environment-setup)
- [Running the Application](#-running-the-application)
- [Database Migrations](#-database-migrations)
- [Running Tests](#-running-tests)
- [How to Submit a Certificate Generation Request](#-how-to-submit-a-certificate-generation-request)
- [How to Retrieve Generated Certificates](#-how-to-retrieve-generated-certificates)
- [How to Retry Failed Certificates](#-how-to-retry-failed-certificates)
- [Health & Readiness Probes](#-health--readiness-probes)
- [Important Implementation & Design Decisions](#-important-implementation--design-decisions)
- [Project Structure](#-project-structure)
- [Environment Configuration Reference](#-environment-configuration-reference)

---

## 🌟 Features

- **Bulk Certificate Generation**: Submit up to 10,000 recipients in a single request with automated background rendering.
- **Asynchronous Worker Queue**: Decoupled HTTP API and Celery workers backed by Redis broker to prevent request timeouts.
- **Per-Certificate Failure Isolation**: An error during one recipient's PDF generation does not abort or corrupt the rest of the batch.
- **Strict Idempotency**: Optional `Idempotency-Key` header prevents duplicate job submission and duplicate billing/processing during network retries.
- **Atomic Worker Safety**: Conditional SQL claiming (`PENDING` $\rightarrow$ `PROCESSING`) guarantees that duplicate Celery deliveries or multiple workers never generate duplicate PDFs.
- **Targeted Retries**: Retry individual failed certificates without re-generating the entire batch.
- **Live Progress & Tracking**: Real-time batch progress metrics (processed, successful, failed, percentage).
- **Fast & Isolated Test Suite**: Pytest suite using an in-memory SQLite database (`StaticPool`) that runs in seconds without external infrastructure.
- **Containerized**: Full Docker and Docker Compose environment ready for development and deployment.

---

## 🏗 System Architecture

```text
[ Client / Frontend ]
         |
         |  1. POST /api/v1/jobs (with Idempotency-Key)
         v
+------------------+         2. Save Job & Recipients (Transaction)
|   FastAPI App    | ---------------------------------------------> [ PostgreSQL ]
|    (API Server)  | <---------------------------------------------
+------------------+
         |
         |  3. Enqueue Job ID (Celery Task)
         v
+------------------+
|   Redis Broker   |
+------------------+
         |
         |  4. Consume Job & Claim Certificate Atomically
         v
+------------------+         5. Fetch recipient details
|  Celery Workers  | <--------------------------------------------> [ PostgreSQL ]
| (ReportLab PDFs) |         6. Update status & counters
+------------------+
         |
         |  7. Write generated PDF file
         v
+-------------------------------------------------------+
| Local Storage (storage/certificates/<job_id>/<id>.pdf)|
+-------------------------------------------------------+
```

---

## 🛠 Tech Stack

| Component | Technology | Description |
|---|---|---|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Modern, high-speed ASGI web framework |
| **ASGI Server** | [Uvicorn](https://www.uvicorn.org/) | Lightning-fast ASGI server |
| **Relational Database** | [PostgreSQL 16](https://www.postgresql.org/) | ACID-compliant relational storage with UUID support |
| **ORM & Migrations** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) & [Alembic](https://alembic.sqlalchemy.org/) | Type-safe ORM & version-controlled database schema migrations |
| **Database Driver** | [psycopg 3 (binary)](https://www.psycopg.org/) | Next-generation PostgreSQL driver for Python |
| **Task Queue & Broker** | [Celery 5](https://docs.celeryq.dev/) & [Redis 7](https://redis.io/) | Distributed asynchronous task execution and message broker |
| **PDF Generation Engine** | [ReportLab](https://www.reportlab.com/) | High-performance programmatic PDF document creation |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) & [email-validator](https://github.com/JoshData/python-email-validator) | Robust schema parsing, trimming, and email validation |
| **Testing** | [Pytest](https://pytest.org/) & [HTTPX / TestClient](https://www.python-httpx.org/) | Automated unit and integration testing |
| **Containerization** | [Docker](https://www.docker.com/) & Docker Compose | Multi-container orchestration |

---

## 📋 Prerequisites

Before running the application, ensure you have the following installed:

- **Docker & Docker Compose** (for containerized execution)
  *— OR —*
- **Python 3.10+ / 3.12**
- **PostgreSQL 14+** (running locally or in a container)
- **Redis 6+** (running locally or in a container)

---

## 🚀 Project Setup

### Option A: Docker Compose (Recommended)

Docker Compose starts PostgreSQL, Redis, the FastAPI application, and the Celery worker in one step.

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd bulk-certificate-generator
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

3. **Build and start the containers**:
   ```bash
   docker compose up --build -d
   ```

4. **Apply database migrations**:
   ```bash
   docker compose run --rm api alembic upgrade head
   ```

5. **Verify services are running**:
   ```bash
   docker compose ps
   ```

---

### Option B: Local Environment Setup

If you prefer to run services directly on your host machine:

1. **Create and activate a virtual environment**:
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. **Install project dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the environment file**:
   Create a `.env` file from `.env.example`:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/certificates
   REDIS_URL=redis://localhost:6379/0
   STORAGE_DIR=./storage/certificates
   ```

4. **Ensure PostgreSQL & Redis are running**:
   If you have Docker installed, you can spin up just PostgreSQL and Redis:
   ```bash
   docker compose up -d postgres redis
   ```

5. **Run Alembic migrations**:
   ```bash
   alembic upgrade head
   ```

---

## 🏃 Running the Application

### 1. Start the FastAPI API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once started, access:
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Root API Info**: [http://localhost:8000/](http://localhost:8000/)

### 2. Start the Celery Worker

In a separate terminal window (with the virtual environment activated):

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

---

## 🗄 Database Migrations

Database schemas are managed with **Alembic**.

- **Apply all migrations**:
  ```bash
  alembic upgrade head
  ```
  *(Or via Docker: `docker compose run --rm api alembic upgrade head`)*

- **Create a new migration after model changes**:
  ```bash
  alembic revision --autogenerate -m "describe schema changes"
  ```

- **Rollback the last migration**:
  ```bash
  alembic downgrade -1
  ```

---

## 🧪 Running Tests

The test suite is fully automated using **Pytest**. 

It uses an in-memory SQLite database fixture (`sqlite://` with `StaticPool`) configured in `tests/conftest.py`, meaning **tests run completely independently and do not require running PostgreSQL or Redis instances**.

### Run all tests

```bash
pytest
```

### Run tests with verbose output

```bash
pytest -v
```

### Run a specific test file

```bash
pytest tests/test_jobs_api.py -v
pytest tests/test_failure_handling.py -v
pytest tests/test_worker_safety.py -v
pytest tests/test_retry_api.py -v
```

### What the test suite verifies:
- **Job Creation & Validation**: Schema validation, email sanitization, and batch bounds.
- **Idempotency**: Repeated requests with the same `Idempotency-Key` return the existing job without creating duplicates.
- **Failure Isolation**: An error generating one certificate does not crash the Celery worker or abort remaining certificates.
- **Worker Safety / Concurrency**: Atomic claiming ensures only one worker processes a given certificate.
- **Certificate Downloads & Access Control**: Verification that completed PDFs can be downloaded, while pending or failed certificates return HTTP `409 Conflict`.
- **Granular Retries**: Only failed certificates can be reset and queued for retry.
- **Health & Readiness Endpoints**: Validates database and cache connectivity probes.

---

## 📨 How to Submit a Certificate Generation Request

Submit a batch of certificate recipients to the `/api/v1/jobs` endpoint.

### Endpoint Details

- **Method**: `POST`
- **Path**: `/api/v1/jobs`
- **Headers**:
  - `Content-Type: application/json`
  - `Idempotency-Key: <unique-string>` *(Recommended — prevents duplicate submissions on network retries)*

### Request Body Format

```json
{
  "event_name": "Modern Cloud Architecture Summit 2026",
  "certificate_title": "Certificate of Completion",
  "recipients": [
    {
      "name": "Jane Doe",
      "email": "jane.doe@example.com"
    },
    {
      "name": "John Smith",
      "email": "john.smith@example.com"
    },
    {
      "name": "Alex Johnson",
      "email": "alex.j@example.com"
    }
  ]
}
```

### Example `curl` Command

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: summit-2026-batch-01" \
  -d '{
    "event_name": "Modern Cloud Architecture Summit 2026",
    "certificate_title": "Certificate of Completion",
    "recipients": [
      {
        "name": "Jane Doe",
        "email": "jane.doe@example.com"
      },
      {
        "name": "John Smith",
        "email": "john.smith@example.com"
      }
    ]
  }'
```

### Response (`201 Created`)

```json
{
  "job_id": "a50fc497-ec23-424d-9bd8-cbf39b8bc14b",
  "status": "QUEUED",
  "total": 2,
  "processed": 0,
  "successful": 0,
  "failed": 0,
  "progress": 0.0,
  "message": "Certificate generation job created and queued successfully."
}
```

---

## 📥 How to Retrieve Generated Certificates

### Step 1: Check Job Status and Progress

Poll the status of the generation job using its `job_id`:

- **Method**: `GET`
- **Path**: `/api/v1/jobs/{job_id}`

```bash
curl http://localhost:8000/api/v1/jobs/a50fc497-ec23-424d-9bd8-cbf39b8bc14b
```

#### Example Response:

```json
{
  "job_id": "a50fc497-ec23-424d-9bd8-cbf39b8bc14b",
  "status": "COMPLETED",
  "total": 2,
  "processed": 2,
  "successful": 2,
  "failed": 0,
  "progress": 100.0,
  "message": "Generation job status retrieved successfully."
}
```

#### Possible Job Statuses:
- `QUEUED`: Job is created and waiting in Redis queue.
- `PROCESSING`: Celery worker is currently generating certificates.
- `COMPLETED`: All certificates were generated successfully.
- `COMPLETED_WITH_ERRORS`: Job finished, but one or more certificates failed.
- `FAILED`: All certificates in the job failed.

---

### Step 2: List All Certificates for a Job

Retrieve metadata and individual IDs for each certificate in a job:

- **Method**: `GET`
- **Path**: `/api/v1/jobs/{job_id}/certificates`

```bash
curl http://localhost:8000/api/v1/jobs/a50fc497-ec23-424d-9bd8-cbf39b8bc14b/certificates
```

#### Example Response:

```json
[
  {
    "certificate_id": "8bb3e935-7ce3-4bb4-a8fe-fb903b41e860",
    "job_id": "a50fc497-ec23-424d-9bd8-cbf39b8bc14b",
    "recipient_name": "Jane Doe",
    "recipient_email": "jane.doe@example.com",
    "status": "SUCCESS",
    "file_path": "/app/storage/a50fc497-ec23-424d-9bd8-cbf39b8bc14b/8bb3e935-7ce3-4bb4-a8fe-fb903b41e860.pdf",
    "error_message": null,
    "created_at": "2026-10-07T12:00:00Z",
    "completed_at": "2026-10-07T12:00:01Z"
  },
  {
    "certificate_id": "2d94cfbc-418a-4467-bc18-2e389d49487c",
    "job_id": "a50fc497-ec23-424d-9bd8-cbf39b8bc14b",
    "recipient_name": "John Smith",
    "recipient_email": "john.smith@example.com",
    "status": "SUCCESS",
    "file_path": "/app/storage/a50fc497-ec23-424d-9bd8-cbf39b8bc14b/2d94cfbc-418a-4467-bc18-2e389d49487c.pdf",
    "error_message": null,
    "created_at": "2026-10-07T12:00:00Z",
    "completed_at": "2026-10-07T12:00:01Z"
  }
]
```

---

### Step 3: Download a Certificate PDF

Download the binary PDF file using the `certificate_id`:

- **Method**: `GET`
- **Path**: `/api/v1/certificates/{certificate_id}`

```bash
curl -o certificate.pdf http://localhost:8000/api/v1/certificates/8bb3e935-7ce3-4bb4-a8fe-fb903b41e860
```

> **Note**: If a certificate is still `PENDING`, `PROCESSING`, or `FAILED`, the API returns HTTP `409 Conflict` preventing partial or corrupted downloads.

---

## 🔄 How to Retry Failed Certificates

If a certificate failed during generation (e.g. temporary filesystem IO error), you can trigger a retry specifically for that certificate without re-running the successful certificates in the batch.

- **Method**: `POST`
- **Path**: `/api/v1/certificates/{certificate_id}/retry`

```bash
curl -X POST http://localhost:8000/api/v1/certificates/2d94cfbc-418a-4467-bc18-2e389d49487c/retry
```

### Response (`200 OK`)

```json
{
  "certificate_id": "2d94cfbc-418a-4467-bc18-2e389d49487c",
  "job_id": "a50fc497-ec23-424d-9bd8-cbf39b8bc14b",
  "recipient_name": "John Smith",
  "recipient_email": "john.smith@example.com",
  "status": "PENDING",
  "file_path": null,
  "error_message": null,
  "created_at": "2026-10-07T12:00:00Z",
  "completed_at": null
}
```

The certificate status is reset to `PENDING`, failure counters are adjusted, and the Celery worker task is re-queued.

---

## 🩺 Health & Readiness Probes

The application provides two dedicated monitoring endpoints for Kubernetes, Docker, or external uptime checkers:

### 1. Liveness Probe (`GET /health`)
Verifies the FastAPI web server is alive and responding.

```bash
curl http://localhost:8000/health
# Response: {"status": "ok"} (HTTP 200)
```

### 2. Readiness Probe (`GET /health/ready`)
Actively verifies database (PostgreSQL) and cache/broker (Redis) connections.

```bash
curl http://localhost:8000/health/ready
```

- **HTTP 200 (Ready)**:
  ```json
  {
    "status": "ready",
    "dependencies": {
      "database": "ok",
      "redis": "ok"
    }
  }
  ```
- **HTTP 503 (Not Ready)**:
  Returned if either PostgreSQL or Redis is unreachable.

---

## 🧠 Important Implementation & Design Decisions

### 1. Asynchronous Architecture & Decoupling (Celery + Redis)
- **Problem**: Generating hundreds or thousands of PDF documents involves significant CPU and file I/O operations. Running this synchronously within an HTTP request causes connection timeouts and degrades API responsiveness.
- **Solution**: The API accepts the batch payload, persists the job and certificate records in a single database transaction, dispatches a Celery task with the `job_id`, and immediately returns HTTP `201 Created`. Celery workers execute the PDF rendering in the background.

### 2. Relational Integrity & Schema Design (PostgreSQL + SQLAlchemy)
- **Two-tier Model**: A parent `generation_jobs` table holds batch metadata and aggregate progress counters (`total_count`, `processed_count`, `successful_count`, `failed_count`), while a child `certificates` table tracks individual recipient records.
- **Foreign Key Cascades**: Certificates reference `job_id` with `ondelete="CASCADE"`.
- **UUID Primary Keys**: Prevents sequential ID enumeration attacks and facilitates distributed scaling.

### 3. Per-Certificate Failure Isolation & Partial Success Handling
- **Problem**: In bulk operations, an unexpected failure (e.g. special character rendering fault, disk glitch) should not invalidate or halt the rest of the batch.
- **Solution**: Each certificate is processed inside its own isolated `try...except` block in `app/workers/tasks.py`. If rendering fails, the exception is logged to `certificates.error_message`, the status is set to `FAILED`, and the worker continues with the next recipient. The parent job status accurately reflects the aggregate outcome (`COMPLETED_WITH_ERRORS`).

### 4. Atomic Worker Claiming & Concurrency Protection
- **Problem**: In distributed systems, Celery guarantees *at-least-once* message delivery. If duplicate task messages are delivered or multiple workers process the same queue, two workers might generate the same certificate concurrently.
- **Solution**: Before generating a certificate, workers perform an atomic conditional database update:
  ```sql
  UPDATE certificates 
  SET status = 'PROCESSING' 
  WHERE id = :certificate_id AND status = 'PENDING';
  ```
  Only the worker whose query returns `rowcount == 1` acquires permission to generate that certificate. Any duplicate attempt gets `rowcount == 0` and skips it.

### 5. Client-Side Idempotency (`Idempotency-Key`)
- Clients can provide a unique `Idempotency-Key` header. The database enforces a unique constraint on `generation_jobs.idempotency_key`.
- If a client experiences a network timeout and retries the exact same request, the API detects the existing key and returns the original job status rather than queuing duplicate batches.

### 6. Granular, Certificate-Level Retries
- Rather than restarting an entire bulk job of 1,000 certificates when only 2 failed, the system provides a granular retry endpoint (`POST /api/v1/certificates/{id}/retry`).
- Only `FAILED` certificates can be reset to `PENDING`. Successful certificates are immutable, avoiding wasted CPU cycles and duplicate files.

### 7. Decoupled File Storage vs Database Blobs
- Generated PDF files are written to structured directory paths (`storage/certificates/<job_id>/<certificate_id>.pdf`) instead of storing large binary data in PostgreSQL.
- This design keeps the relational database lean and enables an easy transition to Amazon S3, Google Cloud Storage, or MinIO in production environments without changing the data model.

### 8. Transactional Consistency Before Enqueueing
- In `app/api/routes/jobs.py`, the Celery task (`process_generation_job.delay(...)`) is triggered **only after** `db.commit()` has successfully persisted the job and all child certificates. This prevents race conditions where workers attempt to process a job before it exists in the database.

---

## 📁 Project Structure

```text
bulk-certificate-generator/
├── alembic/                      # Alembic database migration scripts
│   ├── versions/                 # Schema migration version files
│   │   └── 0001_initial.py       # Initial schema creation
│   └── env.py                    # Alembic environment configuration
├── app/                          # Core application package
│   ├── api/                      # API routing and controllers
│   │   └── routes/
│   │       ├── certificates.py   # Certificate listing, download, retry routes
│   │       ├── health.py         # Liveness and readiness endpoints
│   │       └── jobs.py           # Job submission and status tracking
│   ├── core/                     # Application configurations and database session
│   │   ├── config.py             # Pydantic BaseSettings environment loader
│   │   ├── database.py           # SQLAlchemy Engine, Base, and SessionLocal
│   │   └── health.py             # Database connectivity checker
│   ├── models/                   # SQLAlchemy ORM database models
│   │   ├── certificate.py        # Certificate table model and status enum
│   │   └── generation_job.py     # GenerationJob table model and status enum
│   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── certificate.py        # Certificate response schemas
│   │   └── job.py                # Job creation and response schemas
│   ├── services/                 # Business logic and external service integrations
│   │   ├── certificate_service.py # ReportLab PDF canvas rendering
│   │   ├── job_service.py        # Job creation and DB lookup helpers
│   │   └── storage_service.py    # Local file path and directory management
│   ├── workers/                  # Celery worker configuration and task definitions
│   │   ├── celery_app.py         # Celery instance configuration
│   │   ├── retry.py              # Failed certificate reset logic
│   │   └── tasks.py              # Background worker tasks and atomic claiming
│   └── main.py                   # FastAPI application entrypoint
├── storage/                      # Directory for generated PDF certificates
├── tests/                        # Automated Pytest suite (Isolated SQLite)
│   ├── conftest.py               # Fixtures, in-memory DB engine, and TestClient
│   ├── test_certificates_api.py  # Tests for certificate routes and file downloads
│   ├── test_failure_handling.py  # Tests for per-certificate failure isolation
│   ├── test_generation_service.py# Tests for ReportLab PDF generation
│   ├── test_health.py            # Tests for health & readiness endpoints
│   ├── test_job_schema.py        # Tests for job request/response schema parsing
│   ├── test_jobs_api.py          # Tests for job submission and status API
│   ├── test_retry.py             # Tests for certificate retry state resets
│   ├── test_retry_api.py         # Tests for retry API endpoint
│   ├── test_validation.py        # Tests for Pydantic input validation
│   └── test_worker_safety.py     # Tests for atomic worker claim mechanism
├── .env                          # Local environment variable configuration
├── .env.example                  # Example environment variables template
├── .gitignore                    # Git ignore file
├── alembic.ini                   # Alembic configuration
├── docker-compose.yml            # Multi-container Docker Compose definition
├── Dockerfile                    # Docker build instructions for API and worker
├── requirements.txt              # Python package dependencies
└── README.md                     # Project documentation
```

---

## ⚙️ Environment Configuration Reference

The application is configured using environment variables loaded via Pydantic `BaseSettings`:

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` / `DB_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/certificates` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker and backend URL |
| `STORAGE_DIR` | `storage/certificates` | Local directory path where generated certificate PDFs are saved |

---

## 📄 License

This project is licensed under the MIT License.
