# ADR 0018 — A version is numbered when it is published, by year

**Status:** accepted

## Decision

A draft has no number. `Version.publish()` gives a version its number, inside the same locked block
that puts it in force: the year of publication in the site's time zone, a dot, and its place among
the document's versions published that year. A document's first three publications in 2026 are
`2026.1`, `2026.2` and `2026.3`, and its first in 2027 is `2027.1`.

The number is frozen with the wording, like everything else a published version carries. It is the
only numbering scheme, and there is no setting to choose another.

## Why

A version number is how somebody refers to a wording that was in force. Numbering drafts when they
were created meant every draft took a number whether or not it was ever published, so the published
history read 1, then 4, and a person who accepted version 4 had no way to know there was never a 2
or a 3 in force.

A plain counter says nothing about how old a wording is. A legal document is reworded every year or
two, so the year tells a reader at a glance whether the text in front of them is recent. The site's
time zone decides the year, because a version published just after midnight on New Year's Day is
dated that year where the site's readers are, whatever UTC says.

The count happens under the lock `publish()` already holds on the document, so two publications
racing each other cannot take the same place in the year. The unique constraint on document and
number is the backstop. A draft's number is null rather than empty so that constraint covers
published numbers alone on every database backend without a partial index.

Offering a choice of scheme was left out: no project has asked for another one, and a setting
nobody uses is still a setting everyone has to read about.

## Revisit if

A project needs a numbering scheme other than the year.
