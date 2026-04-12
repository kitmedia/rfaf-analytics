"""Email service with Resend API."""

import os

import resend
import structlog

logger = structlog.get_logger()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = "RFAF Analytics <noreply@rfaf-analytics.es>"


def _render_analysis_started_html(equipo_local: str, equipo_visitante: str, analysis_id: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1a237e;">⚽ Análisis en curso</h2>
        <p>Hemos empezado a analizar el partido:</p>
        <p style="font-size: 18px; font-weight: bold; color: #333;">
            {equipo_local} vs {equipo_visitante}
        </p>
        <p>El informe táctico estará listo en aproximadamente <b>10-15 minutos</b>.</p>
        <p>Te enviaremos otro email con el informe completo cuando esté listo.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            ID de análisis: {analysis_id}<br>
            RFAF Analytics Platform
        </p>
    </div>
    """


def _render_report_email_html(
    equipo_local: str,
    equipo_visitante: str,
    xg_local: float | None,
    xg_visitante: float | None,
    pdf_url: str | None,
) -> str:
    xg_section = ""
    if xg_local is not None and xg_visitante is not None:
        xg_section = f"""
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <p style="margin: 0; font-size: 14px; color: #666;">Expected Goals (xG)</p>
            <p style="margin: 5px 0; font-size: 20px; font-weight: bold;">
                {equipo_local}: {xg_local:.2f} — {equipo_visitante}: {xg_visitante:.2f}
            </p>
        </div>
        """

    pdf_button = ""
    if pdf_url:
        pdf_button = f"""
        <a href="{pdf_url}" style="display: inline-block; background: #1a237e; color: white;
           padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;
           margin: 15px 0;">
            📄 Descargar informe PDF
        </a>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1a237e;">✅ Informe táctico listo</h2>
        <p style="font-size: 18px; font-weight: bold; color: #333;">
            {equipo_local} vs {equipo_visitante}
        </p>
        {xg_section}
        <p>El informe táctico completo con 12 secciones de análisis ya está disponible
           en tu panel de RFAF Analytics.</p>
        {pdf_button}
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">RFAF Analytics Platform</p>
    </div>
    """


def send_analysis_started_email(
    to_email: str,
    equipo_local: str,
    equipo_visitante: str,
    analysis_id: str,
) -> bool:
    """Send notification that analysis has started."""
    if not RESEND_API_KEY:
        logger.warn("resend_api_key_missing", msg="Email no enviado")
        return False

    resend.api_key = RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"⚽ Analizando: {equipo_local} vs {equipo_visitante}",
            "html": _render_analysis_started_html(equipo_local, equipo_visitante, analysis_id),
        })
        logger.info("email_sent", type="analysis_started", to=to_email)
        return True
    except Exception as e:
        logger.error("email_error", type="analysis_started", to=to_email, error=str(e))
        return False


def send_report_email(
    to_email: str,
    equipo_local: str,
    equipo_visitante: str,
    xg_local: float | None = None,
    xg_visitante: float | None = None,
    pdf_url: str | None = None,
) -> bool:
    """Send completed report notification with PDF link."""
    if not RESEND_API_KEY:
        logger.warn("resend_api_key_missing", msg="Email no enviado")
        return False

    resend.api_key = RESEND_API_KEY

    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"✅ Informe listo: {equipo_local} vs {equipo_visitante}",
            "html": _render_report_email_html(
                equipo_local, equipo_visitante, xg_local, xg_visitante, pdf_url
            ),
        })
        logger.info("email_sent", type="report_ready", to=to_email)
        return True
    except Exception as e:
        logger.error("email_error", type="report_ready", to=to_email, error=str(e))
        return False


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Send password reset link."""
    if not RESEND_API_KEY:
        logger.warn("resend_api_key_missing", msg="Email no enviado")
        return False

    resend.api_key = RESEND_API_KEY

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1a237e;">Recuperar contrasena</h2>
        <p>Hemos recibido una solicitud para restablecer tu contrasena en RFAF Analytics.</p>
        <a href="{reset_url}" style="display: inline-block; background: #1a237e; color: white;
           padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;
           margin: 15px 0;">
            Restablecer contrasena
        </a>
        <p style="color: #666; font-size: 14px;">
            Este enlace expira en 1 hora. Si no solicitaste este cambio, ignora este email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">RFAF Analytics Platform</p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Recuperar contrasena - RFAF Analytics",
            "html": html,
        })
        logger.info("email_sent", type="password_reset", to=to_email)
        return True
    except Exception as e:
        logger.error("email_error", type="password_reset", to=to_email, error=str(e))
        return False
