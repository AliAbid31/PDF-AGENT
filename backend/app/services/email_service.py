import base64
import resend
from app.core.config import settings

def send_email(to_email: str, subject: str, text: str, pdf_bytes: bytes, filename: str):
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    params = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "text": text,
        "attachments": [
            {
                "filename": filename,
                "content": pdf_base64
            }
        ]  
    }

    return resend.Emails.send(params)