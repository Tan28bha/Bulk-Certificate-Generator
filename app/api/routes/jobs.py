from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import GenerationJob
from app.schemas.job import GenerationJobCreate, GenerationJobResponse
from app.services.job_service import (
    create_generation_job,
    get_job_by_idempotency_key,
)
from app.workers.tasks import process_generation_job

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


def build_job_response(job, message: str) -> GenerationJobResponse:
    progress = (
        round((job.processed_count / job.total_count) * 100, 2)
        if job.total_count
        else 0.0
    )

    return GenerationJobResponse(
        job_id=job.id,
        status=job.status.value,
        total=job.total_count,
        processed=job.processed_count,
        successful=job.successful_count,
        failed=job.failed_count,
        progress=progress,
        message=message,
    )


@router.post(
    "",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    payload: GenerationJobCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    if idempotency_key:
        existing_job = get_job_by_idempotency_key(db, idempotency_key)

        if existing_job:
            return build_job_response(
                existing_job,
                "An existing job was found for this idempotency key.",
            )

    try:
        job = create_generation_job(
            db=db,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except IntegrityError:
        db.rollback()

        if idempotency_key:
            existing_job = get_job_by_idempotency_key(
                db,
                idempotency_key,
            )

            if existing_job:
                return build_job_response(
                    existing_job,
                    "An existing job was found for this idempotency key.",
                )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create generation job.",
        )

    # Queue only after the DB transaction has successfully committed.
    process_generation_job.delay(str(job.id))

    return build_job_response(
        job,
        "Certificate generation job created and queued successfully.",
    )


@router.get(
    "/{job_id}",
    response_model=GenerationJobResponse,
)
def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    job = db.scalar(
        select(GenerationJob).where(GenerationJob.id == job_id)
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    return build_job_response(
        job,
        "Generation job status retrieved successfully.",
    )
