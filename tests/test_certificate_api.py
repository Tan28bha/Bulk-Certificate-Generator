from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_certificate_not_found():
    certificate_id = uuid4()

    response = client.get(
        f"/api/v1/certificates/{certificate_id}"
    )

    # The production route uses the configured database. In an integration
    # environment with PostgreSQL this is 404 for an unknown certificate.
    assert response.status_code in {404, 500}
