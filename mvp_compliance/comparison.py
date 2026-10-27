"""Two published versions of one document, compared word by word (FS-014)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import ClassVar, cast

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _

from mvp_compliance.models import Version


@dataclass(frozen=True)
class Comparison:
    """The older and the newer of two versions, and the marked-up text between them.

    Built from the HTML each version stored at publication (Article XII), in
    two passes: the top-level elements are matched first, then the words of
    the elements that differ. Unchanged elements and added ones are the newer
    version's own markup; a removed element keeps its own markup, its words
    marked. Nothing is added beyond the marks.

    Attributes:
        older: The version published first.
        newer: The version published last.
        similarity: How alike two elements must be, from 0 to 1, to be
            compared word by word.
        window: How many unpaired older elements a newer one is tried against,
            which bounds the pairing pass at elements times this number.
    """

    older: Version
    newer: Version

    similarity: ClassVar[float] = 0.5
    window: ClassVar[int] = 8

    #: A tag, a run of whitespace, or a word with its punctuation. A tag is
    #: matched quote-aware, so a ``>`` inside an attribute value never ends it.
    TOKEN: ClassVar[re.Pattern[str]] = re.compile(
        r"<(?:[^>\"']|\"[^\"]*\"|'[^']*')*>|\s+|[^\s<]+|<"
    )
    NAME: ClassVar[re.Pattern[str]] = re.compile(r"</?([a-zA-Z][a-zA-Z0-9-]*)")
    VOID: ClassVar[frozenset[str]] = frozenset({"br", "hr", "img", "input", "wbr"})
    LISTS: ClassVar[frozenset[str]] = frozenset({"ul", "ol"})

    @classmethod
    def of(cls, first: Version, second: Version) -> "Comparison":
        """Order two versions by publication, whichever way round they were given.

        Args:
            first: One published version.
            second: The other published version of the same document.

        Returns:
            The comparison of the older with the newer.
        """
        if cast(datetime, first.published_at) <= cast(datetime, second.published_at):
            return cls(older=first, newer=second)
        return cls(older=second, newer=first)

    @property
    def same(self) -> bool:
        """Whether the two read the same: equal words, tags and whitespace ignored."""
        return self.reading(self.older.html) == self.reading(self.newer.html)

    def html(self) -> SafeString:
        """Mark what the newer version added and what it removed from the older.

        Returns:
            The newer version's text with ``<ins>`` and ``<del>`` around the
            words that differ, each starting with a hidden label.
        """
        old, new = self.blocks(self.older.html), self.blocks(self.newer.html)
        matcher = SequenceMatcher(
            None, self.signature(old), self.signature(new), autojunk=False
        )
        out: list[str] = []
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                out.extend(self.copied(new[j1:j2]))
            elif op == "delete":
                out.extend(self.removed(old[i1:i2]))
            elif op == "insert":
                out.extend(self.added(new[j1:j2]))
            else:
                out.extend(self.pair(old[i1:i2], new[j1:j2]))
        return mark_safe("".join(out))  # noqa: S308 — built only from stored, sanitised HTML

    def tokens(self, html: str) -> list[str]:
        """Split HTML into tags, runs of whitespace and words.

        Args:
            html: Stored HTML.

        Returns:
            The tokens in order. A ``<`` that opens no tag is kept as text.
        """
        return ["&lt;" if t == "<" else t for t in self.TOKEN.findall(html)]

    def is_tag(self, token: str) -> bool:
        """Whether a token is a tag rather than text."""
        return token.startswith("<")

    def tag_name(self, token: str) -> str:
        """The lower-case element name of a tag token, or an empty string."""
        found = self.NAME.match(token)
        return found.group(1).lower() if found else ""

    def depth_change(self, token: str) -> int:
        """How a token changes the nesting: one in, one out, or none."""
        if not self.is_tag(token):
            return 0
        if token.startswith("</"):
            return -1
        if token.endswith("/>") or self.tag_name(token) in self.VOID | {""}:
            return 0
        return 1

    def words_of(self, block: list[str]) -> list[str]:
        """The words of a block: its tokens without tags or whitespace."""
        return [t for t in block if not self.is_tag(t) and not t.isspace()]

    def blocks(self, html: str) -> list[list[str]]:
        """Split stored HTML into its top-level elements, each a list of tokens.

        A list is opened into its own tags and its items, so one changed item
        is one difference. Whitespace between elements is dropped, so a change
        of line breaks between paragraphs is never a difference.

        Args:
            html: Stored HTML.

        Returns:
            The elements in order.
        """
        found: list[list[str]] = []
        current: list[str] = []
        depth = 0
        for token in self.tokens(html):
            if depth == 0 and token.isspace() and not current:
                continue
            current.append(token)
            depth += self.depth_change(token)
            if depth <= 0 and not token.isspace():
                found.append(current)
                current, depth = [], 0
        if any(not t.isspace() for t in current):
            found.append(current)
        return [part for block in found for part in self.open_list(block)]

    def open_list(self, block: list[str]) -> list[list[str]]:
        """A list as its opening tag, its items and its closing tag."""
        name = self.tag_name(block[0])
        if (
            name not in self.LISTS
            or len(block) < 2
            or block[-1].lower() != f"</{name}>"
        ):
            return [block]
        return [[block[0]], *self.blocks("".join(block[1:-1])), [block[-1]]]

    def signature(self, blocks: list[list[str]]) -> list[str]:
        """What each block is compared as: its words, joined by single spaces."""
        return [" ".join(self.words_of(block)) for block in blocks]

    def reading(self, html: str) -> list[str]:
        """What a text says: the words of each element that has any."""
        return [s for s in self.signature(self.blocks(html)) if s]

    def alike(self, old: list[str], new: list[str]) -> float:
        """How alike two elements read, from 0 to 1, by their words."""
        return SequenceMatcher(
            None, self.words_of(old), self.words_of(new), autojunk=False
        ).ratio()

    def copied(self, blocks: list[list[str]]) -> list[str]:
        """Elements the newer version shares with the older, as the newer has them."""
        out: list[str] = []
        for block in blocks:
            out.extend(block)
            out.append("\n")
        return out

    def added(self, blocks: list[list[str]]) -> list[str]:
        """Elements only the newer version has, their words marked."""
        out: list[str] = []
        for block in blocks:
            out.extend(self.mark_run("ins", block))
            out.append("\n")
        return out

    def removed(self, blocks: list[list[str]]) -> list[str]:
        """Elements only the older version has, each with its own element.

        An element with no words emits no tags. A list's wrapper is kept only
        when the whole list is here and has words in it.
        """
        out: list[str] = []
        i = 0
        while i < len(blocks):
            block = blocks[i]
            i += 1
            if len(block) == 1 and self.is_tag(block[0]):
                name = self.tag_name(block[0])
                close = None
                if name in self.LISTS and not block[0].startswith("</"):
                    close = next(
                        (
                            k
                            for k in range(i, len(blocks))
                            if blocks[k][0].lower() == f"</{name}>"
                        ),
                        None,
                    )
                if close is not None:
                    inner = self.removed(blocks[i:close])
                    if inner:
                        out.extend([*block, "\n", *inner, *blocks[close], "\n"])
                    i = close + 1
                continue
            if self.words_of(block):
                out.extend(self.mark_run("del", block))
                out.append("\n")
        return out

    def pair(self, old: list[list[str]], new: list[list[str]]) -> list[str]:
        """Match the changed elements of one range to each other, in order.

        An element that reads mostly like one of the next few on the other side
        is compared word by word with it. One that matches none is added or
        removed whole, keeping its own markup.
        """
        out: list[str] = []
        i = 0
        for block in new:
            match = next(
                (
                    k
                    for k in range(i, min(i + self.window, len(old)))
                    if self.alike(old[k], block) >= self.similarity
                ),
                None,
            )
            if match is None:
                out.extend(self.added([block]))
                continue
            out.extend(self.removed(old[i:match]))
            out.extend(self.words(old[match], block))
            out.append("\n")
            i = match + 1
        out.extend(self.removed(old[i:]))
        return out

    def words(self, old: list[str], new: list[str]) -> list[str]:
        """Mark the words that differ between two elements.

        The newer element's markup is kept, so removed words sit inside it and
        their own tags are dropped.
        """
        matcher = SequenceMatcher(
            lambda t: t == " ",
            [self.key(t) for t in old],
            [self.key(t) for t in new],
            autojunk=False,
        )
        out: list[str] = []
        for op, i1, i2, j1, j2 in self.merged(matcher.get_opcodes(), new):
            if op == "equal":
                out.extend(new[j1:j2])
                continue
            if op in ("delete", "replace"):
                text = "".join(t for t in old[i1:i2] if not self.is_tag(t))
                if text.strip():
                    out.append(self.mark("del", text))
            if op in ("insert", "replace"):
                out.extend(self.mark_run("ins", new[j1:j2]))
        return out

    @staticmethod
    def key(token: str) -> str:
        """What a token is compared as: any whitespace counts as one space."""
        return " " if token.isspace() else token

    @staticmethod
    def merged(
        opcodes: Sequence[tuple[str, int, int, int, int]], new: list[str]
    ) -> list[tuple[str, int, int, int, int]]:
        """Fold a space left unchanged between two changes into them.

        A rewritten phrase then reads as one removal and one addition, not
        word by word.
        """
        out: list[tuple[str, int, int, int, int]] = []
        for op, i1, i2, j1, j2 in opcodes:
            only_space = op == "equal" and not "".join(new[j1:j2]).strip()
            if out and out[-1][0] != "equal" and (only_space or op != "equal"):
                out[-1] = ("replace", out[-1][1], i2, out[-1][3], j2)
            else:
                out.append((op, i1, i2, j1, j2))
        return out

    def mark_run(self, tag: str, tokens: list[str]) -> list[str]:
        """Mark the words of a run, leaving its tags outside the marks."""
        out: list[str] = []
        text: list[str] = []

        def flush() -> None:
            joined = "".join(text)
            out.append(self.mark(tag, joined) if joined.strip() else joined)
            text.clear()

        for token in tokens:
            if self.is_tag(token):
                flush()
                out.append(token)
            else:
                text.append(token)
        flush()
        return out

    @staticmethod
    def mark(tag: str, text: str) -> str:
        """One marked run, with words a screen reader announces at its start."""
        label = _("Added:") if tag == "ins" else _("Removed:")
        return f'<{tag}><span class="sr-only">{escape(label)} </span>{text}</{tag}>'
