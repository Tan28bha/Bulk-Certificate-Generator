from pathlib import Path
from uuid import UUID

from app.core.config import get_settings

settings = get_settings()


def certificate_directory(job_id: UUID) -> Path:
    directory = Path(settings.storage_dir) / str(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def certificate_file_path(job_id: UUID, certificate_id: UUID) -> Path:
    return certificate_directory(job_id) / f"{certificate_id}.pdf"
