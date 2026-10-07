from datetime import datetime, timezone
from uuid import UUID

from celery import Task
from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.models import (
    Certificate,
    CertificateStatus,
    GenerationJob,
    JobStatus,
)
from app.services.certificate_service import generate_certificate_pdf
from app.services.storage_service import certificate_file_path
from app.workers.celery_app import celery_app


class CertificateGenerationTask(Task):
    autoretry_for = ()
    max_retries = 0


def claim_certificate(certificate_id: UUID) -> bool:
    """Atomically claim a pending certificate.

    Returns True only for the worker that successfully changes
    PENDING -> PROCESSING.
    """
    db = SessionLocal()
    try:
        result = db.execute(
            update(Certificate)
            .where(Certificate.id == certificate_id)
            .where(Certificate.status == CertificateStatus.PENDING)
            .values(status=CertificateStatus.PROCESSING)
        )
        db.commit()
        return result.rowcount == 1
    finally:
        db.close()


def process_one_certificate(
    job_id: UUID,
    certificate_id: UUID,
) -> None:
    db = SessionLocal()

    try:
        job = db.scalar(
            select(GenerationJob).where(GenerationJob.id == job_id)
        )
        certificate = db.scalar(
            select(Certificate).where(Certificate.id == certificate_id)
        )

        if job is None or certificate is None:
            return

        output_path = certificate_file_path(
            job.id,
            certificate.id,
        )

        try:
            generate_certificate_pdf(
                output_path=output_path,
                recipient_name=certificate.recipient_name,
                event_name=job.event_name,
                certificate_title=job.certificate_title,
            )

            certificate.status = CertificateStatus.SUCCESS
            certificate.file_path = str(output_path)
            certificate.error_message = None
            certificate.completed_at = datetime.now(timezone.utc)

            job.successful_count += 1
            job.processed_count += 1

        except Exception as exc:
            certificate.status = CertificateStatus.FAILED
            certificate.error_message = str(exc)
            certificate.completed_at = datetime.now(timezone.utc)

            job.failed_count += 1
            job.processed_count += 1

        db.commit()

    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=CertificateGenerationTask,
    name="process_generation_job",
)
def process_generation_job(self, job_id: str) -> None:
    db = SessionLocal()

    try:
        job_uuid = UUID(job_id)

        job = db.scalar(
            select(GenerationJob).where(GenerationJob.id == job_uuid)
        )

        if job is None:
            return

        # A duplicate job task should not restart a completed job.
        if job.status in {
            JobStatus.COMPLETED,
            JobStatus.COMPLETED_WITH_ERRORS,
            JobStatus.FAILED,
        }:
            return

        job.status = JobStatus.PROCESSING
        job.started_at = job.started_at or datetime.now(timezone.utc)
        db.commit()

        certificate_ids = db.scalars(
            select(Certificate.id)
            .where(Certificate.job_id == job_uuid)
            .where(Certificate.status == CertificateStatus.PENDING)
            .order_by(Certificate.created_at, Certificate.id)
        ).all()

    finally:
        db.close()

    for certificate_id in certificate_ids:
        # Only one worker can atomically claim a PENDING certificate.
        if claim_certificate(certificate_id):
            process_one_certificate(
                job_id=job_uuid,
                certificate_id=certificate_id,
            )

    finalize_job(job_uuid)


def finalize_job(job_id: UUID) -> None:
    db = SessionLocal()

    try:
        job = db.scalar(
            select(GenerationJob).where(GenerationJob.id == job_id)
        )

        if job is None:
            return

        # Do not finalize while another worker still owns a certificate.
        remaining = db.scalar(
            select(Certificate.id)
            .where(Certificate.job_id == job_id)
            .where(
                Certificate.status.in_(
                    [
                        CertificateStatus.PENDING,
                        CertificateStatus.PROCESSING,
                    ]
                )
            )
            .limit(1)
        )

        if remaining is not None:
            db.commit()
            return

        if job.failed_count == 0 and job.successful_count == job.total_count:
            job.status = JobStatus.COMPLETED
        elif job.successful_count == 0 and job.failed_count == job.total_count:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS

        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    finally:
        db.close()
