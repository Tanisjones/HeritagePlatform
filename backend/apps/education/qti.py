"""
IMS QTI 2.1 export for assessment questions (task F2.c.6).

Builds a QTI 2.1 content package (ZIP) from a set of questions: one
``assessmentItem`` XML per question plus an ``imsmanifest.xml`` that references
them. Questions may be :class:`AssessmentQuestion` model instances OR plain
dicts (duck-typed), so the builder needs no database and is unit-testable
directly.

Mapping of our question types to QTI interactions:
- single_choice / true_false -> single-cardinality ``choiceInteraction``
- multiple_choice            -> multiple-cardinality ``choiceInteraction``
- short_answer               -> ``extendedTextInteraction`` (text entry)
"""

import io
import tempfile
import zipfile
from xml.etree import ElementTree as ET

from .scorm import _pretty_xml, _slugify_filename


QTI_NS = "http://www.imsglobal.org/xsd/imsqti_v2p1"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
_IMSCP_NS = "http://www.imsproject.org/xsd/imscp_rootv1p1p2"


def _q_get(question, key, default=None):
    """Read ``key`` from a question that may be a dict or a model instance."""
    if isinstance(question, dict):
        return question.get(key, default)
    return getattr(question, key, default)


def _normalise_choices(raw) -> list:
    """Coerce a stored ``choices`` value into a list of {id,text,correct} dicts.

    Accepts the JSONField list shape ``[{"id","text","correct"}, ...]`` and is
    tolerant of missing ids (generates CHOICE_n) and of "correct" being absent.
    """
    choices = []
    for idx, ch in enumerate(raw or [], start=1):
        if isinstance(ch, dict):
            cid = str(ch.get("id") or f"CHOICE_{idx}")
            text = str(ch.get("text") or ch.get("label") or "")
            correct = bool(ch.get("correct"))
        else:
            cid = f"CHOICE_{idx}"
            text = str(ch)
            correct = False
        choices.append({"id": cid, "text": text, "correct": correct})
    return choices


def build_assessment_item_xml(question, identifier: str) -> str:
    """Emit a single QTI 2.1 ``assessmentItem`` XML for one question."""
    ET.register_namespace("", QTI_NS)
    ET.register_namespace("xsi", _XSI_NS)

    def _q(tag):
        return f"{{{QTI_NS}}}{tag}"

    qtype = _q_get(question, "question_type", "single_choice")
    prompt = str(_q_get(question, "prompt", "") or "")
    feedback = str(_q_get(question, "feedback", "") or "")
    title = (prompt[:60] or "Question").strip()

    is_choice = qtype in ("single_choice", "multiple_choice", "true_false")
    multiple = qtype == "multiple_choice"

    item = ET.Element(
        _q("assessmentItem"),
        {
            f"{{{_XSI_NS}}}schemaLocation": (
                f"{QTI_NS} http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
            ),
            "identifier": identifier,
            "title": title,
            "adaptive": "false",
            "timeDependent": "false",
        },
    )

    if is_choice:
        choices = _normalise_choices(_q_get(question, "choices"))
        # true_false with no explicit choices gets a canonical yes/no pair.
        if qtype == "true_false" and not choices:
            correct_resp = str(_q_get(question, "correct_response", "true") or "true").lower()
            choices = [
                {"id": "true", "text": "True", "correct": correct_resp in ("true", "1", "yes")},
                {"id": "false", "text": "False", "correct": correct_resp in ("false", "0", "no")},
            ]

        correct_ids = [c["id"] for c in choices if c["correct"]]

        # responseDeclaration
        rd = ET.SubElement(
            item,
            _q("responseDeclaration"),
            {
                "identifier": "RESPONSE",
                "cardinality": "multiple" if multiple else "single",
                "baseType": "identifier",
            },
        )
        if correct_ids:
            correct = ET.SubElement(rd, _q("correctResponse"))
            for cid in correct_ids:
                ET.SubElement(correct, _q("value")).text = cid

        # itemBody + choiceInteraction
        body = ET.SubElement(item, _q("itemBody"))
        interaction = ET.SubElement(
            body,
            _q("choiceInteraction"),
            {
                "responseIdentifier": "RESPONSE",
                "shuffle": "false",
                "maxChoices": "0" if multiple else "1",
            },
        )
        ET.SubElement(interaction, _q("prompt")).text = prompt
        for c in choices:
            simple = ET.SubElement(
                interaction, _q("simpleChoice"), {"identifier": c["id"]}
            )
            simple.text = c["text"]

        # responseProcessing: standard match_correct template.
        ET.SubElement(
            item,
            _q("responseProcessing"),
            {
                "template": (
                    "http://www.imsglobal.org/question/qti_v2p1/"
                    "rptemplates/match_correct"
                )
            },
        )
    else:
        # short_answer -> extendedTextInteraction (text entry).
        correct_resp = str(_q_get(question, "correct_response", "") or "")
        rd = ET.SubElement(
            item,
            _q("responseDeclaration"),
            {"identifier": "RESPONSE", "cardinality": "single", "baseType": "string"},
        )
        if correct_resp:
            correct = ET.SubElement(rd, _q("correctResponse"))
            ET.SubElement(correct, _q("value")).text = correct_resp

        body = ET.SubElement(item, _q("itemBody"))
        interaction = ET.SubElement(
            body,
            _q("extendedTextInteraction"),
            {"responseIdentifier": "RESPONSE", "expectedLength": "200"},
        )
        ET.SubElement(interaction, _q("prompt")).text = prompt

        # Text answers can't be auto-scored reliably; leave scoring to the LMS.
        ET.SubElement(
            item,
            _q("responseProcessing"),
            {
                "template": (
                    "http://www.imsglobal.org/question/qti_v2p1/"
                    "rptemplates/match_correct"
                )
            },
        )

    if feedback:
        # A simple always-shown modal feedback block.
        fb = ET.SubElement(
            item,
            _q("modalFeedback"),
            {"outcomeIdentifier": "FEEDBACK", "identifier": "FB", "showHide": "show"},
        )
        fb.text = feedback

    return _pretty_xml(item)


def _build_qti_manifest_xml(package_id: str, title: str, item_files: list) -> str:
    """imsmanifest.xml for a QTI 2.1 package with one resource per item file.

    ``item_files`` is a list of ``(resource_id, href)`` tuples.
    """
    ET.register_namespace("", _IMSCP_NS)
    ET.register_namespace("xsi", _XSI_NS)

    manifest = ET.Element(
        f"{{{_IMSCP_NS}}}manifest",
        {
            "identifier": package_id,
            f"{{{_XSI_NS}}}schemaLocation": (
                f"{_IMSCP_NS} imscp_rootv1p1p2.xsd"
            ),
        },
    )

    metadata = ET.SubElement(manifest, f"{{{_IMSCP_NS}}}metadata")
    ET.SubElement(metadata, f"{{{_IMSCP_NS}}}schema").text = "QTIv2.1 Package"
    ET.SubElement(metadata, f"{{{_IMSCP_NS}}}schemaversion").text = "1.0.0"

    organizations = ET.SubElement(manifest, f"{{{_IMSCP_NS}}}organizations")
    # QTI item packages carry no organization tree; the element is present but empty.
    organizations.text = ""

    resources = ET.SubElement(manifest, f"{{{_IMSCP_NS}}}resources")
    for res_id, href in item_files:
        resource = ET.SubElement(
            resources,
            f"{{{_IMSCP_NS}}}resource",
            {
                "identifier": res_id,
                "type": "imsqti_item_xmlv2p1",
                "href": href,
            },
        )
        ET.SubElement(resource, f"{{{_IMSCP_NS}}}file", {"href": href})

    return _pretty_xml(manifest)


def build_qti_21_zip(*, title: str, questions, identifier: str):
    """Build an IMS QTI 2.1 content package (ZIP).

    ``questions`` is an iterable of :class:`AssessmentQuestion` instances OR
    dicts. Produces one ``items/item_{n}.xml`` per question plus an
    ``imsmanifest.xml``. Returns (file_like, filename).
    """
    safe_title = title or "Assessment"
    base_name = _slugify_filename(safe_title, fallback="assessment")
    filename = f"{base_name}-qti21.zip"
    package_id = f"QTI-{_slugify_filename(str(identifier), fallback=base_name)}"

    spooled = tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024, mode="w+b")

    with zipfile.ZipFile(spooled, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        item_files = []
        for idx, question in enumerate(questions, start=1):
            res_id = f"ITEM-{idx}"
            href = f"items/item_{idx}.xml"
            item_xml = build_assessment_item_xml(question, identifier=res_id)
            zf.writestr(href, item_xml)
            item_files.append((res_id, href))

        manifest = _build_qti_manifest_xml(package_id, safe_title, item_files)
        zf.writestr("imsmanifest.xml", manifest)

    spooled.seek(0)
    return spooled, filename
