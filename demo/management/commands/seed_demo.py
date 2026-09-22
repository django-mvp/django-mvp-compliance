"""Fill the demo database with accounts and documents in every state.

Idempotent: run it as often as you like. It exists so that the authoring
surface can be used rather than read about — every state the admin can put a
version in is reachable without anybody creating a row by hand.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from mvp_compliance.models import Document, Version

PASSWORD = "password"

DOCUMENT_WORK = [
    "view_document",
    "add_document",
    "change_document",
    "delete_document",
    "view_version",
    "add_version",
    "change_version",
    "delete_version",
]

#: email -> (is_staff, is_superuser, permission codenames on this package)
ACCOUNTS = {
    "regular.user@example.com": (False, False, []),
    "staff.user@example.com": (True, False, []),
    "super.user@example.com": (True, True, []),
    "editor.user@example.com": (True, False, DOCUMENT_WORK),
    "publisher.user@example.com": (True, False, [*DOCUMENT_WORK, "publish_version"]),
}

PRIVACY = """\
## What we collect

We collect the address you sign in with, and nothing else you have not given us
deliberately.

## Who reads it

Nobody outside this site. We do not sell it, and we do not pass it to anyone who
would.

## Asking us to stop

Write to us and we will remove what we hold. There is no form to fill in.
"""

PRIVACY_NEXT = """\
## What we collect

We collect the address you sign in with, the pages you visit while signed in,
and nothing else you have not given us deliberately.

## Who reads it

Nobody outside this site. We do not sell it, and we do not pass it to anyone who
would.

## How long we keep it

Until you ask us to stop, and for a year afterwards so we can show you what we
held.

## Asking us to stop

Write to us and we will remove what we hold. There is no form to fill in.
"""

TERMS = """\
## Using this site

Use it for what it is for. Do not try to break it, and do not use it to reach
somebody else's account.

## What we promise

The site will be here, and it will do what it says. We do not promise it will
never be down.

## Ending it

You can close your account whenever you like. We can close it too, if you do
something on the list above.
"""

COOKIES = """\
## What a cookie does here

One cookie keeps you signed in. Another remembers what you chose the last time
you were asked about cookies.

## The ones you can turn off

Anything that measures how the site is used. Turning them off costs you nothing.
"""


class Command(BaseCommand):
    help = "Seed the demo with the standard accounts and a document in every state."

    def handle(self, *args, **options):
        for email, (is_staff, is_superuser, codenames) in ACCOUNTS.items():
            self.make_account(email, is_staff, is_superuser, codenames)

        self.make_document(
            "Privacy policy",
            drafts=[],
            published=[PRIVACY, PRIVACY_NEXT],
            note="two published versions: one in force, one superseded",
        )
        self.make_document(
            "Terms of use",
            drafts=[],
            published=[TERMS],
            note="one version, in force",
        )
        self.make_document(
            "Cookie policy",
            drafts=[COOKIES],
            published=[],
            note="a draft and nothing published — invisible to a visitor",
        )
        self.make_document(
            "Acceptable use",
            drafts=[],
            published=[],
            note="no versions at all",
        )

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))

    def make_account(self, email, is_staff, is_superuser, codenames):
        """Create or update one account, and set its permissions."""
        model = get_user_model()
        username = email.split("@")[0]
        user, created = model.objects.get_or_create(
            username=username, defaults={"email": email}
        )
        user.email = email
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(PASSWORD)
        user.save()
        user.user_permissions.set(
            Permission.objects.filter(
                content_type__app_label="mvp_compliance", codename__in=codenames
            )
        )
        self.stdout.write(f"  {'created' if created else 'updated'} {email}")

    def make_document(self, name, drafts, published, note):
        """Create a document and its versions, once.

        A document that already has versions is left alone. Publishing is
        one-way, so re-seeding one cannot be made idempotent by rewriting it.
        """
        document, created = Document.objects.get_or_create(name=name)
        if not created and document.versions.exists():
            self.stdout.write(f"  {name}: already seeded")
            return

        for markdown in published:
            version = Version.objects.create(document=document, markdown=markdown)
            version.publish()
        for markdown in drafts:
            Version.objects.create(document=document, markdown=markdown)

        self.stdout.write(f"  {name}: {note}")
