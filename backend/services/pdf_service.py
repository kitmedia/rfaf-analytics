"""PDF generation with ReportLab + mplsoccer charts."""

import base64
import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import structlog

logger = structlog.get_logger()

WIDTH, HEIGHT = A4
MARGIN = 2 * cm


def _get_styles():
    """Build PDF paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "RFAFTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=colors.HexColor("#1a237e"),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "RFAFHeading2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1a237e"),
        spaceBefore=16,
        spaceAfter=8,
        borderWidth=0,
        borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        "RFAFHeading3",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=colors.HexColor("#303f9f"),
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "RFAFBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "RFAFBullet",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=3,
    ))
    return styles


def _md_to_flowables(markdown_text: str, styles) -> list:
    """Convert markdown to ReportLab flowables."""
    flowables = []
    lines = markdown_text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flowables.append(Spacer(1, 4 * mm))
            continue

        # Headers
        if stripped.startswith("### "):
            text = stripped[4:]
            flowables.append(Paragraph(text, styles["RFAFHeading3"]))
        elif stripped.startswith("## "):
            text = stripped[3:]
            flowables.append(Paragraph(text, styles["RFAFHeading2"]))
        elif stripped.startswith("# "):
            text = stripped[2:]
            flowables.append(Paragraph(text, styles["RFAFTitle"]))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            text = _md_inline(text)
            flowables.append(Paragraph(f"• {text}", styles["RFAFBullet"]))
        elif re.match(r"^\d+\.\s", stripped):
            text = re.sub(r"^\d+\.\s", "", stripped)
            text = _md_inline(text)
            flowables.append(Paragraph(f"• {text}", styles["RFAFBullet"]))
        elif stripped.startswith("|") and "|" in stripped[1:]:
            # Skip markdown tables (simplified — just render as text)
            text = stripped.replace("|", " | ").strip()
            if not all(c in "-| " for c in stripped):
                flowables.append(Paragraph(text, styles["RFAFBody"]))
        else:
            text = _md_inline(stripped)
            flowables.append(Paragraph(text, styles["RFAFBody"]))

    return flowables


def _md_inline(text: str) -> str:
    """Convert markdown inline formatting to ReportLab XML."""
    # Bold: **text** → <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic: *text* → <i>text</i>
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # Inline code: `text` → <font name="Courier">text</font>
    text = re.sub(r"`(.+?)`", r'<font name="Courier" size="9">\1</font>', text)
    return text


def _chart_to_image(base64_png: str, width_cm: float = 14) -> Image:
    """Convert base64 PNG to ReportLab Image flowable."""
    img_data = base64.b64decode(base64_png)
    buf = io.BytesIO(img_data)
    img = Image(buf, width=width_cm * cm, height=width_cm * cm * 0.65)
    return img


def _footer(canvas, doc):
    """Draw footer on each page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.gray)
    canvas.drawString(
        MARGIN, 1.2 * cm,
        f"RFAF Analytics Platform · Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    canvas.drawRightString(
        WIDTH - MARGIN, 1.2 * cm,
        f"Página {doc.page}"
    )
    canvas.restoreState()


def generate_pdf(
    contenido_md: str,
    charts_json: dict | None,
    equipo_local: str,
    equipo_visitante: str,
    competicion: str | None = None,
    sponsor_logo_url: str | None = None,
) -> bytes:
    """Generate complete PDF report.

    Args:
        contenido_md: Markdown analysis from Claude.
        charts_json: Dict of chart_name → base64 PNG strings.
        equipo_local: Home team name.
        equipo_visitante: Away team name.
        competicion: Competition name.

    Returns:
        PDF file as bytes.
    """
    buf = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=2 * cm,
    )

    story = []

    # --- Cover page ---
    # Sponsor logo (Story 6.2)
    if sponsor_logo_url:
        try:
            import urllib.request
            logo_data = urllib.request.urlopen(sponsor_logo_url).read()
            logo_buf = io.BytesIO(logo_data)
            story.append(Image(logo_buf, width=5 * cm, height=2 * cm, kind="proportional"))
            story.append(Spacer(1, 1 * cm))
        except Exception as exc:
            logger.warning("pdf_sponsor_logo_error", error=str(exc))
            story.append(Spacer(1, 4 * cm))
    else:
        story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("RFAF Analytics", styles["RFAFTitle"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f"Informe Táctico",
        ParagraphStyle("subtitle", parent=styles["Heading2"], fontSize=18, textColor=colors.HexColor("#455a64")),
    ))
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph(
        f"<b>{equipo_local}</b>  vs  <b>{equipo_visitante}</b>",
        ParagraphStyle("teams", parent=styles["Normal"], fontSize=16, alignment=1),
    ))
    if competicion:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            competicion,
            ParagraphStyle("comp", parent=styles["Normal"], fontSize=12, alignment=1, textColor=colors.gray),
        ))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        datetime.now().strftime("%d de %B de %Y"),
        ParagraphStyle("date", parent=styles["Normal"], fontSize=11, alignment=1, textColor=colors.gray),
    ))
    story.append(PageBreak())

    # --- Charts section (before analysis) ---
    charts = charts_json or {}
    if charts:
        story.append(Paragraph("Visualizaciones", styles["RFAFHeading2"]))
        story.append(Spacer(1, 4 * mm))

        chart_titles = {
            "shot_map_local": f"Mapa de tiros - {equipo_local}",
            "shot_map_visitante": f"Mapa de tiros - {equipo_visitante}",
            "pass_network_local": f"Red de pases - {equipo_local}",
            "pass_network_visitante": f"Red de pases - {equipo_visitante}",
            "xg_timeline": "Evolución xG acumulado",
        }

        for key, title in chart_titles.items():
            if key in charts:
                try:
                    img = _chart_to_image(charts[key])
                    story.append(Spacer(1, 4 * mm))
                    story.append(img)
                    story.append(Spacer(1, 6 * mm))
                except Exception as e:
                    logger.error("pdf_chart_error", chart=key, error=str(e))

        story.append(PageBreak())

    # --- Analysis content ---
    flowables = _md_to_flowables(contenido_md, styles)
    story.extend(flowables)

    # Build PDF
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    pdf_bytes = buf.getvalue()

    logger.info(
        "pdf_generated",
        size_kb=round(len(pdf_bytes) / 1024, 1),
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
    )

    return pdf_bytes
