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


def _build_imsmanifest_xml(
    package_id: str,
    title: str,
    file_hrefs: Iterable[str],
    include_metadata_location: bool = True,
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
        ET.SubElement(metadata, f"{{{ns_adlcp}}}location").text = "metadata/lom.xml"

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
) -> str:
    escaped_title = html.escape(title)
    escaped_desc = html.escape(description or "")

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
  <script src=\"scorm.js\"></script>
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

    lom_json = json.dumps(lom_data or {}, ensure_ascii=False)
    lom_xml = _build_lom_xml(lom_data)

    assets: list[ScormAsset] = []

    # Use SpooledTemporaryFile so small packages stay in memory and larger spill to disk.
    spooled = tempfile.SpooledTemporaryFile(max_size=50 * 1024 * 1024, mode="w+b")

    with zipfile.ZipFile(spooled, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Collect and copy media
        for mf in media_files:
            if not getattr(mf, "file", None) or not getattr(mf.file, "name", None):
                continue

            ext = Path(mf.file.name).suffix
            kind = getattr(mf, "file_type", "asset")
            label = getattr(mf, "caption", None) or getattr(mf, "alt_text", None) or Path(mf.file.name).name

            href = f"assets/{kind}/{mf.id}{ext}"
            assets.append(ScormAsset(href=href, title=str(label)[:200], kind=kind))

            with zf.open(href, "w") as dst:
                mf.file.open("rb")
                try:
                    # Stream content into zip.
                    for chunk in iter(lambda: mf.file.read(1024 * 1024), b""):
                        dst.write(chunk)
                finally:
                    mf.file.close()

        # Core files
        zf.writestr("scorm.js", _build_scorm_js())
        zf.writestr("metadata/lom.json", json.dumps(lom_data or {}, ensure_ascii=False, indent=2))
        zf.writestr("metadata/lom.xml", lom_xml)

        index_html = _build_index_html(
            title=safe_title,
            description=description or "",
            lom_json=lom_json,
            assets=assets,
        )
        zf.writestr("index.html", index_html)

        file_hrefs = [
            "index.html",
            "scorm.js",
            "metadata/lom.json",
            "metadata/lom.xml",
        ] + [a.href for a in assets]

        imsmanifest = _build_imsmanifest_xml(
            package_id=f"MANIFEST-{base_name}",
            title=safe_title,
            file_hrefs=file_hrefs,
            include_metadata_location=True,
        )
        zf.writestr("imsmanifest.xml", imsmanifest)

    spooled.seek(0)
    return spooled, filename
