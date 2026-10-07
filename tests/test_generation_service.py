from pathlib import Path

from app.services.certificate_service import generate_certificate_pdf


def test_certificate_pdf_is_generated(tmp_path: Path):
    output_path = tmp_path / "certificate.pdf"

    generate_certificate_pdf(
        output_path=output_path,
        recipient_name="Tanmay Bhadauria",
        event_name="Python Workshop",
        certificate_title="Certificate of Participation",
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
