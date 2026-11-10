# Decisions — 016 Reading a document in your own language

## D1 — The recorded notice is kept as text

The maintainer ruled at the spec review that recording the language alone says nothing about
whether a person was directed to the original. An acceptance given on a translated page keeps the
full text of the notice it was shown. The notice comes from a translation catalogue, which can
change after the fact, so a key or a template name would not do (FR-010, FR-011).

## D2 — The staff page and the person's copy show it

The interpretation first left FS-004 and FS-012 unchanged. A record that no page can produce is no
evidence of anything, and G2 requires it to be producible, so both show the language, the wording
live when the acceptance was given and the recorded notice (FR-015).

## D3 — A translation that changes under the page is a change on the page

The agreement page already redraws as changed when a version is replaced between drawing and
submitting. A translation corrected, put live or withdrawn in that window is handled the same way,
so an acceptance never stands for wording the person was not shown (FR-013).

## D4 — Regional variants fall back to the general language

A reader in `de-at` with only a `de` translation is served it, as Django's own language fallback
does (US-1 scenario 6).
