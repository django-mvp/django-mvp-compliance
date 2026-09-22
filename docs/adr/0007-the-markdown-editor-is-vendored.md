# ADR 0007 — The Markdown editor is vendored, not depended on or fetched

**Status:** accepted

## Decision

The editor that gives a version's `markdown` field its formatting controls is
[EasyMDE](https://github.com/Ionaru/easy-markdown-editor). Its two distributed files are committed
to this repository under `mvp_compliance/static/mvp_compliance/vendor/easymde/`, byte-identical to
what its project published, beside that project's licence and a `VERSION.md` recording the version,
the source URL and the SHA-256 of each file.

There is no Python dependency wrapping it, and nothing is fetched from a content delivery network
when a page loads. The files are excluded from the whitespace hooks, which otherwise rewrite them
and make the recorded hashes wrong.

The toolbar itself is not the library's default. `MarkdownEditorWidget.TOOLBAR` declares every
control that exists, and the icons are drawn from inline SVG in this package's own stylesheet.

## Why

An editor that renders formatting inline is a requirement rather than a preference. The
specification this surface was built from compares "the editor's own inline formatting display"
with the server-rendered preview and rules that they are two different things — a comparison that
needs an editor that has such a display. A toolbar written over a plain textarea inserts characters
and shows characters, and there would be nothing on one side of it.

Among the controls that qualify, EasyMDE takes its toolbar as an explicit list, so the controls
this package forbids do not exist rather than being hidden, and it writes ordinary Markdown back to
the textarea, so an author who prefers to type it is not obstructed.

Vendoring rather than linking follows from the constitution's rule that nothing this package holds
is transmitted off the host project's own infrastructure. A third-party asset tag reverses that for
every page load and hands somebody else the ability to change what runs inside an authenticated
admin session on every site that installs this. An account that can publish a policy is a
high-value target, which is the same reasoning that puts a sanitiser between authored Markdown and
stored HTML.

A Python package wrapping the same files was the other option. It would add a dependency, a release
cadence and a second opinion about which controls to offer, in exchange for two files this package
would still have to configure. `django-markdownx`, which a sibling project runs, was rejected on
the requirements rather than on taste: it ships no formatting toolbar at all, and it does ship
drag-and-drop image upload, which this surface forbids.

The cost is 340 KB of minified JavaScript in the repository and a refresh that is a manual step.
The icons are ours because the library ships none and expects an icon font this package has no
other use for — a whole font for seven buttons is a poor trade, and declaring the buttons here is
what makes the restriction checkable against the markup a request receives.

## Revisit if

The library stops being maintained, or a later feature needs an editing control this toolbar cannot
express — a comparison view of two versions, say, or structured clauses rather than prose. Either
reopens which editor, not whether to vendor it: the argument against fetching it does not depend on
which one it is.
