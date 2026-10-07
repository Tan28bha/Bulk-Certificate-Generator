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

## Phase 2: Database

Apply the initial migration after PostgreSQL is running:

```bash
docker compose run --rm api alembic upgrade head
```

The initial schema contains:

- `generation_jobs`
- `certificates`

A generation job has many certificate records. Individual certificate failures are stored independently so one failure does not stop the rest of the batch.

Idempotency is represented by a unique `idempotency_key` on `generation_jobs`.

## Phase 3: Create a Generation Job

Create a job:

```http
POST /api/v1/jobs
```

Optional idempotency header:

```http
Idempotency-Key: unique-client-request-id
```

Example request:

```json
{
  "event_name": "Python Workshop 2026",
  "certificate_title": "Certificate of Participation",
  "recipients": [
    {
      "name": "Tanmay Bhadauria",
      "email": "tanmay@example.com"
    },
    {
      "name": "Rahul Sharma",
      "email": "rahul@example.com"
    }
  ]
}
```

The API validates all recipient data using Pydantic. A valid request creates one `generation_jobs` row and one `certificates` row per recipient.

If the same `Idempotency-Key` is submitted again, the existing job is returned instead of creating another batch.

## Phase 4: Background Certificate Generation

A successful job is queued to Celery after the database transaction commits.

The worker:

1. Moves the job to `PROCESSING`.
2. Processes each pending certificate independently.
3. Generates a PDF using the predefined ReportLab template.
4. Stores the generated file under `storage/certificates/<job_id>/`.
5. Marks each certificate as `SUCCESS` or `FAILED`.
6. Updates processed/success/failed counters.
7. Marks the overall job as `COMPLETED`, `FAILED`, or `COMPLETED_WITH_ERRORS`.

A failure for one certificate is caught and recorded without stopping the remaining certificates.

## Phase 5: Certificate Retrieval

List all certificate results for a job:

```http
GET /api/v1/jobs/{job_id}/certificates
```

Download an individual successful certificate:

```http
GET /api/v1/certificates/{certificate_id}
```

Only certificates with `SUCCESS` status and an existing PDF file can be downloaded. Failed or still-processing certificates return an appropriate error response.

## Phase 6: Test Suite

The test suite now covers:

- Job creation
- Request validation
- Idempotent job retries
- Job status/progress
- Missing jobs
- PDF generation
- Individual certificate failure isolation
- Certificate listing
- Successful PDF download
- Failed certificate download protection
- Missing certificate handling

Run:

```bash
pytest -q
```

The API tests use an isolated SQLite database for speed and do not require a running PostgreSQL instance.

## Phase 7: Worker Safety and Retry Design

### Duplicate processing protection

Before processing a certificate, a worker atomically changes:

```text
PENDING -> PROCESSING
```

using a conditional database update.

Only the worker that successfully changes one row is allowed to generate that certificate. A second worker attempting to claim the same certificate gets zero updated rows and skips it.

This protects against duplicate processing if the same Celery job is accidentally delivered more than once.

### Individual certificate retry

A failed certificate can be reset:

```text
FAILED -> PENDING
```

Successful certificates are never reset, so a retry only regenerates failed work.

The retry boundary is deliberately at the individual certificate level rather than rerunning the entire bulk job.

## Phase 8: Retry and Health APIs

Retry a failed certificate:

```http
POST /api/v1/certificates/{certificate_id}/retry
```

Only `FAILED` certificates can be retried. The API resets that certificate to `PENDING` and queues the existing generation job. Successful certificates are not regenerated.

### Health

Liveness:

```http
GET /health
```

Readiness:

```http
GET /health/ready
```

Readiness checks both PostgreSQL and Redis and returns HTTP `503` when either dependency is unavailable.

## Assignment Requirement Checklist

| Requirement | Implementation |
|---|---|
| Accept bulk generation request | `POST /api/v1/jobs` |
| Validate recipient data | Pydantic `RecipientCreate` |
| Predefined certificate template | ReportLab template |
| Generate one certificate per recipient | Celery worker |
| Bulk processing | Redis + Celery |
| Track generation status | `GenerationJob.status` |
| Track progress | processed/success/failure counters + percentage |
| Identify individual failures | `Certificate.status` + `error_message` |
| One failure must not stop others | Per-certificate exception boundary |
| Retrieve generated certificates | Certificate listing + PDF download |
| Retry failed certificates | `POST /api/v1/certificates/{id}/retry` |
| Idempotent job retries | `Idempotency-Key` + unique DB constraint |
| Relational database | PostgreSQL |
| Automated tests | Pytest |
| Setup/run documentation | This README |
| Health checks | `/health` and `/health/ready` |

## API Example

### Create a bulk generation job

```bash
curl -X POST http://localhost:8000/api/v1/jobs   -H "Content-Type: application/json"   -H "Idempotency-Key: workshop-2026-001"   -d '{
    "event_name": "Python Workshop 2026",
    "certificate_title": "Certificate of Participation",
    "recipients": [
      {
        "name": "Tanmay Bhadauria",
        "email": "tanmay@example.com"
      },
      {
        "name": "Rahul Sharma",
        "email": "rahul@example.com"
      }
    ]
  }'
```

### Check progress

```bash
curl http://localhost:8000/api/v1/jobs/<JOB_ID>
```

### List certificate results

```bash
curl http://localhost:8000/api/v1/jobs/<JOB_ID>/certificates
```

### Download a certificate

```bash
curl -o certificate.pdf   http://localhost:8000/api/v1/certificates/<CERTIFICATE_ID>
```

### Retry one failed certificate

```bash
curl -X POST   http://localhost:8000/api/v1/certificates/<CERTIFICATE_ID>/retry
```

## Architecture Decisions

### Why asynchronous processing?

Certificate generation is CPU/file-work that can become expensive for large batches. The API creates the job and returns immediately while Celery workers process certificates asynchronously.

### Why PostgreSQL?

The assignment requires a relational database. PostgreSQL provides transactions, constraints, UUIDs, indexes, and reliable persistence for job/certificate state.

### Why Redis + Celery?

Redis acts as the broker and Celery provides durable worker-based task processing. This avoids keeping an HTTP request open for the entire bulk operation and allows worker scaling.

### Why store PDFs outside PostgreSQL?

The relational database stores metadata and state. PDF files are stored separately under the configured storage directory. In production, the same storage interface can be backed by object storage such as S3.

### Why per-certificate state?

A bulk job can partially succeed. Storing status independently for each recipient allows successful certificates to remain available even when other certificates fail.

### Failure isolation

Each certificate has its own processing boundary. A generation exception is recorded on that certificate and the worker continues with the remaining batch.

### Idempotency

Clients can provide `Idempotency-Key`. The key is unique in PostgreSQL, so network retries do not create duplicate generation jobs.

### Duplicate worker protection

Before generation, a worker atomically changes `PENDING` to `PROCESSING`. Only the worker that successfully performs this conditional update processes the certificate.

## Production Storage Evolution

The current assignment uses local filesystem storage for simplicity:

```text
storage/certificates/<job_id>/<certificate_id>.pdf
```

For production deployment, the storage service can be replaced with an S3-compatible object store. The database would continue to store the object key rather than the PDF binary.

## Running

Start the stack:

```bash
docker compose up --build -d
```

Apply migrations:

```bash
docker compose run --rm api alembic upgrade head
```

Open Swagger:

```text
http://localhost:8000/docs
```

Run tests:

```bash
pytest -q
```
