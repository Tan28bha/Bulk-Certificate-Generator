from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RecipientCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


class GenerationJobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_name: str = Field(..., min_length=1, max_length=255)
    certificate_title: str = Field(..., min_length=1, max_length=255)
    recipients: list[RecipientCreate] = Field(
        ...,
        min_length=1,
        max_length=10_000,
    )


class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    status: str
    total: int
    processed: int
    successful: int
    failed: int
    progress: float
    message: str
