from uuid import uuid4

from app.models import Certificate, CertificateStatus, GenerationJob
from app.workers.tasks import claim_certificate


def test_only_one_worker_can_claim_certificate(
    db_session,
):
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
        status=CertificateStatus.PENDING,
    )
    db_session.add(certificate)
    db_session.commit()

    # The first claim succeeds.
    assert claim_certificate(certificate.id) is True

    # A second worker cannot claim the same certificate.
    assert claim_certificate(certificate.id) is False


def test_missing_certificate_claim_returns_false():
    assert claim_certificate(uuid4()) is False
