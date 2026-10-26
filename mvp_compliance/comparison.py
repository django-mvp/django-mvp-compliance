"""Two published versions of one document, compared word by word (FS-014)."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _

from mvp_compliance.models import Version

#: A tag, a run of whitespace, or a word with the punctuation stuck to it.
TOKEN = re.compile(r"<[^>]+>|\s+|[^\s<]+")
VOID = {"br", "hr", "img", "input", "wbr"}


def key(token: str) -> str:
    """What a token is compared as: any whitespace counts as one space."""
    return " " if token.isspace() else token


def blocks(html: str) -> list[list[str]]:
    """Split stored HTML into its top-level elements, each a list of tokens.

    Whitespace between elements is dropped, so a change of line breaks between
    paragraphs is never a difference.
    """
    out: list[list[str]] = []
    current: list[str] = []
    depth = 0
    for token in TOKEN.findall(html):
        if depth == 0 and token.isspace() and not current:
            continue
        current.append(token)
        if token.startswith("</"):
            depth -= 1
        elif token.startswith("<") and not token.endswith("/>"):
            name = token[1:].split()[0].rstrip(">").lower()
            if name not in VOID:
                depth += 1
        if depth <= 0 and not token.isspace():
            out.append(current)
            current, depth = [], 0
    if current:
        out.append(current)
    return [part for block in out for part in open_lists(block)]


def open_lists(block: list[str]) -> list[list[str]]:
    """A list is compared item by item: its tags and each item become blocks."""
    first = block[0].lower()
    if not (first.startswith("<ul") or first.startswith("<ol")) or len(block) < 2:
        return [block]
    return [[block[0]], *blocks("".join(block[1:-1])), [block[-1]]]


def similar(old: list[str], new: list[str]) -> float:
    """How alike two blocks read, from 0 to 1, by their words."""
    a = [t for t in old if not t.isspace()]
    b = [t for t in new if not t.isspace()]
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


@dataclass(frozen=True)
class Comparison:
    """The older and the newer of two versions, and the marked-up text between them.

    Built from the HTML each version stored at publication (Article XII), in
    two passes: the top-level elements are matched first, then the words of
    the elements that differ. Unchanged elements and added ones are the newer
    version's own markup; a removed element keeps its own markup, its words
    marked. Nothing is added beyond the marks.
    """

    older: Version
    newer: Version

    @classmethod
    def of(cls, first: Version, second: Version) -> "Comparison":
        """Order the two by publication, whichever way round they were given."""
        if first.published_at <= second.published_at:
            return cls(older=first, newer=second)
        return cls(older=second, newer=first)

    @property
    def same(self) -> bool:
        """Whether the two read the same, ignoring whitespace."""
        return self.signature(self.older.html) == self.signature(self.newer.html)

    @staticmethod
    def signature(html: str) -> list[str]:
        return ["".join(key(t) for t in block) for block in blocks(html)]

    def html(self) -> SafeString:
        """The newer version's text with additions and removals marked."""
        old, new = blocks(self.older.html), blocks(self.newer.html)
        matcher = SequenceMatcher(
            None, self.signature(self.older.html), self.signature(self.newer.html),
            autojunk=False,
        )
        out: list[str] = []
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                for block in new[j1:j2]:
                    out.extend(block)
                    out.append("\n")
            elif op == "delete":
                for block in old[i1:i2]:
                    out.extend(self.mark_run("del", block))
                    out.append("\n")
            elif op == "insert":
                for block in new[j1:j2]:
                    out.extend(self.mark_run("ins", block))
                    out.append("\n")
            else:
                out.extend(self.pair(old[i1:i2], new[j1:j2]))
        return mark_safe("".join(out))  # noqa: S308 — built only from stored, sanitised HTML

    def pair(self, old: list[list[str]], new: list[list[str]]) -> list[str]:
        """Match the changed blocks of one range to each other, in order.

        A block that reads mostly like one on the other side is compared word
        by word with it. One that matches nothing is removed or added whole,
        keeping its own markup.
        """
        out: list[str] = []
        i = 0
        for block in new:
            match = next(
                (k for k in range(i, len(old)) if similar(old[k], block) >= 0.5), None
            )
            if match is None:
                out.extend(self.mark_run("ins", block))
            else:
                for removed in old[i:match]:
                    out.extend(self.mark_run("del", removed))
                    out.append("\n")
                out.extend(self.words(old[match], block))
                i = match + 1
            out.append("\n")
        for removed in old[i:]:
            out.extend(self.mark_run("del", removed))
            out.append("\n")
        return out

    def words(self, old: list[str], new: list[str]) -> list[str]:
        """Mark the words that differ between two runs of elements."""
        matcher = SequenceMatcher(
            lambda t: t == " ", [key(t) for t in old], [key(t) for t in new],
            autojunk=False,
        )
        out: list[str] = []
        for op, i1, i2, j1, j2 in self.merged(matcher.get_opcodes(), new):
            if op == "equal":
                out.extend(new[j1:j2])
                continue
            if op in ("delete", "replace"):
                # The newer version's markup is kept, so removed words sit
                # inside it and their own tags are dropped.
                removed = "".join(t for t in old[i1:i2] if not t.startswith("<"))
                if removed.strip():
                    out.append(self.mark("del", removed))
            if op in ("insert", "replace"):
                out.extend(self.mark_run("ins", new[j1:j2]))
        return out

    @staticmethod
    def merged(opcodes, new: list[str]):
        """Fold a space left unchanged between two changes into them, so a
        rewritten phrase reads as one removal and one addition, not word by word."""
        merged: list[list] = []
        for op, i1, i2, j1, j2 in opcodes:
            only_space = op == "equal" and not "".join(new[j1:j2]).strip()
            if merged and merged[-1][0] != "equal" and (only_space or op != "equal"):
                merged[-1] = ["replace", merged[-1][1], i2, merged[-1][3], j2]
            else:
                merged.append([op, i1, i2, j1, j2])
        return merged

    def mark_run(self, tag: str, tokens: list[str]) -> list[str]:
        """Mark the words of a run, leaving its tags outside the marks."""
        out: list[str] = []
        words: list[str] = []

        def flush():
            text = "".join(words)
            out.append(self.mark(tag, text) if text.strip() else text)
            words.clear()

        for token in tokens:
            if token.startswith("<"):
                flush()
                out.append(token)
            else:
                words.append(token)
        flush()
        return out

    @staticmethod
    def mark(tag: str, text: str) -> str:
        """One marked run, with words a screen reader announces at its start."""
        label = _("Added:") if tag == "ins" else _("Removed:")
        return f'<{tag}><span class="sr-only">{escape(label)} </span>{text}</{tag}>'
