from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_pdf_report(submission: dict, output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Keyframe Reverse Search Report")
    y -= 24

    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Submission ID: {submission.get('id')}")
    y -= 16
    c.drawString(40, y, f"Status: {submission.get('status')}")
    y -= 16
    c.drawString(40, y, f"Created: {submission.get('createdAt')}")
    y -= 22

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Earliest Known Matches")
    y -= 18

    c.setFont("Helvetica", 9)
    for item in submission.get("earliestKnownMatches", [])[:40]:
        line = f"[{item.get('engine')}] {item.get('publishedAt') or 'unknown date'} - {item.get('url')}"
        c.drawString(40, y, line[:120])
        y -= 13
        if y < 50:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)

    c.save()
