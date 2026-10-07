from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Certificate, GenerationJob
from app.schemas.job import GenerationJobCreate


def get_job_by_idempotency_key(
    db: Session,
    idempotency_key: str,
) -> GenerationJob | None:
    return db.scalar(
        select(GenerationJob).where(
            GenerationJob.idempotency_key == idempotency_key
        )
    )


def create_generation_job(
    db: Session,
    payload: GenerationJobCreate,
    idempotency_key: str | None = None,
) -> GenerationJob:
    job = GenerationJob(
        event_name=payload.event_name,
        certificate_title=payload.certificate_title,
        total_count=len(payload.recipients),
        idempotency_key=idempotency_key,
    )

    db.add(job)
    db.flush()

    certificates = [
        Certificate(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
        )
        for recipient in payload.recipients
    ]

    db.add_all(certificates)
    db.commit()
    db.refresh(job)

    return job
