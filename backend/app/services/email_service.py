
import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple
from app.core.config import settings
import random

logger = logging.getLogger(__name__)

def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"

def send_email(
    to_email: str,
    subject: str,
    text: str,
    pdf_bytes: bytes,
    filename: str = "document.pdf",
) -> Tuple[bool, str]:
    """Send an email with a PDF attachment via Gmail SMTP."""

    if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
        msg = "EMAIL_ADDRESS or EMAIL_PASSWORD is not configured in .env"
        logger.error(msg)
        return False, msg

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{settings.SENDER_NAME} <{settings.EMAIL_ADDRESS}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px;">
                    <h2 style="color: #2563eb;">📄 Your document is ready!</h2>
                    <p>{text}</p>
                    <div style="background-color: #f8fafc; padding: 12px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; font-size: 14px; color: #64748b;">
                            📎 <strong>Attachment:</strong> {filename}
                        </p>
                    </div>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                    <p style="font-size: 12px; color: #94a3b8; text-align: center;">
                        Automatically generated and sent by <strong>Ali-PDF AI</strong>.
                    </p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        # 3. Attach the PDF file (converts raw bytes into an attachment)
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition", "attachment", filename=filename
        )
        msg.attach(pdf_attachment)

        # 4. Secure connection to the Gmail server
        with smtplib.SMTP(
            settings.SMTP_SERVER, settings.SMTP_PORT, timeout=15
        ) as server:
            server.starttls()  # Enable TLS encryption
            server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            server.send_message(msg)

        success_msg = f"Email with the PDF '{filename}' was successfully sent to {to_email}!"
        logger.info(success_msg)
        return True, success_msg

    except Exception as e:
        error_msg = f"Error while sending the email: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

def send_otp_email(to_email: str, otp_code: str, purpose: str):
    subject = (
        "Account Verification - Ali-PDF AI"
        if purpose == "verification"
        else "Password Reset - Ali-PDF AI"
    )
    title = (
        "Welcome to Ali-PDF AI !"
        if purpose == "verification"
        else "Password Reset Request"
    )
    action_text = (
        "Here is your code to verify your account:"
        if purpose == "verification"
        else "Here is your code to reset your password:"
    )

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 8px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #2563eb; text-align: center;">{title}</h2>
                <p style="font-size: 15px; color: #475569;">{action_text}</p>
                
                <div style="background-color: #eff6ff; border: 2px dashed #3b82f6; border-radius: 8px; padding: 15px; text-align: center; margin: 25px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1d4ed8;">{otp_code}</span>
                </div>
                
                <p style="font-size: 13px; color: #64748b; text-align: center;">⏱️ This code expires in <strong>30 minutes</strong>.</p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <p style="font-size: 11px; color: #94a3b8; text-align: center;">Si vous n'avez pas demandé ce code, ignorez cet email en toute sécurité.</p>
            </div>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = f"{settings.SENDER_NAME} <{settings.EMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(
        settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10
    ) as server:
        server.starttls()
        server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        server.send_message(msg)
