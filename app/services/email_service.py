# backend/app/services/email_service.py - ENHANCED WITH MULTI-PORT FALLBACK
from app.core.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

def send_email_with_fallback(to_email: str, subject: str, html_body: str, html_content: str = None):
    """
    Send email with HTML content using multiple port fallback
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML content for the email body
        html_content: Alternative HTML content (for backward compatibility)
    """
    try:
        if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning(f"SMTP not configured; skipping email to {to_email}")
            return False
        
        # Use html_content if provided, otherwise use html_body
        final_html_content = html_content if html_content is not None else html_body
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.FROM_EMAIL or settings.SMTP_USER
        msg["To"] = to_email
        
        # Create both plain text and HTML versions
        plain_text = "Please view this email in an HTML-compatible email client."
        
        # Attach plain text version
        part1 = MIMEText(plain_text, "plain")
        msg.attach(part1)
        
        # Attach HTML version
        part2 = MIMEText(final_html_content, "html")
        msg.attach(part2)
        
        # ✅ MULTI-PORT FALLBACK STRATEGY - ONLY CHANGED TIMEOUT FROM 10s TO 3s
        ports_to_try = [587, 465, 25, 2525, 8025]
        smtp_servers = {
            587: "Standard TLS port",
            465: "SSL port", 
            25: "Standard SMTP port",
            2525: "Alternative TLS port",
            8025: "Development port"
        }
        
        last_exception = None
        
        for port in ports_to_try:
            try:
                logger.info(f"🔄 Attempting to send email via port {port} ({smtp_servers.get(port, 'Unknown')})")
                
                if port == 465:
                    # SSL connection
                    s = smtplib.SMTP_SSL(settings.SMTP_HOST, port, timeout=3)  # ✅ ONLY CHANGED: 10s → 3s
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                else:
                    # TLS connection
                    s = smtplib.SMTP(settings.SMTP_HOST, port, timeout=3)  # ✅ ONLY CHANGED: 10s → 3s
                    s.starttls()
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                
                # Send the email
                s.sendmail(msg["From"], [to_email], msg.as_string())
                s.quit()
                
                logger.info(f"✅ Email sent successfully to: {to_email} via port {port}")
                return True
                
            except Exception as e:
                last_exception = e
                logger.warning(f"❌ Failed to send via port {port}: {str(e)}")
                continue
        
        # If all ports failed
        logger.error(f"❌ All ports failed for {to_email}. Last error: {str(last_exception)}")
        return False
            
    except Exception as e:
        logger.error(f"❌ Error in send_email for {to_email}: {str(e)}")
        return False

# Keep original function for backward compatibility
def send_email(to_email: str, subject: str, html_body: str, html_content: str = None):
    """Original function that now uses the enhanced version"""
    return send_email_with_fallback(to_email, subject, html_body, html_content)