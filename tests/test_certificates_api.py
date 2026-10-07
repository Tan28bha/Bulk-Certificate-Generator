from pathlib import Path
from uuid import uuid4

from app.models import (
    Certificate,
    CertificateStatus,
    GenerationJob,
    JobStatus,
)


def create_job(db_session):
    job = GenerationJob(
        event_name="Python Workshop",
        certificate_title="Certificate",
        status=JobStatus.COMPLETED,
        total_count=1,
        processed_count=1,
        successful_count=1,
        failed_count=0,
    )
    db_session.add(job)
    db_session.flush()
    return job


def test_list_job_certificates(client, db_session):
    job = create_job(db_session)

    certificate = Certificate(
        job_id=job.id,
        recipient_name="Tanmay Bhadauria",
        recipient_email="tanmay@example.com",
        status=CertificateStatus.SUCCESS,
        file_path="/tmp/certificate.pdf",
    )

    db_session.add(certificate)
    db_session.commit()

    response = client.get(
        f"/api/v1/jobs/{job.id}/certificates"
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["recipient_name"] == "Tanmay Bhadauria"
    assert body[0]["status"] == "SUCCESS"


def test_download_generated_certificate(
    client,
    db_session,
    tmp_path,
):
    job = create_job(db_session)

    pdf_path = Path(tmp_path) / "certificate.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    certificate = Certificate(
        job_id=job.id,
        recipient_name="Tanmay Bhadauria",
        recipient_email="tanmay@example.com",
        status=CertificateStatus.SUCCESS,
        file_path=str(pdf_path),
    )

    db_session.add(certificate)
    db_session.commit()
    db_session.refresh(certificate)

    response = client.get(
        f"/api/v1/certificates/{certificate.id}"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 test"


def test_failed_certificate_cannot_be_downloaded(
    client,
    db_session,
):
    job = create_job(db_session)

    certificate = Certificate(
        job_id=job.id,
        recipient_name="Failed User",
        recipient_email="failed@example.com",
        status=CertificateStatus.FAILED,
        error_message="PDF generation failed",
    )

    db_session.add(certificate)
    db_session.commit()
    db_session.refresh(certificate)

    response = client.get(
        f"/api/v1/certificates/{certificate.id}"
    )

    assert response.status_code == 409


def test_missing_certificate_returns_404(
    client,
):
    response = client.get(
        f"/api/v1/certificates/{uuid4()}"
    )

    assert response.status_code == 404
