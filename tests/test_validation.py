from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_missing_event_name_is_rejected():
    response = client.post(
        "/api/v1/jobs",
        json={
            "certificate_title": "Certificate",
            "recipients": [
                {
                    "name": "Tanmay Bhadauria",
                    "email": "tanmay@example.com",
                }
            ],
        },
    )

    assert response.status_code == 422


def test_invalid_email_is_rejected():
    response = client.post(
        "/api/v1/jobs",
        json={
            "event_name": "Python Workshop",
            "certificate_title": "Certificate",
            "recipients": [
                {
                    "name": "Tanmay Bhadauria",
                    "email": "not-an-email",
                }
            ],
        },
    )

    assert response.status_code == 422


def test_empty_recipients_are_rejected():
    response = client.post(
        "/api/v1/jobs",
        json={
            "event_name": "Python Workshop",
            "certificate_title": "Certificate",
            "recipients": [],
        },
    )

    assert response.status_code == 422
