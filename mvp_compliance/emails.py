"""The ready-made announcement for the people running the site.

Renders text and returns it. Sending it, and choosing who receives it, is the
host project's.
"""

from django.template.loader import render_to_string
from django.urls import reverse

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
