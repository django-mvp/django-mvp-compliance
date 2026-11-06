"""What the demo does when a version is published: it emails the people who use the site.

This is the receiver docs/announcing.md describes, run for real so the email can be read in a
mail catcher such as Mailpit.
"""

from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver

from mvp_compliance.emails import render_new_version_email
from mvp_compliance.models import Version
from mvp_compliance.signals import version_published


def recipients_for(version):
    """The addresses of everyone who agreed to an earlier version of the document."""
    return list(
        get_user_model()
        .objects.filter(compliance_acceptances__version__document=version.document)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )


@receiver(version_published, sender=Version)
def tell_the_users(sender, version, replaced, **kwargs):
    """Send the new-version email to everyone who agreed to the document before."""
    recipients = recipients_for(version)
    if not recipients:
        return
    subject, text, html = render_new_version_email(version, replaced)
    message = EmailMultiAlternatives(subject, text, None, bcc=recipients)
    message.attach_alternative(html, "text/html")
    message.send()
