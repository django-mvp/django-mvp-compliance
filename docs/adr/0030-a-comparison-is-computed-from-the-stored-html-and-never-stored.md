# ADR 0030 — A comparison is computed from the stored HTML and never stored

**Status:** accepted

## Decision

A comparison of two published versions of one document (`mvp_compliance.comparison.Comparison`) is
computed from the HTML each version stored at publication, on each request, with the standard
library's `difflib`. It is never stored, and it is never computed from the Markdown. Only published
versions of the same document are compared. Drafts never are.

The result keeps the newer version's markup and adds only `<ins>` and `<del>` marks, each starting
with a hidden, escaped label. Changes are marked word by word, with a removed paragraph or list item
marked whole. Each newer element is matched only against the next few unmatched older ones
(`Comparison.window`), which keeps the cost proportional to the length of the text.

## Why

The stored HTML is what a reader was served and what an acceptance points at, and Article XII
forbids rendering Markdown at request time. Comparing the Markdown and rendering the result would
show a text that no reader was ever served. Both versions are immutable, so the same two always
give the same comparison and there is nothing to keep in step by storing it. A comparison is also
not evidence of anything, unlike a version or an acceptance.

The standard library covers the job, so no dependency was added (Article VII). The matching window
exists because an unbounded match of two long texts that share nothing took several seconds.

## Revisit if

A comparison has to cover a draft (a compliance editor comparing a version being written with the
one in force), or documents in more than one language need comparing across translations. Either
would bring in a text that is not a stored, published version.
