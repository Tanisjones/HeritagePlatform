import html
import io
import json
import mimetypes
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from xml.etree import ElementTree as ET

from django.utils import timezone


@dataclass(frozen=True)
class ScormAsset:
    href: str
    title: str
    kind: str


def _slugify_filename(value: str, fallback: str = "resource") -> str:
    value = (value or "").strip()
    if not value:
        return fallback
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-.")
    return value or fallback


def _guess_mime(name: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(name)
    return guessed or fallback


def _pretty_xml(elem: ET.Element) -> str:
    # ET.indent exists in Python 3.9+. Keep it best-effort.
    try:
        ET.indent(elem, space="  ")
    except Exception:
        pass
    return ET.tostring(elem, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _build_lom_xml(lom_data: Optional[dict]) -> str:
    """Create a simple IEEE LOM-like XML document from the serialized LOM JSON.

    This is not a full IEEE LOM schema implementation; it aims to preserve all
    available fields in a predictable XML structure.
    """

    lom_data = lom_data or {}

    root = ET.Element("lom")

    def add_text(parent: ET.Element, tag: str, value: Optional[str]):
        if value is None:
            return
        text = str(value).strip()
        if not text:
            return
        node = ET.SubElement(parent, tag)
        node.text = text

    general = ET.SubElement(root, "general")
    add_text(general, "identifier", lom_data.get("id"))
    add_text(general, "title", lom_data.get("title"))
    add_text(general, "language", lom_data.get("language"))
    add_text(general, "description", lom_data.get("description"))

    keywords = lom_data.get("keywords")
    if keywords:
        kw_node = ET.SubElement(general, "keywords")
        # keywords may be list or comma-separated string depending on serializer/model.
        if isinstance(keywords, list):
            for kw in keywords:
                add_text(kw_node, "keyword", kw)
        else:
            for kw in str(keywords).split(","):
                add_text(kw_node, "keyword", kw)

    add_text(general, "coverage", lom_data.get("coverage"))

    lifecycle = lom_data.get("lifecycle")
    if lifecycle:
        lc = ET.SubElement(root, "lifecycle")
        add_text(lc, "version", lifecycle.get("version"))
        add_text(lc, "status", lifecycle.get("status"))
        contributors = lifecycle.get("contributors") or []
        if contributors:
            contribs = ET.SubElement(lc, "contributors")
            for c in contributors:
                cnode = ET.SubElement(contribs, "contributor")
                add_text(cnode, "role", c.get("role"))
                add_text(cnode, "entity", c.get("entity"))
                add_text(cnode, "date", c.get("date"))

    educational = lom_data.get("educational")
    if educational:
        edu_node = ET.SubElement(root, "educational")
        if isinstance(educational, list):
            entries = educational
        else:
            entries = [educational]
        for entry in entries:
            enode = ET.SubElement(edu_node, "entry")
            for key, value in (entry or {}).items():
                add_text(enode, key, value)

    rights = lom_data.get("rights")
    if rights:
        rnode = ET.SubElement(root, "rights")
        for key, value in (rights or {}).items():
            add_text(rnode, key, value)

    classifications = lom_data.get("classifications") or []
    if classifications:
        cnode = ET.SubElement(root, "classifications")
        for cls in classifications:
            one = ET.SubElement(cnode, "classification")
            for key, value in (cls or {}).items():
                add_text(one, key, value)

    relations = lom_data.get("relations") or []
    if relations:
        rnode = ET.SubElement(root, "relations")
        for rel in relations:
            one = ET.SubElement(rnode, "relation")
            for key, value in (rel or {}).items():
                add_text(one, key, value)

    # Preserve any unknown top-level keys
    known = {
        "id",
        "title",
        "language",
        "description",
        "keywords",
        "coverage",
        "lifecycle",
        "educational",
        "rights",
        "classifications",
        "relations",
    }
    extra = {k: v for k, v in lom_data.items() if k not in known}
    if extra:
        extra_node = ET.SubElement(root, "extra")
        for key, value in extra.items():
            if isinstance(value, (dict, list)):
                child = ET.SubElement(extra_node, key)
                child.text = json.dumps(value, ensure_ascii=False)
            else:
                add_text(extra_node, key, value)

    return _pretty_xml(root)


# ---------------------------------------------------------------------------
# Valid IEEE 1484.12.3 LOM XML (task F2.c.1)
# ---------------------------------------------------------------------------
#
# Unlike ``_build_lom_xml`` above (a flat, lossless dump kept for
# backward-compat), this emits schema-shaped IEEE LOM: the proper
# ``http://ltsc.ieee.org/xsd/LOM`` namespace, ``<string language="...">``
# wrappers for LangString-typed elements, and ``<source>/<value>`` pairs for
# vocabulary elements. It is bound to the *loose* schema (``lomLoose.xsd``) so
# our platform extensions and partial data validate.

_LOM_NS = "http://ltsc.ieee.org/xsd/LOM"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
# Namespace for the non-standard platform pedagogical extension fields.
_LOM_EXT_NS = "https://heritageplatform.ddns.net/xsd/lom-ext"

# Map our stored vocabulary tokens (snake_case) to the LOM v1.0 vocabulary
# values, which use spaces (e.g. "narrative text", "educational objective").
_LOM_VOCAB_SPACES = {
    "narrative_text": "narrative text",
    "problem_statement": "problem statement",
    "self_assessment": "self assessment",
    "very_low": "very low",
    "very_high": "very high",
    "very_easy": "very easy",
    "very_difficult": "very difficult",
    "higher_education": "higher education",
    "educational_objective": "educational objective",
    "accessibility_restrictions": "accessibility restrictions",
    "educational_level": "educational level",
    "skill_level": "skill level",
    "security_level": "security level",
    "is_part_of": "ispartof",
    "has_part": "haspart",
    "is_version_of": "isversionof",
    "has_version": "hasversion",
    "is_format_of": "isformatof",
    "has_format": "hasformat",
    "is_referenced_by": "isreferencedby",
    "is_required_by": "isrequiredby",
    "is_similar_to": "issimilarto",
}


def _lom_vocab(token: Optional[str]) -> str:
    """Normalise a stored token to its LOM v1.0 vocabulary spelling."""
    if not token:
        return ""
    return _LOM_VOCAB_SPACES.get(token, str(token).replace("_", " "))


def build_ieee_lom_xml(lom_data: Optional[dict]) -> str:
    """Emit valid IEEE 1484.12.3 LOM XML (loose schema) from serialized LOM JSON.

    Vocabulary elements use ``<source>LOMv1.0</source><value>…</value>`` and
    LangString elements use ``<string language="…">…</string>``. Text is escaped
    via ElementTree. The platform pedagogical extension fields (§5 additions such
    as learning_objectives, prerequisites, …) are NOT standard LOM: objectives
    are surfaced as a ``<classification>`` with purpose "educational objective",
    and the remainder go into a namespaced ``<ex:extension>`` block at the end.
    """

    lom_data = lom_data or {}
    default_lang = str(lom_data.get("language") or "es") or "es"

    ET.register_namespace("", _LOM_NS)
    ET.register_namespace("xsi", _XSI_NS)
    ET.register_namespace("ex", _LOM_EXT_NS)

    root = ET.Element(
        f"{{{_LOM_NS}}}lom",
        {
            f"{{{_XSI_NS}}}schemaLocation": f"{_LOM_NS} lomLoose.xsd",
        },
    )

    def _q(tag: str) -> str:
        return f"{{{_LOM_NS}}}{tag}"

    def _sub(parent, tag):
        return ET.SubElement(parent, _q(tag))

    def _langstring(parent, tag, value, lang=None):
        """Append ``<tag><string language="lang">value</string></tag>``."""
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        node = _sub(parent, tag)
        s = _sub(node, "string")
        s.set("language", lang or default_lang)
        s.text = text
        return node

    def _vocab(parent, tag, token, source="LOMv1.0"):
        """Append ``<tag><source>LOMv1.0</source><value>token</value></tag>``."""
        value = _lom_vocab(token) if token else ""
        if not value:
            return None
        node = _sub(parent, tag)
        _sub(node, "source").text = source
        _sub(node, "value").text = value
        return node

    def _plain(parent, tag, value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        node = _sub(parent, tag)
        node.text = text
        return node

    def _keyword_list(raw):
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(k).strip() for k in raw if str(k).strip()]
        return [k.strip() for k in str(raw).split(",") if k.strip()]

    # --- 1. General ---
    general = _sub(root, "general")
    identifier = _sub(general, "identifier")
    _sub(identifier, "catalog").text = "URI"
    _sub(identifier, "entry").text = str(lom_data.get("id") or "")
    _langstring(general, "title", lom_data.get("title"))
    _plain(general, "language", lom_data.get("language") or default_lang)
    _langstring(general, "description", lom_data.get("description"))
    for kw in _keyword_list(lom_data.get("keywords")):
        _langstring(general, "keyword", kw)
    _langstring(general, "coverage", lom_data.get("coverage"))
    _vocab(general, "structure", lom_data.get("structure"))
    agg = lom_data.get("aggregation_level")
    if agg:
        _vocab(general, "aggregationLevel", str(agg))

    # --- 2. Life cycle ---
    lifecycle = lom_data.get("lifecycle") or {}
    if lifecycle:
        lc = _sub(root, "lifeCycle")
        version = lifecycle.get("version")
        if version:
            vnode = _sub(lc, "version")
            s = _sub(vnode, "string")
            s.set("language", default_lang)
            s.text = str(version)
        _vocab(lc, "status", lifecycle.get("status"))
        for c in lifecycle.get("contributors") or []:
            contribute = _sub(lc, "contribute")
            _vocab(contribute, "role", c.get("role"))
            # 2.3.2 Entity should be a vCard; we emit the plain name as text.
            entity = c.get("entity")
            if entity:
                _sub(contribute, "entity").text = str(entity)
            date = c.get("date")
            if date:
                dnode = _sub(contribute, "date")
                _sub(dnode, "dateTime").text = str(date)

    # --- 5. Educational (may repeat; we emit one block) ---
    educational = lom_data.get("educational")
    edu_entries = []
    if isinstance(educational, list):
        edu_entries = [e for e in educational if e]
    elif educational:
        edu_entries = [educational]

    for entry in edu_entries:
        edu = _sub(root, "educational")
        _vocab(edu, "interactivityType", entry.get("interactivity_type"))
        _vocab(edu, "learningResourceType", entry.get("learning_resource_type"))
        _vocab(edu, "interactivityLevel", entry.get("interactivity_level"))
        _vocab(edu, "semanticDensity", entry.get("semantic_density"))
        _vocab(edu, "intendedEndUserRole", entry.get("intended_end_user_role"))
        _vocab(edu, "context", entry.get("context"))
        _langstring(edu, "typicalAgeRange", entry.get("typical_age_range"))
        _vocab(edu, "difficulty", entry.get("difficulty"))
        tlt = entry.get("typical_learning_time")
        if tlt:
            # LOM 5.9 Duration datatype: <duration><duration>ISO</duration>…
            tnode = _sub(edu, "typicalLearningTime")
            _sub(tnode, "duration").text = str(tlt)
        _langstring(edu, "description", entry.get("description"),
                    lang=entry.get("language") or default_lang)

    # --- 6. Rights ---
    rights = lom_data.get("rights") or {}
    if rights:
        rnode = _sub(root, "rights")
        if "cost" in rights:
            _vocab(rnode, "cost", "yes" if rights.get("cost") else "no")
        if "copyright_and_other_restrictions" in rights:
            _vocab(
                rnode,
                "copyrightAndOtherRestrictions",
                "yes" if rights.get("copyright_and_other_restrictions") else "no",
            )
        _langstring(rnode, "description", rights.get("description"))

    # --- Learning objectives → a LOM 9.Classification (purpose "educational objective") ---
    objectives = []
    for entry in edu_entries:
        objs = entry.get("learning_objectives") or []
        if isinstance(objs, list):
            objectives.extend([str(o).strip() for o in objs if str(o).strip()])
    if objectives:
        cls = _sub(root, "classification")
        _vocab(cls, "purpose", "educational_objective")
        for obj in objectives:
            taxon_path = _sub(cls, "taxonPath")
            src = _sub(taxon_path, "source")
            ssrc = _sub(src, "string")
            ssrc.set("language", default_lang)
            ssrc.text = "Heritage Platform Learning Objectives"
            taxon = _sub(taxon_path, "taxon")
            _langstring(taxon, "entry", obj)
        _langstring(cls, "description",
                    "; ".join(objectives))

    # --- 9. Classification (repeat) ---
    for cls_data in lom_data.get("classifications") or []:
        if not cls_data:
            continue
        cls = _sub(root, "classification")
        _vocab(cls, "purpose", cls_data.get("purpose"))
        taxon_source = cls_data.get("taxon_source")
        taxon_id = cls_data.get("taxon_id")
        taxon_entry = cls_data.get("taxon_entry")
        if taxon_source or taxon_id or taxon_entry:
            taxon_path = _sub(cls, "taxonPath")
            if taxon_source:
                src = _sub(taxon_path, "source")
                ssrc = _sub(src, "string")
                ssrc.set("language", default_lang)
                ssrc.text = str(taxon_source)
            taxon = _sub(taxon_path, "taxon")
            if taxon_id:
                _sub(taxon, "id").text = str(taxon_id)
            if taxon_entry:
                _langstring(taxon, "entry", taxon_entry)
        _langstring(cls, "description", cls_data.get("description"))
        for kw in _keyword_list(cls_data.get("keywords")):
            _langstring(cls, "keyword", kw)

    # --- platform pedagogical extension (non-standard §5 additions) ---
    # Kept in a namespaced trailing block so the core document stays LOM-valid.
    ext_fields = ("prerequisites", "competencies", "pedagogical_approach",
                  "curriculum_alignment", "suggested_activities")
    ext_payload = {}
    for entry in edu_entries:
        for f in ext_fields:
            val = entry.get(f)
            if val:
                ext_payload[f] = val
    if ext_payload:
        ext = ET.SubElement(root, f"{{{_LOM_EXT_NS}}}extension")
        for key, value in ext_payload.items():
            child = ET.SubElement(ext, f"{{{_LOM_EXT_NS}}}{key}")
            child.text = str(value)

    return _pretty_xml(root)


def _build_imsmanifest_xml(
    package_id: str,
    title: str,
    file_hrefs: Iterable[str],
    include_metadata_location: bool = True,
    metadata_location: str = "metadata/lom.xml",
) -> str:
    ns_imscp = "http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    ns_adlcp = "http://www.adlnet.org/xsd/adlcp_rootv1p2"
    ns_xsi = "http://www.w3.org/2001/XMLSchema-instance"

    ET.register_namespace("", ns_imscp)
    ET.register_namespace("adlcp", ns_adlcp)
    ET.register_namespace("xsi", ns_xsi)

    manifest = ET.Element(
        f"{{{ns_imscp}}}manifest",
        {
            "identifier": package_id,
            f"{{{ns_xsi}}}schemaLocation": (
                f"{ns_imscp} imscp_rootv1p1p2.xsd {ns_adlcp} adlcp_rootv1p2.xsd"
            ),
        },
    )

    metadata = ET.SubElement(manifest, f"{{{ns_imscp}}}metadata")
    ET.SubElement(metadata, f"{{{ns_imscp}}}schema").text = "ADL SCORM"
    ET.SubElement(metadata, f"{{{ns_imscp}}}schemaversion").text = "1.2"
    if include_metadata_location:
        ET.SubElement(metadata, f"{{{ns_adlcp}}}location").text = metadata_location

    organizations = ET.SubElement(manifest, f"{{{ns_imscp}}}organizations", {"default": "ORG-1"})
    organization = ET.SubElement(organizations, f"{{{ns_imscp}}}organization", {"identifier": "ORG-1"})
    ET.SubElement(organization, f"{{{ns_imscp}}}title").text = title
    item = ET.SubElement(
        organization,
        f"{{{ns_imscp}}}item",
        {"identifier": "ITEM-1", "identifierref": "RES-1"},
    )
    ET.SubElement(item, f"{{{ns_imscp}}}title").text = title

    resources = ET.SubElement(manifest, f"{{{ns_imscp}}}resources")
    resource = ET.SubElement(
        resources,
        f"{{{ns_imscp}}}resource",
        {
            "identifier": "RES-1",
            "type": "webcontent",
            f"{{{ns_adlcp}}}scormtype": "sco",
            "href": "index.html",
        },
    )

    for href in sorted(set(file_hrefs)):
        ET.SubElement(resource, f"{{{ns_imscp}}}file", {"href": href})

    return _pretty_xml(manifest)


def _build_scorm_js() -> str:
    # Minimal SCORM 1.2 runtime wrapper.
    return """(function () {
  function findApi(win) {
    var maxTries = 500;
    while (win && maxTries--) {
      if (win.API && typeof win.API.LMSInitialize === 'function') {
        return win.API;
      }
      win = win.parent;
    }
    return null;
  }

  var api = null;
  var initialized = false;

  function init() {
    if (initialized) return;
    api = findApi(window);
    if (!api) return;
    try {
      api.LMSInitialize('');
      initialized = true;
    } catch (e) {
      // ignore
    }
  }

  function setCompleted() {
    if (!initialized || !api) return;
    try {
      api.LMSSetValue('cmi.core.lesson_status', 'completed');
      api.LMSCommit('');
    } catch (e) {
      // ignore
    }
  }

  function finish() {
    if (!initialized || !api) return;
    try {
      api.LMSCommit('');
      api.LMSFinish('');
    } catch (e) {
      // ignore
    }
  }

  window.addEventListener('load', function () {
    init();
    setCompleted();
  });

  window.addEventListener('beforeunload', function () {
    finish();
  });
})();
"""


def _build_index_html(
    title: str,
    description: str,
    lom_json: str,
    assets: list[ScormAsset],
    runtime_js: str = "scorm.js",
) -> str:
    escaped_title = html.escape(title)
    escaped_desc = html.escape(description or "")
    runtime_src = html.escape(runtime_js)

    sections: list[str] = []
    images = [a for a in assets if a.kind == "image"]
    audio = [a for a in assets if a.kind == "audio"]
    video = [a for a in assets if a.kind == "video"]
    docs = [a for a in assets if a.kind == "document"]

    if images:
        sections.append("<h2>Images</h2>")
        for a in images:
            sections.append(
                f'<figure><img src="{html.escape(a.href)}" alt="{html.escape(a.title)}" style="max-width:100%;height:auto"/><figcaption>{html.escape(a.title)}</figcaption></figure>'
            )

    if audio:
        sections.append("<h2>Audio</h2>")
        for a in audio:
            sections.append(
                f'<div><div>{html.escape(a.title)}</div><audio controls src="{html.escape(a.href)}"></audio></div>'
            )

    if video:
        sections.append("<h2>Video</h2>")
        for a in video:
            sections.append(
                f'<div><div>{html.escape(a.title)}</div><video controls style="max-width:100%" src="{html.escape(a.href)}"></video></div>'
            )

    if docs:
        sections.append("<h2>Documents</h2>")
        for a in docs:
            mime = _guess_mime(a.href)
            if mime == "application/pdf" or mime.startswith("text/"):
                sections.append(
                    f'<div><div>{html.escape(a.title)}</div><iframe title="{html.escape(a.title)}" src="{html.escape(a.href)}" style="width:100%;height:520px;border:1px solid #ddd"></iframe></div>'
                )
            else:
                sections.append(
                    f'<div><a href="{html.escape(a.href)}" target="_blank" rel="noopener">{html.escape(a.title)}</a></div>'
                )

    sections_html = "\n".join(sections) if sections else "<p>No bundled media.</p>"

    # Embed LOM JSON for offline viewing.
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escaped_title}</title>
  <script src=\"{runtime_src}\"></script>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; line-height: 1.45; }}
    h1 {{ margin: 0 0 8px; }}
    .muted {{ color: #666; }}
    .box {{ background: #fafafa; border: 1px solid #eee; border-radius: 10px; padding: 16px; margin-top: 24px; }}
    pre {{ white-space: pre-wrap; word-break: break-word; }}
  </style>
</head>
<body>
  <h1>{escaped_title}</h1>
  <div class=\"muted\">Exported: {html.escape(timezone.now().isoformat())}</div>
  <p>{escaped_desc}</p>

  {sections_html}

  <div class=\"box\">
    <h2>LOM metadata (JSON)</h2>
    <pre id=\"lom\"></pre>
  </div>

  <script type=\"application/json\" id=\"lom-json\">{html.escape(lom_json)}</script>
  <script>
    try {{
            var raw = document.getElementById('lom-json').textContent || '{{}}';
      var obj = JSON.parse(raw);
      document.getElementById('lom').textContent = JSON.stringify(obj, null, 2);
    }} catch (e) {{
      document.getElementById('lom').textContent = 'Failed to load LOM metadata.';
    }}
  </script>
</body>
</html>
"""


def _build_imsmanifest_2004_xml(
    package_id: str,
    title: str,
    file_hrefs: Iterable[str],
    metadata_location: str = "metadata/lom.xml",
) -> str:
    """SCORM 2004 4th Edition imsmanifest.xml.

    Uses the 2004 namespace set (imscp v1p1, adlcp v1p3, adlseq, adlnav, imsss)
    and declares the resource ``adlcp:scormType="sco"`` with a minimal default
    sequencing on the organization.
    """
    ns_imscp = "http://www.imsglobal.org/xsd/imscp_v1p1"
    ns_adlcp = "http://www.adlnet.org/xsd/adlcp_v1p3"
    ns_adlseq = "http://www.adlnet.org/xsd/adlseq_v1p3"
    ns_adlnav = "http://www.adlnet.org/xsd/adlnav_v1p3"
    ns_imsss = "http://www.imsglobal.org/xsd/imsss"
    ns_xsi = "http://www.w3.org/2001/XMLSchema-instance"

    ET.register_namespace("", ns_imscp)
    ET.register_namespace("adlcp", ns_adlcp)
    ET.register_namespace("adlseq", ns_adlseq)
    ET.register_namespace("adlnav", ns_adlnav)
    ET.register_namespace("imsss", ns_imsss)
    ET.register_namespace("xsi", ns_xsi)

    manifest = ET.Element(
        f"{{{ns_imscp}}}manifest",
        {
            "identifier": package_id,
            "version": "1",
            f"{{{ns_xsi}}}schemaLocation": (
                f"{ns_imscp} imscp_v1p1.xsd "
                f"{ns_adlcp} adlcp_v1p3.xsd "
                f"{ns_adlseq} adlseq_v1p3.xsd "
                f"{ns_adlnav} adlnav_v1p3.xsd "
                f"{ns_imsss} imsss_v1p0.xsd"
            ),
        },
    )

    metadata = ET.SubElement(manifest, f"{{{ns_imscp}}}metadata")
    ET.SubElement(metadata, f"{{{ns_imscp}}}schema").text = "ADL SCORM"
    ET.SubElement(metadata, f"{{{ns_imscp}}}schemaversion").text = "2004 4th Edition"
    ET.SubElement(metadata, f"{{{ns_adlcp}}}location").text = metadata_location

    organizations = ET.SubElement(
        manifest, f"{{{ns_imscp}}}organizations", {"default": "ORG-1"}
    )
    organization = ET.SubElement(
        organizations, f"{{{ns_imscp}}}organization", {"identifier": "ORG-1"}
    )
    ET.SubElement(organization, f"{{{ns_imscp}}}title").text = title
    item = ET.SubElement(
        organization,
        f"{{{ns_imscp}}}item",
        {"identifier": "ITEM-1", "identifierref": "RES-1"},
    )
    ET.SubElement(item, f"{{{ns_imscp}}}title").text = title
    # Minimal default sequencing so LMSs accept the package.
    ET.SubElement(organization, f"{{{ns_imsss}}}sequencing")

    resources = ET.SubElement(manifest, f"{{{ns_imscp}}}resources")
    resource = ET.SubElement(
        resources,
        f"{{{ns_imscp}}}resource",
        {
            "identifier": "RES-1",
            "type": "webcontent",
            f"{{{ns_adlcp}}}scormType": "sco",
            "href": "index.html",
        },
    )
    for href in sorted(set(file_hrefs)):
        ET.SubElement(resource, f"{{{ns_imscp}}}file", {"href": href})

    return _pretty_xml(manifest)


def _build_scorm_2004_js() -> str:
    # Minimal SCORM 2004 4th Edition runtime wrapper (API_1484_11).
    return """(function () {
  function findApi(win) {
    var maxTries = 500;
    while (win && maxTries--) {
      if (win.API_1484_11 && typeof win.API_1484_11.Initialize === 'function') {
        return win.API_1484_11;
      }
      win = win.parent;
    }
    return null;
  }

  var api = null;
  var initialized = false;

  function init() {
    if (initialized) return;
    api = findApi(window);
    if (!api) return;
    try {
      api.Initialize('');
      initialized = true;
    } catch (e) {
      // ignore
    }
  }

  function setCompleted() {
    if (!initialized || !api) return;
    try {
      api.SetValue('cmi.completion_status', 'completed');
      api.SetValue('cmi.success_status', 'passed');
      api.Commit('');
    } catch (e) {
      // ignore
    }
  }

  function finish() {
    if (!initialized || !api) return;
    try {
      api.Commit('');
      api.Terminate('');
    } catch (e) {
      // ignore
    }
  }

  window.addEventListener('load', function () {
    init();
    setCompleted();
  });

  window.addEventListener('beforeunload', function () {
    finish();
  });
})();
"""


def _build_cmi5_js() -> str:
    # Defensive cmi5 / xAPI stub. A real launch supplies endpoint/auth/actor/
    # registration query params and an LRS to POST statements to; without those
    # this no-ops gracefully so the content still renders standalone.
    return """(function () {
  function getParams() {
    try {
      var p = new URLSearchParams(window.location.search);
      return {
        endpoint: p.get('endpoint'),
        auth: p.get('auth'),
        actor: p.get('actor'),
        registration: p.get('registration'),
        activityId: p.get('activityId'),
      };
    } catch (e) {
      return {};
    }
  }

  function sendCompleted() {
    var cfg = getParams();
    // No LRS/launch context => nothing to do (standalone viewing).
    if (!cfg.endpoint || !cfg.auth || !cfg.actor) {
      return;
    }
    try {
      var actor = JSON.parse(cfg.actor);
      var stmt = {
        actor: actor,
        verb: {
          id: 'http://adlnet.gov/expapi/verbs/completed',
          display: { 'en-US': 'completed' }
        },
        object: {
          id: cfg.activityId || (window.location.origin + window.location.pathname),
          objectType: 'Activity'
        }
      };
      if (cfg.registration) {
        stmt.context = { registration: cfg.registration };
      }
      // A real integration would honour the cmi5 "moveOn" and send
      // initialized/passed/completed. This is a single best-effort statement.
      fetch(cfg.endpoint.replace(/\\/$/, '') + '/statements', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': cfg.auth,
          'X-Experience-API-Version': '1.0.3'
        },
        body: JSON.stringify(stmt)
      }).catch(function () { /* ignore: no LRS reachable */ });
    } catch (e) {
      // ignore: malformed launch context
    }
  }

  window.addEventListener('load', function () {
    // Give the page a beat to render before reporting completion.
    setTimeout(sendCompleted, 500);
  });
})();
"""


def _copy_media_into_zip(zf: zipfile.ZipFile, media_files: Iterable, prefix: str = "") -> list[ScormAsset]:
    """Stream each media file into ``assets/[{prefix}/]{kind}/{id}{ext}``.

    Returns the list of :class:`ScormAsset` written. Shared by every package
    builder so the copy loop lives in exactly one place.
    """
    assets: list[ScormAsset] = []
    for mf in media_files:
        if not getattr(mf, "file", None) or not getattr(mf.file, "name", None):
            continue

        ext = Path(mf.file.name).suffix
        kind = getattr(mf, "file_type", "asset")
        label = getattr(mf, "caption", None) or getattr(mf, "alt_text", None) or Path(mf.file.name).name

        sub = f"{prefix}/" if prefix else ""
        href = f"assets/{sub}{kind}/{mf.id}{ext}"
        assets.append(ScormAsset(href=href, title=str(label)[:200], kind=kind))

        with zf.open(href, "w") as dst:
            mf.file.open("rb")
            try:
                for chunk in iter(lambda: mf.file.read(1024 * 1024), b""):
                    dst.write(chunk)
            finally:
                mf.file.close()
    return assets


def _write_single_item_package(
    zf: zipfile.ZipFile,
    *,
    safe_title: str,
    description: str,
    lom_data: Optional[dict],
    media_files: Iterable,
    runtime_js_name: str,
    runtime_js: str,
) -> list[str]:
    """Write the common file set (media, runtime, index.html, LOM metadata) for a
    single-item SCORM/cmi5 package into ``zf``.

    ``metadata/lom.xml`` is the *valid* IEEE LOM (build_ieee_lom_xml); the flat
    legacy dump is kept alongside as ``metadata/lom-flat.xml`` for debugging.
    Returns the list of file hrefs (for the manifest ``<resource>``).
    """
    lom_json = json.dumps(lom_data or {}, ensure_ascii=False)

    assets = _copy_media_into_zip(zf, media_files)

    zf.writestr(runtime_js_name, runtime_js)
    zf.writestr("metadata/lom.json", json.dumps(lom_data or {}, ensure_ascii=False, indent=2))
    zf.writestr("metadata/lom.xml", build_ieee_lom_xml(lom_data))
    zf.writestr("metadata/lom-flat.xml", _build_lom_xml(lom_data))

    index_html = _build_index_html(
        title=safe_title,
        description=description or "",
        lom_json=lom_json,
        assets=assets,
        runtime_js=runtime_js_name,
    )
    zf.writestr("index.html", index_html)

    return [
        "index.html",
        runtime_js_name,
        "metadata/lom.json",
        "metadata/lom.xml",
        "metadata/lom-flat.xml",
    ] + [a.href for a in assets]


def build_scorm_12_pif_zip(
    *,
    title: str,
    description: str,
    lom_data: Optional[dict],
    media_files: Iterable,
) -> tuple[io.BufferedIOBase, str]:
    """Build a SCORM 1.2 package interchange file (ZIP) as a file-like object.

    Returns (file_like, filename).
    """

    safe_title = title or "Heritage Item"
    base_name = _slugify_filename(safe_title, fallback="heritage-item")
    filename = f"{base_name}-scorm12.zip"

    # Use SpooledTemporaryFile so small packages stay in memory and larger spill to disk.
    spooled = tempfile.SpooledTemporaryFile(max_size=50 * 1024 * 1024, mode="w+b")

    with zipfile.ZipFile(spooled, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        file_hrefs = _write_single_item_package(
            zf,
            safe_title=safe_title,
            description=description,
            lom_data=lom_data,
            media_files=media_files,
            runtime_js_name="scorm.js",
            runtime_js=_build_scorm_js(),
        )

        imsmanifest = _build_imsmanifest_xml(
            package_id=f"MANIFEST-{base_name}",
            title=safe_title,
            file_hrefs=file_hrefs,
            include_metadata_location=True,
        )
        zf.writestr("imsmanifest.xml", imsmanifest)

    spooled.seek(0)
    return spooled, filename


def build_scorm_2004_pif_zip(
    *,
    title: str,
    description: str,
    lom_data: Optional[dict],
    media_files: Iterable,
) -> tuple[io.BufferedIOBase, str]:
    """Build a SCORM 2004 4th Edition package interchange file (ZIP).

    Same content set as the 1.2 package, but with a 2004 manifest (imsss default
    sequencing, adlcp v1p3) and the API_1484_11 runtime. Returns (file_like,
    filename).
    """

    safe_title = title or "Heritage Item"
    base_name = _slugify_filename(safe_title, fallback="heritage-item")
    filename = f"{base_name}-scorm2004.zip"

    spooled = tempfile.SpooledTemporaryFile(max_size=50 * 1024 * 1024, mode="w+b")

    with zipfile.ZipFile(spooled, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        file_hrefs = _write_single_item_package(
            zf,
            safe_title=safe_title,
            description=description,
            lom_data=lom_data,
            media_files=media_files,
            runtime_js_name="scorm2004.js",
            runtime_js=_build_scorm_2004_js(),
        )

        imsmanifest = _build_imsmanifest_2004_xml(
            package_id=f"MANIFEST-{base_name}",
            title=safe_title,
            file_hrefs=file_hrefs,
        )
        zf.writestr("imsmanifest.xml", imsmanifest)

    spooled.seek(0)
    return spooled, filename


def _build_cmi5_course_xml(course_id: str, title: str, description: str, au_url: str = "index.html") -> str:
    """cmi5 course structure (cmi5.xml) with a single assignable unit (AU)."""
    ns = "https://w3id.org/xapi/profiles/cmi5/v1/CourseStructure.xsd"
    ns_xsi = "http://www.w3.org/2001/XMLSchema-instance"

    ET.register_namespace("", ns)
    ET.register_namespace("xsi", ns_xsi)

    course_structure = ET.Element(
        f"{{{ns}}}courseStructure",
        {f"{{{ns_xsi}}}noNamespaceSchemaLocation": "CourseStructure.xsd"},
    )

    course = ET.SubElement(course_structure, f"{{{ns}}}course", {"id": course_id})
    title_el = ET.SubElement(course, f"{{{ns}}}title")
    ET.SubElement(title_el, f"{{{ns}}}langstring", {"lang": "es"}).text = title
    desc_el = ET.SubElement(course, f"{{{ns}}}description")
    ET.SubElement(desc_el, f"{{{ns}}}langstring", {"lang": "es"}).text = description or title

    au = ET.SubElement(
        course_structure,
        f"{{{ns}}}au",
        {"id": f"{course_id}/au/1", "moveOn": "Completed"},
    )
    au_title = ET.SubElement(au, f"{{{ns}}}title")
    ET.SubElement(au_title, f"{{{ns}}}langstring", {"lang": "es"}).text = title
    au_desc = ET.SubElement(au, f"{{{ns}}}description")
    ET.SubElement(au_desc, f"{{{ns}}}langstring", {"lang": "es"}).text = description or title
    ET.SubElement(au, f"{{{ns}}}url").text = au_url

    return _pretty_xml(course_structure)


def build_cmi5_zip(
    *,
    title: str,
    description: str,
    lom_data: Optional[dict],
    media_files: Iterable,
) -> tuple[io.BufferedIOBase, str]:
    """Build a minimal cmi5 (xAPI) package: a cmi5.xml course structure with one
    AU pointing at index.html, the media + index.html, and a defensive xAPI
    runtime that no-ops without an LRS/launch context. Returns (file_like,
    filename).
    """

    safe_title = title or "Heritage Item"
    base_name = _slugify_filename(safe_title, fallback="heritage-item")
    filename = f"{base_name}-cmi5.zip"
    course_id = f"https://heritageplatform.ddns.net/cmi5/{base_name}"

    spooled = tempfile.SpooledTemporaryFile(max_size=50 * 1024 * 1024, mode="w+b")

    with zipfile.ZipFile(spooled, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        _write_single_item_package(
            zf,
            safe_title=safe_title,
            description=description,
            lom_data=lom_data,
            media_files=media_files,
            runtime_js_name="cmi5.js",
            runtime_js=_build_cmi5_js(),
        )
        # cmi5 uses cmi5.xml (not imsmanifest.xml) as its course descriptor.
        zf.writestr("cmi5.xml", _build_cmi5_course_xml(course_id, safe_title, description))

    spooled.seek(0)
    return spooled, filename


# ---------------------------------------------------------------------------
# Collection / multi-item packaging (task F2.c.2 — joins with routes)
# ---------------------------------------------------------------------------


def _build_collection_index_html(title: str, description: str, sections: list[tuple[str, str, list[ScormAsset]]]) -> str:
    """One index.html with a table of contents + a section per collection entry.

    ``sections`` is a list of ``(anchor_id, item_title, assets)`` tuples.
    """
    escaped_title = html.escape(title)
    escaped_desc = html.escape(description or "")

    toc_items = "\n".join(
        f'<li><a href="#{html.escape(anchor)}">{html.escape(item_title)}</a></li>'
        for anchor, item_title, _ in sections
    )

    body_sections: list[str] = []
    for anchor, item_title, assets in sections:
        body_sections.append(f'<section id="{html.escape(anchor)}"><h2>{html.escape(item_title)}</h2>')
        for a in assets:
            if a.kind == "image":
                body_sections.append(
                    f'<figure><img src="{html.escape(a.href)}" alt="{html.escape(a.title)}" style="max-width:100%;height:auto"/><figcaption>{html.escape(a.title)}</figcaption></figure>'
                )
            elif a.kind == "audio":
                body_sections.append(
                    f'<div><div>{html.escape(a.title)}</div><audio controls src="{html.escape(a.href)}"></audio></div>'
                )
            elif a.kind == "video":
                body_sections.append(
                    f'<div><div>{html.escape(a.title)}</div><video controls style="max-width:100%" src="{html.escape(a.href)}"></video></div>'
                )
            else:
                body_sections.append(
                    f'<div><a href="{html.escape(a.href)}" target="_blank" rel="noopener">{html.escape(a.title)}</a></div>'
                )
        body_sections.append("</section>")

    sections_html = "\n".join(body_sections) if body_sections else "<p>No bundled media.</p>"

    return f"""<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escaped_title}</title>
  <script src=\"scorm.js\"></script>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; line-height: 1.45; }}
    h1 {{ margin: 0 0 8px; }}
    .muted {{ color: #666; }}
    nav ul {{ padding-left: 20px; }}
    section {{ border-top: 1px solid #eee; padding-top: 16px; margin-top: 24px; }}
  </style>
</head>
<body>
  <h1>{escaped_title}</h1>
  <div class=\"muted\">Exported: {html.escape(timezone.now().isoformat())}</div>
  <p>{escaped_desc}</p>
  <nav><h2>Contenido</h2><ul>
  {toc_items}
  </ul></nav>
  {sections_html}
</body>
</html>
"""


def build_collection_scorm_zip(
    *,
    title: str,
    description: str,
    entries: list,
    package_format: str = "scorm12",
) -> tuple[io.BufferedIOBase, str]:
    """Bundle MULTIPLE heritage items into ONE learning package.

    ``entries`` is a list of dicts:
        {"heritage_item": <HeritageItem>, "lom_data": <dict>, "media_files": [<MediaFile>...]}

    Media go under ``assets/{item_slug}/{kind}/{id}{ext}``; a single index.html
    holds a table of contents + one section per item; the manifest organization
    has one ``<item>`` per entry. A top-level ``metadata/lom.xml`` describes the
    whole collection (structure "collection"). ``package_format`` is "scorm12"
    or "scorm2004". Returns (file_like, filename).
    """
    is_2004 = package_format == "scorm2004"
    safe_title = title or "Heritage Collection"
    base_name = _slugify_filename(safe_title, fallback="heritage-collection")
    suffix = "scorm2004" if is_2004 else "scorm12"
    filename = f"{base_name}-{suffix}.zip"

    # Collection-level LOM: aggregationLevel 2+, structure "collection".
    collection_lom = {
        "id": base_name,
        "title": safe_title,
        "description": description or safe_title,
        "structure": "collection",
        "aggregation_level": 2,
    }

    spooled = tempfile.SpooledTemporaryFile(max_size=100 * 1024 * 1024, mode="w+b")

    with zipfile.ZipFile(spooled, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        sections: list[tuple[str, str, list[ScormAsset]]] = []
        # (item_identifier, item_title) for the manifest organization.
        manifest_items: list[tuple[str, str]] = []
        used_slugs: set[str] = set()

        for idx, entry in enumerate(entries, start=1):
            item = entry.get("heritage_item")
            lom_data = entry.get("lom_data") or {}
            media_files = entry.get("media_files") or []

            item_title = (
                lom_data.get("title")
                or getattr(item, "title", None)
                or f"Item {idx}"
            )
            slug = _slugify_filename(str(item_title), fallback=f"item-{idx}")
            # Ensure a unique per-item asset folder even on title collisions.
            if slug in used_slugs:
                slug = f"{slug}-{idx}"
            used_slugs.add(slug)

            assets = _copy_media_into_zip(zf, media_files, prefix=slug)
            # Per-item LOM metadata for provenance/round-tripping.
            zf.writestr(
                f"metadata/{slug}/lom.json",
                json.dumps(lom_data, ensure_ascii=False, indent=2),
            )
            zf.writestr(f"metadata/{slug}/lom.xml", build_ieee_lom_xml(lom_data))

            sections.append((slug, str(item_title), assets))
            manifest_items.append((f"ITEM-{idx}", str(item_title)))

        # Runtime + collection index + collection metadata.
        runtime_name = "scorm.js"
        zf.writestr(runtime_name, _build_scorm_2004_js() if is_2004 else _build_scorm_js())
        zf.writestr(
            "metadata/lom.json",
            json.dumps(collection_lom, ensure_ascii=False, indent=2),
        )
        zf.writestr("metadata/lom.xml", build_ieee_lom_xml(collection_lom))

        index_html = _build_collection_index_html(safe_title, description, sections)
        zf.writestr("index.html", index_html)

        # Gather every file href for the manifest resource.
        file_hrefs = ["index.html", runtime_name, "metadata/lom.json", "metadata/lom.xml"]
        for slug, _title, assets in sections:
            file_hrefs.append(f"metadata/{slug}/lom.json")
            file_hrefs.append(f"metadata/{slug}/lom.xml")
            file_hrefs.extend(a.href for a in assets)

        if is_2004:
            manifest = _build_collection_manifest_2004_xml(
                package_id=f"MANIFEST-{base_name}",
                title=safe_title,
                items=manifest_items,
                file_hrefs=file_hrefs,
            )
        else:
            manifest = _build_collection_manifest_12_xml(
                package_id=f"MANIFEST-{base_name}",
                title=safe_title,
                items=manifest_items,
                file_hrefs=file_hrefs,
            )
        zf.writestr("imsmanifest.xml", manifest)

    spooled.seek(0)
    return spooled, filename


def _build_collection_manifest_12_xml(
    package_id: str,
    title: str,
    items: list,
    file_hrefs: Iterable[str],
) -> str:
    """SCORM 1.2 manifest whose single organization lists one <item> per entry.

    All items point at the same SCO resource (RES-1 = index.html) with the
    per-item anchor conveyed via the collection index's table of contents.
    """
    ns_imscp = "http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    ns_adlcp = "http://www.adlnet.org/xsd/adlcp_rootv1p2"
    ns_xsi = "http://www.w3.org/2001/XMLSchema-instance"

    ET.register_namespace("", ns_imscp)
    ET.register_namespace("adlcp", ns_adlcp)
    ET.register_namespace("xsi", ns_xsi)

    manifest = ET.Element(
        f"{{{ns_imscp}}}manifest",
        {
            "identifier": package_id,
            f"{{{ns_xsi}}}schemaLocation": (
                f"{ns_imscp} imscp_rootv1p1p2.xsd {ns_adlcp} adlcp_rootv1p2.xsd"
            ),
        },
    )

    metadata = ET.SubElement(manifest, f"{{{ns_imscp}}}metadata")
    ET.SubElement(metadata, f"{{{ns_imscp}}}schema").text = "ADL SCORM"
    ET.SubElement(metadata, f"{{{ns_imscp}}}schemaversion").text = "1.2"
    ET.SubElement(metadata, f"{{{ns_adlcp}}}location").text = "metadata/lom.xml"

    organizations = ET.SubElement(manifest, f"{{{ns_imscp}}}organizations", {"default": "ORG-1"})
    organization = ET.SubElement(organizations, f"{{{ns_imscp}}}organization", {"identifier": "ORG-1"})
    ET.SubElement(organization, f"{{{ns_imscp}}}title").text = title
    for item_id, item_title in items:
        item = ET.SubElement(
            organization,
            f"{{{ns_imscp}}}item",
            {"identifier": item_id, "identifierref": "RES-1"},
        )
        ET.SubElement(item, f"{{{ns_imscp}}}title").text = item_title

    resources = ET.SubElement(manifest, f"{{{ns_imscp}}}resources")
    resource = ET.SubElement(
        resources,
        f"{{{ns_imscp}}}resource",
        {
            "identifier": "RES-1",
            "type": "webcontent",
            f"{{{ns_adlcp}}}scormtype": "sco",
            "href": "index.html",
        },
    )
    for href in sorted(set(file_hrefs)):
        ET.SubElement(resource, f"{{{ns_imscp}}}file", {"href": href})

    return _pretty_xml(manifest)


def _build_collection_manifest_2004_xml(
    package_id: str,
    title: str,
    items: list,
    file_hrefs: Iterable[str],
) -> str:
    """SCORM 2004 manifest whose single organization lists one <item> per entry."""
    ns_imscp = "http://www.imsglobal.org/xsd/imscp_v1p1"
    ns_adlcp = "http://www.adlnet.org/xsd/adlcp_v1p3"
    ns_adlseq = "http://www.adlnet.org/xsd/adlseq_v1p3"
    ns_adlnav = "http://www.adlnet.org/xsd/adlnav_v1p3"
    ns_imsss = "http://www.imsglobal.org/xsd/imsss"
    ns_xsi = "http://www.w3.org/2001/XMLSchema-instance"

    ET.register_namespace("", ns_imscp)
    ET.register_namespace("adlcp", ns_adlcp)
    ET.register_namespace("adlseq", ns_adlseq)
    ET.register_namespace("adlnav", ns_adlnav)
    ET.register_namespace("imsss", ns_imsss)
    ET.register_namespace("xsi", ns_xsi)

    manifest = ET.Element(
        f"{{{ns_imscp}}}manifest",
        {
            "identifier": package_id,
            "version": "1",
            f"{{{ns_xsi}}}schemaLocation": (
                f"{ns_imscp} imscp_v1p1.xsd "
                f"{ns_adlcp} adlcp_v1p3.xsd "
                f"{ns_adlseq} adlseq_v1p3.xsd "
                f"{ns_adlnav} adlnav_v1p3.xsd "
                f"{ns_imsss} imsss_v1p0.xsd"
            ),
        },
    )

    metadata = ET.SubElement(manifest, f"{{{ns_imscp}}}metadata")
    ET.SubElement(metadata, f"{{{ns_imscp}}}schema").text = "ADL SCORM"
    ET.SubElement(metadata, f"{{{ns_imscp}}}schemaversion").text = "2004 4th Edition"
    ET.SubElement(metadata, f"{{{ns_adlcp}}}location").text = "metadata/lom.xml"

    organizations = ET.SubElement(manifest, f"{{{ns_imscp}}}organizations", {"default": "ORG-1"})
    organization = ET.SubElement(organizations, f"{{{ns_imscp}}}organization", {"identifier": "ORG-1"})
    ET.SubElement(organization, f"{{{ns_imscp}}}title").text = title
    for item_id, item_title in items:
        item = ET.SubElement(
            organization,
            f"{{{ns_imscp}}}item",
            {"identifier": item_id, "identifierref": "RES-1"},
        )
        ET.SubElement(item, f"{{{ns_imscp}}}title").text = item_title
    ET.SubElement(organization, f"{{{ns_imsss}}}sequencing")

    resources = ET.SubElement(manifest, f"{{{ns_imscp}}}resources")
    resource = ET.SubElement(
        resources,
        f"{{{ns_imscp}}}resource",
        {
            "identifier": "RES-1",
            "type": "webcontent",
            f"{{{ns_adlcp}}}scormType": "sco",
            "href": "index.html",
        },
    )
    for href in sorted(set(file_hrefs)):
        ET.SubElement(resource, f"{{{ns_imscp}}}file", {"href": href})

    return _pretty_xml(manifest)
