"""Lesson-plan PDF handout generation (P.6).

Renders a LessonPlan to a printable classroom handout using reportlab (pure-Python,
no system libs). Kept dependency-light: a single-column flowable document with the
header, objectives, curriculum standards, the ordered activities, and any rubrics.

Activity instructions are stored as sanitized HTML; for the PDF we strip tags to
plain text (reportlab Paragraph accepts a small HTML subset, but arbitrary authored
markup is safer flattened).
"""

from __future__ import annotations

import io
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# Brand terracotta (matches the SPA primary-600).
_PRIMARY = colors.HexColor("#b55a3a")


def _text(value) -> str:
    """Flatten HTML-ish content to plain text and collapse whitespace.

    Coerces non-strings to str defensively — `objectives` is a free-form JSONField,
    so a numeric/None entry must not crash the PDF build."""
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        value = str(value)
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", value)).strip()


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("lp_title", parent=base["Title"], textColor=_PRIMARY, fontSize=20),
        "h2": ParagraphStyle("lp_h2", parent=base["Heading2"], textColor=_PRIMARY, spaceBefore=10),
        "h3": ParagraphStyle("lp_h3", parent=base["Heading3"], spaceBefore=6),
        "body": ParagraphStyle("lp_body", parent=base["BodyText"], alignment=TA_LEFT, fontSize=10, leading=14),
        "meta": ParagraphStyle("lp_meta", parent=base["BodyText"], textColor=colors.grey, fontSize=9),
    }
    return styles


def build_lesson_plan_pdf(plan) -> tuple[io.BytesIO, str]:
    """Render ``plan`` (a LessonPlan with prefetched activities/rubrics/standards)
    to a PDF. Returns (BytesIO positioned at 0, filename)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=plan.title,
    )
    s = _styles()
    story = []

    # Header
    story.append(Paragraph(_text(plan.title) or "Plan de lección", s["title"]))
    meta_bits = [b for b in (plan.subject, plan.grade_level, plan.audience) if b]
    if meta_bits:
        story.append(Paragraph(" · ".join(_text(b) for b in meta_bits), s["meta"]))
    total = plan.estimated_total_minutes or sum(
        (a.duration_minutes or 0) for a in plan.activities.all()
    )
    if total:
        story.append(Paragraph(f"⏱ {total} min", s["meta"]))
    if plan.summary:
        story.append(Spacer(1, 6))
        story.append(Paragraph(_text(plan.summary), s["body"]))

    # Objectives
    objectives = list(plan.objectives or [])
    if objectives:
        story.append(Paragraph("Objetivos de aprendizaje", s["h2"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(_text(o), s["body"])) for o in objectives],
            bulletType="bullet",
        ))

    # Curriculum standards
    standards = list(plan.standards.all())
    if standards:
        story.append(Paragraph("Estándares curriculares", s["h2"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(f"<b>{_text(st.code)}</b> — {_text(st.description)}", s["body"]))
             for st in standards],
            bulletType="bullet",
        ))
    elif plan.curriculum_alignment:
        story.append(Paragraph("Alineación curricular", s["h2"]))
        story.append(Paragraph(_text(plan.curriculum_alignment), s["body"]))

    # Activities
    activities = sorted(plan.activities.all(), key=lambda a: a.order)
    if activities:
        story.append(Paragraph("Secuencia de actividades", s["h2"]))
        for i, a in enumerate(activities, start=1):
            dur = f" · {a.duration_minutes} min" if a.duration_minutes else ""
            story.append(Paragraph(f"{i}. {_text(a.title)} <font color='#999'>({_text(a.activity_type)}{dur})</font>", s["h3"]))
            if a.instructions:
                story.append(Paragraph(_text(a.instructions), s["body"]))
            if a.materials:
                story.append(Paragraph(f"<i>Materiales:</i> {_text(a.materials)}", s["meta"]))

    # Rubrics
    rubrics = list(plan.rubrics.all())
    for rubric in rubrics:
        story.append(Paragraph(f"Rúbrica: {_text(rubric.title)}", s["h2"]))
        if rubric.description:
            story.append(Paragraph(_text(rubric.description), s["body"]))
        criteria = sorted(rubric.criteria.all(), key=lambda c: c.order)
        if criteria:
            data = [["Criterio", "Puntos", "Niveles"]]
            for c in criteria:
                levels = "; ".join(
                    f"{_text(str(lv.get('level', '')))} ({lv.get('points', '')})"
                    for lv in (c.levels or []) if isinstance(lv, dict)
                )
                data.append([_text(c.label), str(c.max_points), levels or "—"])
            table = Table(data, colWidths=[55 * mm, 20 * mm, 85 * mm])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf6f4")]),
            ]))
            story.append(table)

    doc.build(story)
    buf.seek(0)
    # Reuse the shared filename slug helper (don't add a third divergent copy).
    from apps.routes.exports import slugify_filename

    filename = slugify_filename(_text(plan.title), fallback="lesson-plan") + "-lesson-plan.pdf"
    return buf, filename
