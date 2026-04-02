"""Send invite emails via Gmail SMTP."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_invite_email(
    to_email: str,
    invite_url: str,
    invited_by_username: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
) -> None:
    subject = "Undangan akses ICS Monitoring Hub"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px">
      <img src="https://msmonitoring.bagusganteng.app/brand/ics-logo.png"
           alt="ICS" style="height:40px;margin-bottom:24px"/>
      <h2 style="color:#0f172a;margin-bottom:8px">Kamu diundang ke ICS Monitoring Hub</h2>
      <p style="color:#475569;line-height:1.6">
        <strong>{invited_by_username}</strong> mengundangmu untuk mengakses
        <strong>ICS Monitoring Hub</strong> — platform monitoring infrastruktur ICS.
      </p>
      <p style="color:#475569;line-height:1.6">
        Klik tombol di bawah untuk aktivasi akun menggunakan akun Google
        <strong>@icscompute.com</strong>-mu. Link berlaku <strong>72 jam</strong>.
      </p>
      <a href="{invite_url}"
         style="display:inline-block;margin:20px 0;padding:12px 28px;background:#0f172a;
                color:#fff;text-decoration:none;border-radius:8px;font-weight:600">
        Aktivasi Akun
      </a>
      <p style="color:#94a3b8;font-size:12px;margin-top:24px">
        Jika kamu tidak merasa diundang, abaikan email ini.<br/>
        Link: <a href="{invite_url}" style="color:#94a3b8">{invite_url}</a>
      </p>
    </div>
    """

    plain = (
        f"Kamu diundang oleh {invited_by_username} ke ICS Monitoring Hub.\n\n"
        f"Aktivasi akun: {invite_url}\n\n"
        "Link berlaku 72 jam."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())
