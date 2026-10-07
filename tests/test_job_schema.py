from app.schemas.job import GenerationJobCreate


def test_valid_job_payload():
    payload = GenerationJobCreate(
        event_name="Python Workshop",
        certificate_title="Certificate of Participation",
        recipients=[
            {
                "name": "Tanmay Bhadauria",
                "email": "tanmay@example.com",
            }
        ],
    )

    assert payload.event_name == "Python Workshop"
    assert len(payload.recipients) == 1
    assert payload.recipients[0].name == "Tanmay Bhadauria"
