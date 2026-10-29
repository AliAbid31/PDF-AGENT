import html
import io
import re
import unicodedata
from datetime import datetime
from pypdf import PdfReader

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD_PATH = r"C:\Windows\Fonts\arialbd.ttf"
FONT_ITALIC_PATH = r"C:\Windows\Fonts\ariali.ttf"

if all(
    __import__("os").path.exists(path)
    for path in (FONT_PATH, FONT_BOLD_PATH, FONT_ITALIC_PATH)
):
    pdfmetrics.registerFont(TTFont("AliPDF", FONT_PATH))
    pdfmetrics.registerFont(TTFont("AliPDF-Bold", FONT_BOLD_PATH))
    pdfmetrics.registerFont(TTFont("AliPDF-Italic", FONT_ITALIC_PATH))
else:
    pdfmetrics.registerFontFamily("Helvetica", normal="Helvetica", bold="Helvetica-Bold")


def _safe_text(value: str) -> str:
    """Normalize extracted text without replacing Unicode characters with squares."""
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u25a0": "-",
        "\ufffd": "",
        "\u00a0": " ",
        "\u00d7": " x ",
        "\u2248": " approximately ",
        "\u2264": " <= ",
        "\u2265": " >= ",
        "\u2208": " in ",
        "\u2200": " for all ",
        "\u221e": " infinity ",
    }
    value = unicodedata.normalize("NFKC", value)
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = "".join(
        character
        for character in value
        if character in "\n\t" or ord(character) >= 32
    )
    value = "".join(
        character
        for character in value
        if unicodedata.category(character) not in {"So", "Sk"}
    )
    return value


def _font(name: str) -> str:
    try:
        pdfmetrics.getFont(name)
        return name
    except KeyError:
        return "Helvetica"


def _is_heading(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned or len(cleaned) > 100:
        return False
    if cleaned.endswith(":") or re.match(
        r"^(chapter|part|section|module|lesson|introduction|conclusion|page)\b",
        cleaned,
        re.IGNORECASE,
    ):
        return True
    if "|" in cleaned and len(cleaned) <= 120:
        return True
    words = re.findall(r"[A-Za-zÀ-ÿ]+", cleaned)
    return len(words) <= 8 and len(words) >= 2 and cleaned.isupper()


def _is_equation(line: str) -> bool:
    cleaned = line.strip()
    if len(cleaned) < 5 or len(cleaned) > 240:
        return False
    operators = sum(cleaned.count(char) for char in ("=", "≤", "≥", "∑", "/", "→"))
    variables = len(re.findall(r"\b[a-zA-Z](?:_[a-zA-Z0-9]+)?\b", cleaned))
    return operators >= 1 and variables >= 2


class _SingleLineEquation(Flowable):
    def __init__(self, value: str, max_width: float, font_name: str):
        super().__init__()
        self.value = value
        self.max_width = max_width
        self.font_name = font_name
        self.font_size = 10.5
        self.leading = 16
        self.width = max_width
        self.height = self.leading

    def wrap(self, available_width: float, available_height: float):
        self.max_width = min(self.max_width, available_width)
        while (
            pdfmetrics.stringWidth(self.value, self.font_name, self.font_size)
            > self.max_width
            and self.font_size > 6.5
        ):
            self.font_size -= 0.5
        self.leading = self.font_size + 5
        self.height = self.leading
        return available_width, self.height

    def draw(self):
        self.canv.setFont(self.font_name, self.font_size)
        self.canv.setFillColor(colors.HexColor("#1e293b"))
        self.canv.drawString(0, 2, self.value)


def clean_extracted_text(text: str) -> str:
    """Recover readable structure from PDF extraction that lost line breaks."""
    text = _safe_text(text)
    text = text.replace("\r", "\n")
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    text = re.sub(r"(?m)^\s*\[?[^]\n|]+\s*\|\s*Page\s+\d+\]?\s*$", "", text)
    text = re.sub(r"(?m)^\s*Page\s+\d+\s*$", "", text)
    text = re.sub(
        r"(?m)^\s*\d+\s*/\s*\d+\s+.+?(?:Chapter|chapter).*$",
        "",
        text,
    )
    text = re.sub(r"(?m)^\s*\d+\s*/\s*\d+\s*$", "", text)
    text = re.sub(r"(?m)^\s*(?:Page\s+)?\d+\s*-\s*.+$", "", text)
    text = re.sub(r"(?m)^\s*(?:Page\s+)?\d+\s*-\s*.+$", "", text)
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    text = re.sub(r"[\uFFF0-\uFFFF]", "", text)
    text = re.sub(r"(?m)^\s*(?:unn|uii|bi-|n\s*[Σ∑]|[(),])\s*$", "", text)
    text = re.sub(r"(?m)^\s*\\?\s*fe\d+\s*$", "", text)
    text = re.sub(r"(?<=\w)\?+(?=\w)", " x ", text)
    text = re.sub(r"\?{3,}", "", text)
    text = re.sub(r"(?<!\d)\s+(?=\d+\.\d+\s+[A-Z])", "\n\n", text)
    text = re.sub(r"(?<!\d)\s+(?=\d+\.\s+[A-Za-z])", "\n", text)
    text = re.sub(r"(?<=:)\s+(?=[A-Z][A-Za-z ]{3,40}:)", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


_clean_extracted_text = clean_extracted_text


def review_summary_text(text: str) -> str:
    """Turn extracted equation fragments into readable notes before rendering."""
    reviewed = unicodedata.normalize("NFKC", text).replace("\r", "\n")
    reviewed = re.sub(
        r"xk\s*=\s*\n?\s*det\s*\(\s*a\s*1\s*,\s*\.\.\.\s*,\s*b.*?"
        r"k-th column.*?\n?\s*,\s*\.\.\.\s*,\s*a\s*n\s*\)\s*\n?"
        r"\s*det\s*A\s*,?\s*k\s*=\s*1\s*,\s*\.\.\.\s*,\s*n\s*\.",
        "x_k = det(a_1, ..., b, ..., a_n) / det(A),  k = 1, ..., n.",
        reviewed,
        flags=re.IGNORECASE | re.DOTALL,
    )
    reviewed = re.sub(
        r"xn\s*=\s*bn\s*\n\s*unn\s*,?\s*x\s*i\s*=\s*1\s*\n\s*uii"
        r".*?(?:\n\s*)?j\s*=\s*i\s*\+\s*1.*?\)?",
        "x_n = b_n / u_nn;  x_i = (b_i - sum(u_ij * x_j, j=i+1..n)) / u_ii,  i=n-1,...,1.",
        reviewed,
        flags=re.IGNORECASE | re.DOTALL,
    )
    reviewed = clean_extracted_text(reviewed)
    reviewed = re.sub(
        r"(?m)^\s*xn\s*=\s*bn\s*$",
        "Back substitution starts with: x_n = b_n / u_nn.",
        reviewed,
    )
    reviewed = re.sub(
        r"(?m)^\s*,?\s*x\s*i\s*=\s*1\s*$",
        "Then solve the remaining variables from i = n - 1 down to 1.",
        reviewed,
    )
    reviewed = re.sub(
        r"(?m)^\s*bi\s*-\s*$",
        "Each step subtracts the already computed terms from b_i.",
        reviewed,
    )
    reviewed = re.sub(
        r"(?m)^\s*([ynx])\s*[?□]+\s*$",
        r"\1 (mathematical expression shown in the source document).",
        reviewed,
    )
    reviewed = re.sub(
        r"(?m)^\s*(?:n|j\s*=\s*i\s*\+\s*1|uij\s*xj)\s*$",
        "",
        reviewed,
    )
    reviewed = re.sub(r"(?m)^\s*\)?\s*$", "", reviewed)
    reviewed = re.sub(
        r"(?m)^\s*,?\s*i\s*=\s*n\s*[−-]\s*1\s*,\s*\.\.\.\s*,\s*1\s*\.\s*$",
        "",
        reviewed,
    )
    reviewed = re.sub(r"[?□]{2,}", "", reviewed)
    reviewed = re.sub(r"(?m)^\s*[-,()]+\s*$", "", reviewed)
    return re.sub(r"\n{3,}", "\n\n", reviewed).strip()


def validate_pdf_bytes(pdf_bytes: bytes) -> None:
    """Prevent delivery of a PDF whose extracted text is visibly corrupted."""
    pages = PdfReader(io.BytesIO(pdf_bytes)).pages
    extracted = "\n".join(page.extract_text() or "" for page in pages)
    if "\ufffd" in extracted or re.search(r"[?□]{3,}", extracted):
        raise ValueError("Generated PDF failed text-quality review.")


def _paragraphs(text: str) -> list[tuple[str, str]]:
    elements: list[tuple[str, str]] = []
    previous_heading = ""
    for raw_block in re.split(r"\n\s*\n", clean_extracted_text(text)):
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].casefold() in {"course resume", "document summary"}:
            lines = lines[1:]
        if not lines:
            continue
        source = lines[0]
        if re.match(r"^\[.+\|\s*Page\s+\d+\]$", source):
            elements.append(("source", source[1:-1]))
            lines = lines[1:]
        if not lines:
            continue
        paragraph_lines: list[str] = []
        for line in lines:
            if _is_heading(line) or _is_equation(line) or line.startswith(("-", "*", "•")) or re.match(r"^\d+\.\s", line):
                if paragraph_lines:
                    elements.append(("body", " ".join(paragraph_lines)))
                    paragraph_lines = []
            if _is_heading(line):
                if line.casefold() == previous_heading:
                    continue
                elements.append(("heading", line))
                previous_heading = line.casefold()
            elif _is_equation(line):
                elements.append(("equation", line))
            elif line.startswith(("-", "*", "•")):
                elements.append(("bullet", line.lstrip("-*• ").strip()))
            elif re.match(r"^\d+\.\s", line):
                elements.append(("bullet", re.sub(r"^\d+\.\s*", "", line)))
            else:
                paragraph_lines.append(line)
        if paragraph_lines:
            elements.append(("body", " ".join(paragraph_lines)))
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
            fontName=_font("AliPDF-Bold"),
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
            fontName=_font("AliPDF"),
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
            fontName=_font("AliPDF-Bold"),
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
            fontName=_font("AliPDF"),
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
            fontName=_font("AliPDF-Italic"),
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

    for kind, value in _paragraphs(text):
        escaped = html.escape(value)
        if kind == "heading":
            story.append(Paragraph(escaped, styles["SectionHeading"]))
        elif kind == "source":
            story.append(Paragraph(escaped, styles["SourceNote"]))
        elif kind == "bullet":
            story.append(Paragraph(f"- {escaped}", styles["BulletReadable"]))
        elif kind == "equation":
            story.append(
                _SingleLineEquation(
                    value,
                    document.width,
                    _font("AliPDF"),
                )
            )
            story.append(Spacer(1, 4))
        else:
            story.append(Paragraph(escaped, styles["BodyReadable"]))

    document.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    packet.seek(0)
    return packet.getvalue()
