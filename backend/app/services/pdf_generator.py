"""Posture screening report (PDF, ReportLab).

All user- and model-provided text is escaped before it reaches ReportLab's paragraph markup.
"""

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.posture.metrics import METRIC_LABELS

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")

PRIMARY = colors.HexColor("#0D6EFD")
TEAL = colors.HexColor("#0D9488")
TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#E5E7EB")
DANGER = colors.HexColor("#B91C1C")
DANGER_BG = colors.HexColor("#FEF2F2")
SEVERITY_COLORS = {"mild": "#B45309", "moderate": "#C2410C", "pronounced": "#B91C1C"}

VIEW_LABELS = {"front": "Front", "back": "Back", "left_side": "Side (left)", "right_side": "Side (right)"}
SEX_LABELS = {"female": "Female", "male": "Male", "other": "Other", "prefer_not_to_say": "Prefer not to say"}
DISCLAIMER = (
    "PostureAI provides AI-assisted posture screening and educational information. It is not a medical diagnosis "
    "and does not replace evaluation by a qualified healthcare professional. Measurements describe body-landmark "
    "positions in a single photo and depend on how the photo was taken. The alignment score is a PostureAI metric, "
    "not a measure of health."
)

_base = {"fontName": "DejaVu", "textColor": TEXT}
STYLES = {
    "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=20, leading=24, textColor=PRIMARY),
    "subtitle": ParagraphStyle("subtitle", fontName="DejaVu-Bold", fontSize=10, leading=13, textColor=TEAL),
    "h2": ParagraphStyle(
        "h2", fontName="DejaVu-Bold", fontSize=12.5, leading=16, textColor=PRIMARY, spaceBefore=12, spaceAfter=5
    ),
    "h3": ParagraphStyle(
        "h3", fontName="DejaVu-Bold", fontSize=10, leading=13, textColor=TEXT, spaceBefore=6, spaceAfter=2
    ),
    "body": ParagraphStyle("body", fontSize=9.2, leading=13, spaceAfter=4, **_base),
    "small": ParagraphStyle("small", fontSize=8, leading=11, textColor=MUTED, fontName="DejaVu"),
    "cell": ParagraphStyle("cell", fontSize=8.6, leading=11.5, **_base),
    "cell_bold": ParagraphStyle("cell_bold", fontSize=8.6, leading=11.5, fontName="DejaVu-Bold", textColor=TEXT),
    "score": ParagraphStyle(
        "score", fontName="DejaVu-Bold", fontSize=26, leading=30, textColor=PRIMARY, alignment=TA_CENTER
    ),
    "center_small": ParagraphStyle(
        "center_small", fontSize=7.5, leading=10, textColor=MUTED, fontName="DejaVu", alignment=TA_CENTER
    ),
}


@dataclass
class ReportData:
    analysis_id: str
    created_at: datetime
    timezone: str
    snapshot: dict
    view: str
    alignment_score: float | None
    measurements: list[dict]
    unavailable: list[dict]
    findings: list[dict]
    explanation: dict
    explanation_source: str
    explanation_model: str | None
    plan: dict
    annotated_jpeg: bytes | None


def _p(text: str | None, style: str = "body") -> Paragraph:
    return Paragraph(escape(text or "—"), STYLES[style])


def _bullets(items: list[str], style: str = "body") -> list[Paragraph]:
    return [Paragraph(f"•&nbsp;&nbsp;{escape(item)}", STYLES[style]) for item in items]


def _table(rows: list[list], widths: list[float], header: bool = True, zebra: bool = True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT)]
    if zebra:
        style += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")])]
    table.setStyle(TableStyle(style))
    return table


def _page_decorations(analysis_id: str):
    def draw(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, height - 6 * mm, width, 6 * mm, stroke=0, fill=1)
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "PostureAI posture screening — educational, not a medical diagnosis")
        canvas.drawRightString(width - 18 * mm, 10 * mm, f"Report {analysis_id[:8]} · Page {doc.page}")
        canvas.restoreState()

    return draw


def _fmt_number(value, suffix: str = "") -> str:
    return "—" if value is None else f"{float(value):g}{suffix}"


def build_report(data: ReportData) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="PostureAI Posture Screening Report",
        author="PostureAI",
    )
    content_width = doc.width
    local_time = data.created_at.astimezone(ZoneInfo(data.timezone))
    s = data.snapshot
    story: list = []

    # Header
    story += [
        Paragraph("POSTUREAI", STYLES["subtitle"]),
        Paragraph("Posture Screening Report", STYLES["title"]),
        Spacer(1, 3),
        _p(
            f"Analysis date: {local_time:%d %B %Y, %I:%M %p} ({data.timezone}) · Report ID: {data.analysis_id}", "small"
        ),
        Spacer(1, 8),
    ]

    # Patient information
    story.append(Paragraph("Patient information", STYLES["h2"]))
    info = [
        [
            _p("Name", "cell_bold"),
            _p(s.get("full_name"), "cell"),
            _p("Age", "cell_bold"),
            _p(_fmt_number(s.get("age"), " years"), "cell"),
        ],
        [
            _p("Sex", "cell_bold"),
            _p(SEX_LABELS.get(s.get("sex") or "", "—"), "cell"),
            _p("Height / weight", "cell_bold"),
            _p(f"{_fmt_number(s.get('height_cm'), ' cm')} / {_fmt_number(s.get('weight_kg'), ' kg')}", "cell"),
        ],
        [_p("Reported symptoms", "cell_bold"), _p(s.get("symptoms") or "None reported", "cell"), "", ""],
    ]
    info_table = _table(info, [32 * mm, 58 * mm, 32 * mm, content_width - 122 * mm], header=False, zebra=False)
    info_table.setStyle(TableStyle([("SPAN", (1, 2), (3, 2)), ("BACKGROUND", (0, 0), (-1, -1), LIGHT)]))
    story.append(info_table)

    # Summary + score + image
    story.append(Paragraph("Posture summary", STYLES["h2"]))
    score_text = "—" if data.alignment_score is None else f"{data.alignment_score:.0f}<font size=12> / 100</font>"
    score_cell = [
        Paragraph(score_text, STYLES["score"]),
        Paragraph("PostureAI alignment score", STYLES["center_small"]),
        Paragraph(
            "A product-specific summary of the measured angles. Not a medical or health score.", STYLES["center_small"]
        ),
    ]
    summary_cell = [
        _p(f"Camera view: {VIEW_LABELS.get(data.view, data.view)}", "cell_bold"),
        Spacer(1, 3),
        _p(data.explanation.get("summary"), "body"),
    ]
    story.append(_table([[score_cell, summary_cell]], [45 * mm, content_width - 45 * mm], header=False, zebra=False))

    if data.annotated_jpeg:
        image = Image(BytesIO(data.annotated_jpeg))
        max_w, max_h = content_width * 0.55, 105 * mm
        ratio = min(max_w / image.imageWidth, max_h / image.imageHeight)
        image.drawWidth, image.drawHeight = image.imageWidth * ratio, image.imageHeight * ratio
        story += [
            Paragraph("Annotated posture image", STYLES["h2"]),
            KeepTogether(
                [
                    image,
                    Paragraph(
                        "Detected body landmarks with reference lines and measured angles.", STYLES["center_small"]
                    ),
                ]
            ),
        ]

    # Observations
    story.append(Paragraph("Detected observations", STYLES["h2"]))
    if data.findings:
        rows = [[_p("Observation", "cell_bold"), _p("Severity", "cell_bold"), _p("Details", "cell_bold")]]
        for f in data.findings:
            color = SEVERITY_COLORS.get(f["severity"], "#1F2937")
            rows.append(
                [
                    _p(f["title"], "cell"),
                    Paragraph(
                        f'<font color="{color}"><b>{escape(f["severity"].capitalize())}</b></font>', STYLES["cell"]
                    ),
                    _p(f["observation"], "cell"),
                ]
            )
        story.append(_table(rows, [48 * mm, 30 * mm, content_width - 78 * mm]))
    else:
        story.append(_p("No alignment pattern exceeded PostureAI's screening thresholds in this photo."))

    # Measurements
    story.append(Paragraph("Measurements", STYLES["h2"]))
    rows = [[_p("Metric", "cell_bold"), _p("Result", "cell_bold"), _p("Confidence", "cell_bold")]]
    for m in data.measurements:
        unit = "°" if m["unit"] == "degrees" else f" {m['unit']}"
        rows.append(
            [
                _p(METRIC_LABELS.get(m["metric"], m["metric"]), "cell"),
                _p(f"{m['value']:.1f}{unit}", "cell"),
                _p(f"{m['confidence'] * 100:.0f}%", "cell"),
            ]
        )
    story.append(_table(rows, [content_width - 60 * mm, 30 * mm, 30 * mm]))
    if data.unavailable:
        story.append(Spacer(1, 4))
        story.append(
            _p(
                "Not measured from this photo: "
                + "; ".join(
                    f"{METRIC_LABELS.get(u['metric'], u['metric'])} ({u['reason'].rstrip('.').lower()})"
                    for u in data.unavailable
                )
                + ".",
                "small",
            )
        )
    story.append(_p("Thresholds are PostureAI screening heuristics and have not been clinically validated.", "small"))

    # AI explanation
    source_label = (
        f"Generated by a local AI model ({data.explanation_model}) from the measurements above, "
        "then automatically checked."
        if data.explanation_source == "ollama"
        else "Standard explanation (the AI model was not available)."
    )
    story += [
        Paragraph("Educational explanation", STYLES["h2"]),
        _p(source_label, "small"),
        Spacer(1, 3),
        _p(data.explanation.get("what_this_may_mean")),
    ]
    titles = {f["code"]: f["title"] for f in data.findings}
    for item in data.explanation.get("finding_explanations", []):
        story += [Paragraph(escape(titles.get(item["code"], item["code"])), STYLES["h3"]), _p(item["explanation"])]

    # Corrective plan
    plan = data.plan
    story.append(Paragraph("Corrective exercise plan", STYLES["h2"]))
    rows = [[_p("Exercise", "cell_bold"), _p("How to do it", "cell_bold"), _p("Amount", "cell_bold")]]
    for e in plan.get("exercises", []):
        rows.append(
            [
                [_p(e["name"], "cell_bold"), _p(e["category"].capitalize(), "small")],
                [
                    _p(e["instructions"], "cell"),
                    Paragraph(f"<i>Safety: {escape(e['safety_note'])}</i>", STYLES["small"]),
                ],
                [_p(e["duration"], "cell"), _p(e["frequency"], "small")],
            ]
        )
    story.append(_table(rows, [38 * mm, content_width - 83 * mm, 45 * mm]))

    names = {e["id"]: e["name"] for e in plan.get("exercises", [])}
    story.append(Paragraph("4-week programme", STYLES["h3"]))
    rows = [[_p("Week", "cell_bold"), _p("Focus", "cell_bold"), _p("Exercises and habits", "cell_bold")]]
    for week in plan.get("weekly_plan", []):
        exercises = ", ".join(names.get(i, i) for i in week["exercise_ids"])
        rows.append(
            [
                _p(f"Week {week['week']}", "cell_bold"),
                [_p(week["title"], "cell_bold"), _p(week["focus"], "small")],
                [_p(exercises, "cell"), _p(" ".join(week["habits"]), "small")],
            ]
        )
    story.append(_table(rows, [18 * mm, 55 * mm, content_width - 73 * mm]))

    # Lifestyle
    story.append(Paragraph("Lifestyle recommendations", STYLES["h2"]))
    listed = set(plan.get("workstation", []) + plan.get("sleep", []) + plan.get("movement_breaks", []))
    personal = [tip for tip in data.explanation.get("lifestyle_tips", []) if tip not in listed]
    for heading, items in (
        ("Workstation", plan.get("workstation", [])),
        ("Sleep", plan.get("sleep", [])),
        ("Movement breaks", plan.get("movement_breaks", [])),
        ("Personal tips", personal),
    ):
        if items:
            story += [Paragraph(heading, STYLES["h3"]), *_bullets(items)]
    if data.explanation.get("follow_up_guidance"):
        story += [Paragraph("Follow-up", STYLES["h3"]), _p(data.explanation["follow_up_guidance"])]

    # Professional care and warning signs
    care = plan.get("professional_care", {})
    story += [Paragraph("When to seek professional care", STYLES["h2"]), *_bullets(care.get("when", []))]
    warning = [
        Paragraph(
            "<b>Seek medical attention promptly if you notice:</b>",
            ParagraphStyle("w", parent=STYLES["body"], textColor=DANGER),
        ),
        *_bullets(plan.get("warning_signs", []), "cell"),
        _p(plan.get("warning_advice"), "cell"),
    ]
    box = Table([[warning]], colWidths=[content_width])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DANGER_BG),
                ("BOX", (0, 0), (-1, -1), 0.8, DANGER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story += [Spacer(1, 4), KeepTogether(box)]

    story += [
        Paragraph("Recommended healthcare providers", STYLES["h2"]),
        *_bullets(care.get("who", [])),
        _p(
            "Use Find Care in PostureAI to see providers near you. Listings come from OpenStreetMap and are shown "
            "with their source; appointments can be booked with providers who manage their availability in PostureAI.",
            "small",
        ),
    ]

    story += [Spacer(1, 10), Paragraph("Medical disclaimer", STYLES["h3"]), _p(DISCLAIMER, "small")]

    decorate = _page_decorations(data.analysis_id)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
