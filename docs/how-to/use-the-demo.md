# How to use the demo

The repository holds a demonstration project, `demo/`, for looking at the package in a browser
while it is being built. Its pages are this documentation, and every state the package can be
in is seeded, with an account to sign in as for each one.

## Running it

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py build_docs
uv run python manage.py runserver 0.0.0.0:8021
```

`seed_demo` rebuilds the documents, their versions and the accounts, and can be run again at any
time to start over. `build_docs` builds these pages. Run it again after editing a page under
`docs/`, then reload.

## Accounts

The password for every account is `password`.

| Sign in as | Can do |
|---|---|
| `editor.user@example.com` | Write, preview and discard versions. Cannot publish. |
| `publisher.user@example.com` | Everything the editor can, and publish. |
| `super.user@example.com` | Everything, including the rest of the admin. |
| `staff.user@example.com` | Reach the admin and nothing in this package. |
| `regular.user@example.com` | Not staff. Cannot reach the admin at all. Has agreed to nothing. |
| `veteran.user@example.com` | On the site since it opened: 49 acceptances, forty of them of one document. |
| `acceptor.user@example.com` | Agreed to the privacy policy twice and the terms once. All of it is in force. |
| `newcomer.user@example.com` | Agreed to one version of one document. |
| `returning.user@example.com` | Agreed to the privacy policy before it was reworded, and not since. |
| `longstanding.user@example.com` | A long history across four documents, and one more that has since become a notice. |
| `monitoring.user@example.com` | Has agreed to nothing and is never stopped, because the demo's settings name it. Agreeing to a document records one like anybody else. |
| `support.user@example.com` | Has agreed to nothing and is never stopped, because its group holds the permission to continue without accepting. Remove the permission from the group in the admin and its next request is stopped. |

## Documents

The documents and their versions are written in the admin, under **Compliance**, at `/admin/`.
A visitor reads the version in force at `/legal/<slug>/`, and a document with nothing published
is not found. The demo's settings declare four documents its pages link to: the privacy policy,
the terms of use, the impressum and the accessibility statement. The accessibility statement has
no version yet, so its page is not found until one is published.

| Document | What it holds |
|---|---|
| Privacy policy | Two published versions, one in force and one superseded. |
| Terms of use | One version, in force. |
| Impressum | A notice with one version in force. People read it and are never asked to agree to it. |
| Community guidelines | Five published versions over three years, under a long name. |
| Membership terms | Forty published versions since 2013. |
| Delivery information | Agreed to once, then made a notice. |
| Cookie policy | A draft and nothing published. |
| Acceptable use | No versions at all. |

## Being asked to agree

A signed-in person with something required outstanding is sent from any page to a list of it and
asked to agree, then sent on to where they were going. Open `/legal/agree/` directly to see the
page with no address to return to, which shows it even when only optional documents are
outstanding. Which state you see depends on who you sign in as.

| Sign in as | What you see |
|---|---|
| `one-document.user@example.com` | One required document, agreed to before, with the summary of what changed since. |
| `behind.user@example.com` | One required document, four versions behind, with the summaries of the three since that have one, newest first. |
| `longstanding.user@example.com` | Two required documents, one with a long name. |
| `regular.user@example.com` | Five documents, four required and one optional. |
| `unrecorded.user@example.com` | Two required documents, and the record is never written. |
| `optional.user@example.com` | One document that holds you up and one that is optional. Agree to only the first and you are sent on. |
| `optional-only.user@example.com` | Only an optional document, so the page offers it and lets you continue. |
| `veteran.user@example.com` | Nothing outstanding, so you are sent straight on. |

## A person's own pages

Signed in, a person finds the account area in the user menu. It holds three of the package's
pages:

- **Agreements**, the list of what they have agreed to.
- **Your data**, where they download a copy of what the demo holds about them. The demo declares
  a profile and the files a person uploaded, so the copy has something in it.
- **Delete account**, where they delete their account and everything the demo holds about them.
  Run `seed_demo` again afterwards to bring the account back.

Your data and Delete account ask for the password again before they show anything.
