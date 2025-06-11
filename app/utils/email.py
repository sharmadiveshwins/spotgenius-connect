import logging
import smtplib
from fastapi import FastAPI, HTTPException
from email.message import EmailMessage
from app.config import settings
from app.schema.emails import EmailSchema


logger = logging.getLogger(__name__)


def send_email(email: EmailSchema):

    msg = EmailMessage()
    msg.set_content(email.body)
    msg["Subject"] = email.subject
    msg["From"] = settings.SMTP_USERNAME
    msg["To"] = email.to_emails

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        # raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
        logger.critical(f"Failed to send email: {str(e)}")
        return {"message": "Email not sent."}

    return {"message": "Email sent successfully"}
