"""HTML sanitization for user-authored rich-text fields.

``EducationalResource.content`` is stored as raw HTML and rendered with Vue's
``v-html`` in the SPA, so any HTML that reaches the DB is executed in the
browser of everyone who views the resource. Because the write endpoint is a
plain ``ModelViewSet`` gated only by ``IsAuthenticatedOrReadOnly``, ANY
authenticated user (down to a self-registered tourist) could otherwise store a
``<script>``/``onerror`` payload — a stored-XSS against all readers.

We sanitize on write (in the serializer) rather than only at the render sink so
every consumer is protected: the SPA, the DRF ``search`` on ``content``, the
admin, and any future API client all get already-clean HTML.

Uses ``nh3`` (Rust ``ammonia`` bindings) with an allowlist so legitimate rich
formatting (headings, lists, links, emphasis) survives while scripts, event
handlers, iframes, and ``javascript:`` URLs are stripped.
"""

import nh3

# Tags allowed in rich content. nh3 drops everything else (and always drops
# <script>/<style> content). Intentionally excludes <iframe>, <object>,
# <embed>, <form>, and inputs.
_ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "cite", "code", "col",
    "colgroup", "dd", "del", "div", "dl", "dt", "em", "figcaption", "figure",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "ins", "li", "mark",
    "ol", "p", "pre", "q", "s", "small", "span", "strong", "sub", "sup",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}

# Per-tag attribute allowlist. No ``style`` (CSS can smuggle behaviour) and no
# ``on*`` handlers (nh3 strips event handlers regardless). NB: do NOT allow
# ``rel`` on <a> here — we set ``link_rel`` below and ammonia panics if both are
# configured ("it makes no sense to let the user set rel while forcing a value").
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "*": {"class"},
}

# URL schemes permitted on href/src. Notably excludes ``javascript:``.
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto", "tel"}


def sanitize_html(value):
    """Return ``value`` with unsafe HTML removed, or the value unchanged when
    it is not a non-empty string.
    """
    if not value or not isinstance(value, str):
        return value
    return nh3.clean(
        value,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
    )
