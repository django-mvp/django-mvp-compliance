# Research: Documents and their versions readable as pages of the site

The questions the design rests on, each answered from the code on main or from the packages as the
project resolves them (Django 6.1.1 and django-mvp 0.24.0 in the development virtualenv), never from
recollection.

---

## R1 — What does a page need to render inside the django-mvp shell?

**Question.** FR-012: every page renders in the shell with no template written by the project.

**Finding.** mvp's views resolve the view's own template first and fall back to a packaged one
(`mvp/views/base.py`, `BaseTemplateNameMixin`). `page_view.html` extends `base.html` and exposes
`page.header`, `page.title`, `page.actions`, `page.content` and `page.footer` blocks.
`detail_view.html` extends it and fills `page.actions` from the view's `directory`. A package template
that extends `page_view.html` and fills `page.content` therefore gets the whole shell.

Rendering the shell also needs the host project's `FLEX_MENUS` renderers. Without them, rendering
any MVP view in the demo raises `ValueError: Renderer 'sidebar' not found in FLEX_MENUS['renderers']`
(probed on this branch's base, 2026-09-26). That is host-project configuration and mvp's documented
install step, so it belongs in the demo and test settings, not the package.

**Consequence.** Templates extend `page_view.html`, fill `page.content` only, and the detail views
set `directory = []` so no edit or delete link is drawn. `demo/settings.py` and `tests/settings.py`
gain `FLEX_MENUS`.

---

## R2 — Does the prebuilt stylesheet style rendered Markdown?

**Question.** A version's HTML is plain headings, paragraphs, lists and tables. It needs readable
styling without the project writing CSS.

**Finding.** mvp ships the Tailwind typography plugin. `prose` and `not-prose` are present;
`prose-lg` and `prose-invert` are not (mvp `docs/utility-classes.md`, *Typography*). `max-w-prose`
also ships.

**Consequence.** The wording is wrapped in `prose`. No size or colour modifiers.

---

## R3 — Can the slug be prepopulated on create and read-only once fixed?

**Question.** FR-016 wants a suggestion from the name. FR-017 wants the field fixed after the first
publication.

**Finding.** `django.contrib.admin.helpers.AdminForm.__init__` builds its prepopulated list with
`form[field_name]` for every entry in `prepopulated_fields`. A read-only field is not on the form,
so leaving `slug` in `prepopulated_fields` while it is read-only raises `KeyError`.

**Consequence.** `get_prepopulated_fields()` returns `{}` whenever `get_readonly_fields()` adds
`slug`.

---

## R4 — How are the dates a version was in force derived?

**Question.** FR-003 and FR-010 need "in force from" and "replaced on" for each version.

**Finding.** `published_at` is set once, at publication, and never changes (Article XII). Versions of
a document are published one at a time under a lock in `publish()`, so publication order is
`published_at` order. The version that replaced another is the next one published.

**Consequence.** "In force from" is `published_at`. "Replaced on" is the `published_at` of the next
published version of the same document, annotated in one `Subquery`. Nothing new is stored.
