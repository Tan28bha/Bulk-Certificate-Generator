from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_certificate_pdf(
    output_path: Path,
    recipient_name: str,
    event_name: str,
    certificate_title: str,
) -> None:
    # This is the single predefined certificate template.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    pdf.setTitle(certificate_title)

    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 150, certificate_title)

    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(
        width / 2,
        height - 220,
        "This certificate is proudly presented to",
    )

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(
        width / 2,
        height - 280,
        recipient_name,
    )

    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(
        width / 2,
        height - 340,
        f"for participating in {event_name}",
    )

    date_text = datetime.now(timezone.utc).strftime("%d %B %Y")

    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(
        width / 2,
        130,
        date_text,
    )

    pdf.line(width / 2 - 70, 100, width / 2 + 70, 100)

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(width / 2, 80, "Organizer")

    pdf.save()
