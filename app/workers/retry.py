from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Certificate, CertificateStatus, GenerationJob


def reset_failed_certificate(
    db: Session,
    certificate_id: UUID,
) -> Certificate:
    """Move one failed certificate back to PENDING for retry."""
    certificate = db.scalar(
        select(Certificate).where(Certificate.id == certificate_id)
    )

    if certificate is None:
        raise ValueError("Certificate not found.")

    if certificate.status != CertificateStatus.FAILED:
        raise ValueError("Only FAILED certificates can be retried.")

    job = db.scalar(
        select(GenerationJob).where(GenerationJob.id == certificate.job_id)
    )

    if job is None:
        raise ValueError("Generation job not found.")

    certificate.status = CertificateStatus.PENDING
    certificate.error_message = None
    certificate.completed_at = None

    # Move the batch back into an active state and remove this failure
    # from the aggregate counters because it will be processed again.
    if job.failed_count > 0:
        job.failed_count -= 1
    if job.processed_count > 0:
        job.processed_count -= 1

    job.completed_at = None
    from app.models import JobStatus
    job.status = JobStatus.PROCESSING

    db.commit()
    db.refresh(certificate)

    return certificate
