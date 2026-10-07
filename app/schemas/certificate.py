from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    certificate_id: UUID
    job_id: UUID
    recipient_name: str
    recipient_email: str
    status: str
    file_path: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
