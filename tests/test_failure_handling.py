from pathlib import Path

from app.models import (
    Certificate,
    CertificateStatus,
    GenerationJob,
    JobStatus,
)
from app.workers.tasks import process_generation_job


def test_individual_certificate_failure_does_not_stop_job(
    db_session,
    monkeypatch,
    tmp_path,
):
    job = GenerationJob(
        event_name="Test Event",
        certificate_title="Certificate",
        total_count=3,
    )
    db_session.add(job)
    db_session.flush()

    certificates = [
        Certificate(
            job_id=job.id,
            recipient_name="Success One",
            recipient_email="one@example.com",
        ),
        Certificate(
            job_id=job.id,
            recipient_name="Failure",
            recipient_email="failure@example.com",
        ),
        Certificate(
            job_id=job.id,
            recipient_name="Success Two",
            recipient_email="two@example.com",
        ),
    ]

    db_session.add_all(certificates)
    db_session.commit()

    def fake_generate(
        output_path: Path,
        recipient_name: str,
        event_name: str,
        certificate_title: str,
    ):
        if recipient_name == "Failure":
            raise RuntimeError("Intentional test failure")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-test")

    monkeypatch.setattr(
        "app.workers.tasks.generate_certificate_pdf",
        fake_generate,
    )
    monkeypatch.setattr(
        "app.workers.tasks.certificate_file_path",
        lambda job_id, certificate_id: (
            tmp_path / f"{certificate_id}.pdf"
        ),
    )

    process_generation_job(str(job.id))

    db_session.expire_all()

    updated_job = db_session.get(GenerationJob, job.id)
    results = (
        db_session.query(Certificate)
        .filter(Certificate.job_id == job.id)
        .order_by(Certificate.recipient_name)
        .all()
    )

    assert updated_job.status == JobStatus.COMPLETED_WITH_ERRORS
    assert updated_job.processed_count == 3
    assert updated_job.successful_count == 2
    assert updated_job.failed_count == 1

    statuses = {
        certificate.recipient_name: certificate.status
        for certificate in results
    }

    assert statuses["Success One"] == CertificateStatus.SUCCESS
    assert statuses["Failure"] == CertificateStatus.FAILED
    assert statuses["Success Two"] == CertificateStatus.SUCCESS

    failure = next(
        certificate
        for certificate in results
        if certificate.recipient_name == "Failure"
    )

    assert failure.error_message == "Intentional test failure"
