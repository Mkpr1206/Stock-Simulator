"""
Email service — supports SendGrid (preferred) or SMTP fallback.
If EMAIL_ENABLED=false, emails are printed to console (dev mode).
"""
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from config import (
    EMAIL_ENABLED, SENDGRID_API_KEY, EMAIL_FROM, EMAIL_FROM_NAME,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, APP_URL
)


def _send_via_smtp(to_email: str, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())


def _send_via_sendgrid(to_email: str, subject: str, html_body: str):
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        mail = Mail(
            from_email=Email(EMAIL_FROM, EMAIL_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body)
        )
        sg.client.mail.send.post(request_body=mail.get())
    except ImportError:
        raise RuntimeError("sendgrid package not installed — pip install sendgrid")


def send_email(to_email: str, subject: str, html_body: str):
    """Main send function — auto-selects method or logs to console."""
    if not EMAIL_ENABLED:
        print(f"\n[EMAIL LOG] To: {to_email}")
        print(f"[EMAIL LOG] Subject: {subject}")
        print(f"[EMAIL LOG] Body preview: {html_body[:200]}...\n")
        return

    if SENDGRID_API_KEY:
        _send_via_sendgrid(to_email, subject, html_body)
    elif SMTP_USER:
        _send_via_smtp(to_email, subject, html_body)
    else:
        print(f"[EMAIL WARN] No email provider configured. Would send to {to_email}: {subject}")


# ── Email templates ────────────────────────────────────────────────

def _base_template(content: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #080a0c; color: #dde4ed; margin: 0; padding: 0; }}
  .wrapper {{ max-width: 560px; margin: 40px auto; background: #0d1117; border: 1px solid #1c2128; border-radius: 10px; overflow: hidden; }}
  .header {{ background: #0d1117; padding: 32px; text-align: center; border-bottom: 1px solid #1c2128; }}
  .logo {{ font-size: 28px; font-weight: 700; color: #dde4ed; letter-spacing: -0.5px; }}
  .logo span {{ color: #00d4c8; }}
  .body {{ padding: 32px; line-height: 1.7; color: #9aa5b4; }}
  .body h2 {{ color: #dde4ed; font-size: 20px; margin-bottom: 12px; }}
  .btn {{ display: inline-block; margin: 20px 0; padding: 13px 28px; background: #00d4c8; color: #080a0c; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 14px; letter-spacing: 0.5px; }}
  .footer {{ padding: 20px 32px; border-top: 1px solid #1c2128; font-size: 11px; color: #4a5568; text-align: center; }}
  .code {{ background: #161a1f; border: 1px solid #1c2128; border-radius: 6px; padding: 14px 20px; font-family: monospace; font-size: 24px; letter-spacing: 6px; color: #00d4c8; text-align: center; margin: 16px 0; }}
</style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <div class="logo">Stock<span>Sim</span></div>
    </div>
    <div class="body">{content}</div>
    <div class="footer">
      StockSim — Learn to trade. Risk nothing real.<br>
      This is an automated message. No real money is ever involved.
    </div>
  </div>
</body>
</html>
"""


def send_verification_email(to_email: str, username: str, token: str):
    verify_url = f"{APP_URL}/auth/verify-email?token={token}"
    content = f"""
        <h2>Welcome to StockSim, {username}! 👋</h2>
        <p>You're almost ready to start trading with S$100,000 in SimBucks — no real money involved.</p>
        <p>Click below to verify your email and activate your account:</p>
        <a href="{verify_url}" class="btn">VERIFY EMAIL →</a>
        <p>Or paste this link in your browser:<br><small style="color:#4a5568">{verify_url}</small></p>
        <p>This link expires in <strong>24 hours</strong>.</p>
    """
    send_email(to_email, "Verify your StockSim account", _base_template(content))


def send_password_reset_email(to_email: str, username: str, token: str):
    reset_url = f"{APP_URL}/reset-password?token={token}"
    content = f"""
        <h2>Password Reset Request</h2>
        <p>Hi {username}, we received a request to reset your StockSim password.</p>
        <p>Click the button below to choose a new password:</p>
        <a href="{reset_url}" class="btn">RESET PASSWORD →</a>
        <p>Or paste this link:<br><small style="color:#4a5568">{reset_url}</small></p>
        <p>This link expires in <strong>1 hour</strong>. If you didn't request this, ignore this email — your account is safe.</p>
    """
    send_email(to_email, "Reset your StockSim password", _base_template(content))


def send_trade_confirmation_email(to_email: str, username: str, action: str, ticker: str, qty: int, price: float):
    total = qty * price
    color = "#00d4c8" if action == "BUY" else "#f05050"
    content = f"""
        <h2>Trade Executed ✓</h2>
        <p>Hi {username}, your order has been filled:</p>
        <div style="background:#161a1f;border:1px solid #1c2128;border-radius:6px;padding:16px;margin:16px 0">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span>Action</span><strong style="color:{color}">{action}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span>Stock</span><strong>{ticker}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span>Quantity</span><strong>{qty} shares</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span>Price</span><strong>S${price:,.2f}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;border-top:1px solid #1c2128;padding-top:8px;margin-top:8px">
            <span>Total</span><strong style="color:{color}">S${total:,.2f}</strong>
          </div>
        </div>
        <p>Remember: this is SimBucks — no real money is involved. Keep learning!</p>
    """
    send_email(to_email, f"Trade Confirmed: {action} {qty}× {ticker}", _base_template(content))
