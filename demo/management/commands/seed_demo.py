"""Fill the demo database with accounts and documents in every state.

Idempotent: run it as often as you like. It exists so that the authoring
surface can be used rather than read about — every state the admin can put a
version in is reachable without anybody creating a row by hand.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.http import HttpRequest

from mvp_compliance.models import Acceptance, Document, Version

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
    # Holds the produce permission and nothing else, which is the point of it
    # being separate: fielding a request is a different job from writing a
    # document, and staff.user above holds neither.
    "disclosure.user@example.com": (True, False, ["produce_disclosure"]),
}

#: A name long enough to wrap, on a document with many versions.
COMMUNITY = (
    "Community guidelines for members, guests and organisations posting for them"
)

#: The people the demo holds acceptances for, so every state a page can be in
#: is reachable. Each line is a document, the number of the version accepted
#: and the day it was accepted. regular.user holds none at all.
ACCEPTORS = {
    # Everything accepted is in force, with an earlier version under one.
    "acceptor.user@example.com": [
        ("Privacy policy", "2025.1", (2025, 3, 12)),
        ("Terms of use", "2025.1", (2025, 3, 12)),
        ("Privacy policy", "2026.1", (2026, 6, 5)),
    ],
    # One document, one version.
    "newcomer.user@example.com": [
        ("Terms of use", "2025.1", (2026, 9, 22)),
    ],
    # Accepted the privacy policy before it was reworded and nothing since.
    "returning.user@example.com": [
        ("Privacy policy", "2025.1", (2025, 4, 2)),
        ("Terms of use", "2025.1", (2025, 4, 2)),
    ],
    # A long history: many versions of one document with one never accepted
    # and the newest not accepted yet, and a document that was made a notice
    # after it was accepted.
    "longstanding.user@example.com": [
        (COMMUNITY, "2024.1", (2024, 2, 6)),
        (COMMUNITY, "2024.2", (2024, 11, 20)),
        (COMMUNITY, "2026.1", (2026, 2, 10)),
        ("Privacy policy", "2025.1", (2025, 3, 11)),
        ("Privacy policy", "2026.1", (2026, 6, 3)),
        ("Terms of use", "2025.1", (2025, 3, 11)),
        ("House rules", "2025.1", (2025, 9, 3)),
        ("Delivery information", "2025.1", (2025, 3, 11)),
    ],
}

#: Someone whose account is closed and whose records outlived it, which is the
#: ordinary case for a request and the one that cannot be asked for by an
#: email address, because there is no account left to carry one.
DEPARTED = "departed.user@example.com"

#: Someone who published a version and whose account was removed afterwards,
#: so a version that says its publisher's account is gone is reachable.
DEPARTED_PUBLISHER = "departed-publisher.user@example.com"

#: document name -> the slug its address is made from
SLUGS = {
    "Privacy policy": "privacy-policy",
    "Terms of use": "terms-of-use",
    "Cookie policy": "cookie-policy",
    "Acceptable use": "acceptable-use",
    "House rules": "house-rules",
    "Impressum": "impressum",
    COMMUNITY: "community-guidelines",
    "Delivery information": "delivery-information",
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


HOUSE_RULES = """\
## Be decent

Treat the people here the way you would want to be treated.

## Stay on topic

Keep each thread to what it started about.
"""

IMPRESSUM = """\
## Publisher

Example Site GmbH, Musterstrasse 1, 10115 Berlin.

## Contact

Write to hello@example.com.
"""


COMMUNITY_WORDING = """\
## Who this covers

Members, guests, and anyone posting for an organisation.

## What we ask

Be accurate, be civil, and say who you are posting for.

## Revision {revision}

This is the wording as revised for the {revision} time.
"""

DELIVERY = """\
## Where we deliver

Anywhere in Germany, within three working days.
"""


@contextmanager
def on(year, month, day):
    """Run what is inside as though it were that day.

    Publishing and accepting both stamp the present moment and neither can be
    rewritten afterwards, so a history spread over years has to be made on
    the days it happened.
    """
    moment = datetime(year, month, day, 10, 0, tzinfo=UTC)
    with mock.patch("django.utils.timezone.now", return_value=moment):
        yield


class Command(BaseCommand):
    help = "Seed the demo with the standard accounts and a document in every state."

    def handle(self, *args, **options):
        for email, (is_staff, is_superuser, codenames) in ACCOUNTS.items():
            self.make_account(email, is_staff, is_superuser, codenames)

        publisher = get_user_model().objects.get(username="publisher.user")
        self.make_document(
            "Privacy policy",
            drafts=[],
            published=[(PRIVACY, (2025, 3, 10)), (PRIVACY_NEXT, (2026, 6, 2))],
            note="two published versions: one in force, one superseded",
            publisher=publisher,
        )
        self.make_document(
            "Terms of use",
            drafts=[],
            published=[(TERMS, (2025, 3, 10))],
            note="one version, in force, published from code with nobody named",
        )
        self.make_departed_publisher_document()
        self.make_document(
            "Impressum",
            drafts=[],
            published=[(IMPRESSUM, (2025, 3, 10))],
            note="a notice, one version in force: read, never agreed to",
            kind=Document.Kind.NOTICE,
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

        self.make_document(
            COMMUNITY,
            drafts=[],
            published=[
                (COMMUNITY_WORDING.format(revision=revision), day)
                for revision, day in [
                    ("first", (2024, 2, 5)),
                    ("second", (2024, 11, 18)),
                    ("third", (2025, 7, 1)),
                    ("fourth", (2026, 2, 9)),
                    ("fifth", (2026, 9, 14)),
                ]
            ],
            note="five published versions over three years, and a long name",
        )
        self.make_document(
            "Delivery information",
            drafts=[],
            published=[(DELIVERY, (2025, 3, 10))],
            note="agreed to once, and made a notice afterwards",
        )

        self.make_acceptances()
        # After the acceptances: one of a notice is refused, so it has to be
        # recorded while the document is still one people agree to.
        Document.objects.filter(name="Delivery information").update(
            kind=Document.Kind.NOTICE
        )

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))

    def make_departed_publisher_document(self):
        """A version whose publisher's account has since been removed."""
        if Document.objects.filter(name="House rules").exists():
            self.stdout.write("  House rules: already seeded")
            return
        departed = self.make_account(DEPARTED_PUBLISHER, True, False, [])
        self.make_document(
            "House rules",
            drafts=[],
            published=[(HOUSE_RULES, (2025, 9, 1))],
            note="published by an account since removed",
            publisher=departed,
        )
        departed.delete()

    def make_acceptances(self):
        """Record the acceptances the disclosure page is there to produce.

        Guarded on there being none at all rather than on each record: an
        acceptance cannot be edited or deleted once written, so re-seeding one
        is not something this can undo.
        """
        if Acceptance.objects.exists():
            self.stdout.write("  acceptances: already seeded")
            return

        for email, accepted in ACCEPTORS.items():
            person = self.make_account(email, False, False, [])
            for name, number, day in accepted:
                version = Version.objects.get(document__name=name, number=number)
                with on(*day):
                    Acceptance.objects.record(person, version, request=self.request())
            self.stdout.write(f"  {email}: {len(accepted)} acceptances")

        departed = self.make_account(DEPARTED, False, False, [])
        privacy = Document.objects.get(name="Privacy policy")
        subject = Acceptance.subject_of(departed)
        for version in privacy.versions.published():
            Acceptance.objects.record(departed, version)
        departed.delete()
        self.stdout.write(
            f"  {DEPARTED}: account removed, records kept — ask for subject {subject}"
        )

    def request(self):
        """A request carrying an address, so the optional evidence is reachable.

        The demo turns ``MVP_COMPLIANCE_RECORD_IP_ADDRESS`` on, so a record
        made from a request holds the address it came from and the page has
        that state to show. The package's own default is off.
        """
        request = HttpRequest()
        request.META["REMOTE_ADDR"] = "198.51.100.24"
        return request

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
        return user

    def make_document(
        self,
        name,
        drafts,
        published,
        note,
        publisher=None,
        kind=Document.Kind.AGREED,
    ):
        """Create a document and its versions, once.

        A document that already has versions is left alone. Publishing is
        one-way, so re-seeding one cannot be made idempotent by rewriting it.
        """
        document, created = Document.objects.get_or_create(
            name=name, defaults={"slug": SLUGS[name], "kind": kind}
        )
        if not created and document.versions.exists():
            self.stdout.write(f"  {name}: already seeded")
            return

        for markdown, day in published:
            version = Version.objects.create(document=document, markdown=markdown)
            with on(*day):
                version.publish(publisher=publisher)
        for markdown in drafts:
            Version.objects.create(document=document, markdown=markdown)

        self.stdout.write(f"  {name}: {note}")
