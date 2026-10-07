import pytest

from app.models import Certificate, CertificateStatus, GenerationJob
from app.workers.retry import reset_failed_certificate


def test_failed_certificate_can_be_reset_for_retry(db_session):
    job = GenerationJob(
        event_name="Test Event",
        certificate_title="Certificate",
        total_count=1,
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

    result = reset_failed_certificate(
        db_session,
        certificate.id,
    )

    assert result.status == CertificateStatus.PENDING
    assert result.error_message is None
    assert result.completed_at is None


def test_successful_certificate_cannot_be_retried(db_session):
    job = GenerationJob(
        event_name="Test Event",
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

    with pytest.raises(ValueError):
        reset_failed_certificate(
            db_session,
            certificate.id,
        )
