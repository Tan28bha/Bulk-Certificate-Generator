from app.models import Certificate, GenerationJob


def valid_payload():
    return {
        "event_name": "Python Workshop 2026",
        "certificate_title": "Certificate of Participation",
        "recipients": [
            {
                "name": "Tanmay Bhadauria",
                "email": "tanmay@example.com",
            },
            {
                "name": "Rahul Sharma",
                "email": "rahul@example.com",
            },
        ],
    }


def test_create_generation_job(client, db_session, monkeypatch):
    queued = []

    monkeypatch.setattr(
        "app.api.routes.jobs.process_generation_job.delay",
        lambda job_id: queued.append(job_id),
    )

    response = client.post(
        "/api/v1/jobs",
        json=valid_payload(),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["status"] == "QUEUED"
    assert body["total"] == 2
    assert body["processed"] == 0
    assert body["successful"] == 0
    assert body["failed"] == 0

    job = db_session.query(GenerationJob).one()
    certificates = db_session.query(Certificate).all()

    assert str(job.id) == body["job_id"]
    assert len(certificates) == 2
    assert len(queued) == 1
    assert queued[0] == str(job.id)


def test_idempotent_retry_returns_existing_job(
    client,
    db_session,
    monkeypatch,
    idempotency_key,
):
    queued = []

    monkeypatch.setattr(
        "app.api.routes.jobs.process_generation_job.delay",
        lambda job_id: queued.append(job_id),
    )

    payload = valid_payload()

    first = client.post(
        "/api/v1/jobs",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )

    second = client.post(
        "/api/v1/jobs",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["job_id"] == second.json()["job_id"]

    assert db_session.query(GenerationJob).count() == 1
    assert db_session.query(Certificate).count() == 2
    assert len(queued) == 1


def test_get_job_status(client, db_session):
    from app.models import GenerationJob, JobStatus

    job = GenerationJob(
        event_name="Python Workshop",
        certificate_title="Certificate",
        status=JobStatus.PROCESSING,
        total_count=10,
        processed_count=6,
        successful_count=5,
        failed_count=1,
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(f"/api/v1/jobs/{job.id}")

    assert response.status_code == 200

    body = response.json()

    assert body["job_id"] == str(job.id)
    assert body["status"] == "PROCESSING"
    assert body["total"] == 10
    assert body["processed"] == 6
    assert body["successful"] == 5
    assert body["failed"] == 1


def test_get_missing_job(client):
    import uuid

    response = client.get(f"/api/v1/jobs/{uuid.uuid4()}")

    assert response.status_code == 404
