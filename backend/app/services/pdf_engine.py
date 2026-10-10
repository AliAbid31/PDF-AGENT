import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_pdf(title: str, text: str) -> bytes:
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica-B", 16)
    can.drawString(50, 750, title)
    y = 710
    for line in text.split("/n"):
        can.drawString(50, y, line[:90])
        y -= 20
        if y < 50:
            can.showPage()
            y = 750

    can.save()
    packet.seek(0)
    return packet.getvalue()