from app.models import (
    Certificate,
    CertificateStatus,
    GenerationJob,
)


def test_retry_failed_certificate(
    client,
    db_session,
    monkeypatch,
):
    job = GenerationJob(
        event_name="Python Workshop",
        certificate_title="Certificate",
        total_count=1,
        failed_count=1,
        processed_count=1,
    )
    db_session.add(job)
    db_session.flush()

    certificate = Certificate(
        job_id=job.id,
        recipient_name="Tanmay",
        recipient_email="tanmay@example.com",
        status=CertificateStatus.FAILED,
        error_message="Temporary failure",
    )
    db_session.add(certificate)
    db_session.commit()
    db_session.refresh(certificate)

    queued = []

    monkeypatch.setattr(
        "app.api.routes.certificates.process_generation_job.delay",
        lambda job_id: queued.append(job_id),
    )

    response = client.post(
        f"/api/v1/certificates/{certificate.id}/retry"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"
    assert queued == [str(job.id)]


def test_retry_successful_certificate_returns_conflict(
    client,
    db_session,
):
    job = GenerationJob(
        event_name="Python Workshop",
        certificate_title="Certificate",
        total_count=1,
    )
    db_session.add(job)
    db_session.flush()

    certificate = Certificate(
        job_id=job.id,
        recipient_name="Tanmay",
        recipient_email="tanmay@example.com",
        status=CertificateStatus.SUCCESS,
    )
    db_session.add(certificate)
    db_session.commit()
    db_session.refresh(certificate)

    response = client.post(
        f"/api/v1/certificates/{certificate.id}/retry"
    )

    assert response.status_code == 409
