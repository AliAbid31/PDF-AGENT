import html
import io
import re
import unicodedata
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _safe_text(value: str) -> str:
    """Keep extracted PDF text readable with ReportLab's built-in fonts."""
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
        "\ufffd": "",
    }
    value = unicodedata.normalize("NFKC", value)
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value.encode("latin-1", "replace").decode("latin-1")


def _is_heading(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned or len(cleaned) > 100:
        return False
    if cleaned.endswith(":") or re.match(
        r"^(chapter|part|section|module|lesson|introduction|conclusion)\b",
        cleaned,
        re.IGNORECASE,
    ):
        return True
    words = re.findall(r"[A-Za-zÀ-ÿ]+", cleaned)
    return len(words) <= 8 and len(words) >= 2 and cleaned.isupper()


def _paragraphs(text: str) -> list[tuple[str, str]]:
    elements: list[tuple[str, str]] = []
    for raw_block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
        if not lines:
            continue
        source = lines[0]
        if re.match(r"^\[.+\|\s*Page\s+\d+\]$", source):
            elements.append(("source", source[1:-1]))
            lines = lines[1:]
        if not lines:
            continue
        if len(lines) == 1 and _is_heading(lines[0]):
            elements.append(("heading", lines[0]))
        elif all(line.startswith(("-", "*", "•")) for line in lines):
            elements.extend(("bullet", line.lstrip("-*• ").strip()) for line in lines)
        else:
            elements.append(("body", " ".join(lines)))
    return elements


def _draw_page_chrome(canvas, document) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#dbe3ee"))
    canvas.setLineWidth(0.6)
    canvas.line(document.leftMargin, height - 0.55 * inch, width - document.rightMargin, height - 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(document.leftMargin, 0.42 * inch, "ALI-PDF AI  |  Document summary")
    canvas.drawRightString(
        width - document.rightMargin,
        0.42 * inch,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def generate_pdf(title: str, text: str) -> bytes:
    packet = io.BytesIO()
    document = SimpleDocTemplate(
        packet,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.78 * inch,
        bottomMargin=0.7 * inch,
        title=_safe_text(title),
        author="ALI-PDF AI",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=31,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748b"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1d4ed8"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyReadable",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SourceNote",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            spaceBefore=2,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletReadable",
            parent=styles["BodyReadable"],
            leftIndent=14,
            firstLineIndent=-9,
            bulletIndent=0,
            spaceAfter=4,
        )
    )

    story = [
        Spacer(1, 0.75 * inch),
        Paragraph(html.escape(_safe_text(title)), styles["CoverTitle"]),
        Paragraph("A structured summary generated from your uploaded document", styles["CoverMeta"]),
        Spacer(1, 0.2 * inch),
        Table(
            [[Paragraph(
                f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}<br/>"
                "<b>Format:</b> Course summary",
                styles["CoverMeta"],
            )]],
            colWidths=[4.8 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#bfdbfe")),
                ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]),
        ),
        PageBreak(),
    ]

    for kind, value in _paragraphs(_safe_text(text)):
        escaped = html.escape(value)
        if kind == "heading":
            story.append(Paragraph(escaped, styles["SectionHeading"]))
        elif kind == "source":
            story.append(Paragraph(escaped, styles["SourceNote"]))
        elif kind == "bullet":
            story.append(Paragraph(f"- {escaped}", styles["BulletReadable"]))
        else:
            story.append(Paragraph(escaped, styles["BodyReadable"]))

    document.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    packet.seek(0)
    return packet.getvalue()
