from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Certificate, CertificateStatus, GenerationJob
from app.schemas.certificate import CertificateResponse
from app.workers.retry import reset_failed_certificate
from app.workers.tasks import process_generation_job

router = APIRouter(prefix="/api/v1", tags=["Certificates"])


@router.get(
    "/jobs/{job_id}/certificates",
    response_model=list[CertificateResponse],
)
def list_job_certificates(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    job_exists = db.scalar(
        select(GenerationJob.id).where(GenerationJob.id == job_id)
    )

    if job_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    certificates = db.scalars(
        select(Certificate)
        .where(Certificate.job_id == job_id)
        .order_by(Certificate.created_at, Certificate.id)
    ).all()

    return [
        CertificateResponse(
            certificate_id=certificate.id,
            job_id=certificate.job_id,
            recipient_name=certificate.recipient_name,
            recipient_email=certificate.recipient_email,
            status=certificate.status.value,
            file_path=certificate.file_path,
            error_message=certificate.error_message,
            created_at=certificate.created_at,
            completed_at=certificate.completed_at,
        )
        for certificate in certificates
    ]


@router.post(
    "/certificates/{certificate_id}/retry",
    response_model=CertificateResponse,
)
def retry_certificate(
    certificate_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        certificate = reset_failed_certificate(
            db,
            certificate_id,
        )
    except ValueError as exc:
        message = str(exc)

        if message == "Certificate not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )

    process_generation_job.delay(str(certificate.job_id))

    return CertificateResponse(
        certificate_id=certificate.id,
        job_id=certificate.job_id,
        recipient_name=certificate.recipient_name,
        recipient_email=certificate.recipient_email,
        status=certificate.status.value,
        file_path=certificate.file_path,
        error_message=certificate.error_message,
        created_at=certificate.created_at,
        completed_at=certificate.completed_at,
    )


@router.get("/certificates/{certificate_id}")
def download_certificate(
    certificate_id: UUID,
    db: Session = Depends(get_db),
):
    certificate = db.scalar(
        select(Certificate).where(Certificate.id == certificate_id)
    )

    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )

    if certificate.status != CertificateStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Certificate is not available for download. "
                f"Current status: {certificate.status.value}."
            ),
        )

    if not certificate.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated certificate file was not found.",
        )

    file_path = Path(certificate.file_path)

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated certificate file was not found.",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"certificate-{certificate.id}.pdf",
    )
