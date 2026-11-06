"""The ready-made emails announcing a publication: one for the people running
the site, one for the people who use it.

Each is rendered and returned. Sending it, and choosing who receives it, is the
host project's.
"""

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import urlencode

SUBJECT_TEMPLATE = "mvp_compliance/email/version_published_subject.txt"
BODY_TEMPLATE = "mvp_compliance/email/version_published_body.txt"


def render_publication_email(version, replaced, site_url) -> tuple[str, str]:
    """Render the announcement for the people running the site. Sends nothing.

    Args:
        version: The version now in force, as ``version_published`` sends it.
            The publisher is read from it.
        replaced: The version it superseded, or ``None`` for a document's first.
        site_url: The address the site is served at, such as
            ``"https://example.com"``, joined to the version's admin page.

    Returns:
        ``(subject, body)``. The subject is always one line. Both are plain
        text and are not escaped, so send the body as plain text, never as HTML.
    """
    context = {
        "version": version,
        "replaced": replaced,
        "admin_url": site_url.rstrip("/")
        + reverse("admin:mvp_compliance_version_change", args=[version.pk]),
    }
    subject = render_to_string(SUBJECT_TEMPLATE, context)
    body = render_to_string(BODY_TEMPLATE, context)
    return " ".join(subject.split()), body


NEW_VERSION_SUBJECT_TEMPLATE = "mvp_compliance/email/new_version_subject.txt"
NEW_VERSION_TEXT_TEMPLATE = "mvp_compliance/email/new_version_message.txt"
NEW_VERSION_HTML_TEMPLATE = "mvp_compliance/email/new_version_message.html"


def render_new_version_email(version, replaced, request=None) -> tuple[str, str, str]:
    """Render the email telling the site's users about a new version. Sends nothing.

    The HTML body extends django-mvp's email layout, so it carries the site's
    name, logo and colours. Its links are full addresses, taken from
    ``request`` when one is given and otherwise from the current ``Site``.

    Args:
        version: The version now in force, as ``version_published`` sends it.
        replaced: The version it superseded, or ``None`` for a document's first.
        request: The request the email is rendered for, or ``None``. Without
            one, ``django.contrib.sites`` must be installed and ``SITE_ID`` set.

    Returns:
        ``(subject, text, html)``. The subject is always one line. ``text`` is
        plain text and not escaped, so send it as the plain-text part and
        ``html`` as the HTML alternative.
    """
    document_path = reverse("mvp_compliance:document", args=[version.document.slug])
    comparison_path = None
    if replaced is not None:
        comparison_path = (
            reverse("mvp_compliance:comparison", args=[version.document.slug])
            + "?"
            + urlencode({"from": replaced.number, "to": version.number})
        )
    context = {
        "version": version,
        "replaced": replaced,
        "document_path": document_path,
        "comparison_path": comparison_path,
    }
    subject = render_to_string(NEW_VERSION_SUBJECT_TEMPLATE, context, request)
    text = render_to_string(NEW_VERSION_TEXT_TEMPLATE, context, request)
    html = render_to_string(NEW_VERSION_HTML_TEMPLATE, context, request)
    return " ".join(subject.split()), text, html
