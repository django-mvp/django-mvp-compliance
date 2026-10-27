"""Tests for mvp_compliance.comparison."""

import time
from datetime import timedelta
from html.parser import HTMLParser
from unittest import mock

import pytest
from django.utils import timezone

from mvp_compliance.comparison import Comparison
from mvp_compliance.models import Version
from tests.factories import DocumentFactory, VersionFactory

VOID = {"br", "hr", "img", "input", "wbr"}
MARKS = {"ins", "del"}


class Reading(HTMLParser):
    """Read marked-up output the way a browser would, keeping what the tests ask about."""

    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.balanced = True
        self.tags: set[tuple[str, tuple]] = set()
        self.marks: list[dict] = []
        self.current: dict | None = None
        self.hidden = 0
        self.feed(html)
        self.close()
        self.balanced = self.balanced and not self.stack

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class") or ""
        label = tag == "span" and "sr-only" in classes.split()
        if tag in MARKS:
            self.current = {
                "tag": tag,
                "text": "",
                "ancestors": list(self.stack),
                "label_first": False,
            }
            self.marks.append(self.current)
            self.stack.append(tag)
            return
        if label and self.current is not None:
            self.current["label_first"] = not self.current["text"]
            self.hidden += 1
            self.stack.append(tag)
            return
        self.tags.add((tag, tuple(sorted(attrs))))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.balanced = False
            return
        self.stack.pop()
        if tag == "span" and self.hidden:
            self.hidden -= 1
        if tag in MARKS:
            self.current = None

    def handle_data(self, data):
        if self.current is not None and not self.hidden:
            self.current["text"] += data

    def words(self, tag: str) -> list[str]:
        """The text of every mark of one kind, outside its hidden label."""
        return [m["text"].strip() for m in self.marks if m["tag"] == tag]


def published(document, markdown: str) -> Version:
    """A version of the document published from Markdown, so its html is real."""
    version = VersionFactory(document=document, markdown=markdown)
    version.publish()
    return version


def stored(document, html: str, minutes: int = 0) -> Version:
    """A published version whose html is written directly, bypassing the renderer."""
    return Version.objects.create(
        document=document,
        markdown="stored",
        html=html,
        status=Version.Status.SUPERSEDED,
        number=f"2026.{minutes + 1}",
        published_at=timezone.now() + timedelta(minutes=minutes),
    )


def tags_of(html: str) -> set[tuple[str, tuple]]:
    """The tags a text holds, with their attributes."""
    return Reading(html).tags


@pytest.fixture
def document():
    return DocumentFactory()


@pytest.mark.django_db
class TestOf:
    def test_either_order_gives_the_same_older_and_newer(self, document):
        first = published(document, "Original wording")
        second = published(document, "Revised wording")

        forward = Comparison.of(first, second)
        backward = Comparison.of(second, first)

        assert (forward.older, forward.newer) == (first, second)
        assert (backward.older, backward.newer) == (first, second)


@pytest.mark.django_db
class TestMarkingWords:
    def test_added_words_are_inside_ins_and_removed_words_inside_del(self, document):
        older = published(document, "We keep your data for one year.")
        newer = published(document, "We keep your data for two years.")

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.words("del") == ["one year."]
        assert reading.words("ins") == ["two years."]

    def test_no_word_the_two_versions_share_is_marked(self, document):
        older = published(document, "Alpha beta gamma delta")
        newer = published(document, "Alpha beta gamma delta epsilon")

        reading = Reading(Comparison.of(older, newer).html())

        marked = " ".join(m["text"] for m in reading.marks)
        for shared in ("Alpha", "beta", "gamma", "delta"):
            assert shared not in marked

    def test_one_word_changed_in_a_long_paragraph_marks_that_word_alone(self, document):
        words = [f"word{n}" for n in range(60)]
        changed = [*words[:30], "replacement", *words[31:]]
        older = published(document, " ".join(words))
        newer = published(document, " ".join(changed))

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.words("del") == ["word30"]
        assert reading.words("ins") == ["replacement"]

    def test_each_mark_starts_with_a_hidden_label(self, document):
        older = published(document, "Keep this. Drop that.")
        newer = published(document, "Keep this. Add those.")

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.marks
        assert all(mark["label_first"] for mark in reading.marks)

    def test_a_difference_in_whitespace_alone_marks_nothing(self, document):
        older = published(document, "One two three")
        newer = published(document, "One  two\tthree")

        comparison = Comparison.of(older, newer)

        assert Reading(comparison.html()).marks == []


@pytest.mark.django_db
class TestKeepingStructure:
    def test_a_changed_heading_keeps_its_element(self, document):
        older = published(document, "# Privacy\n\nBody text.")
        newer = published(document, "# Privacy notice\n\nBody text.")

        reading = Reading(Comparison.of(older, newer).html())

        assert [m["ancestors"] for m in reading.marks] == [["h1"]]
        assert reading.words("ins") == ["notice"]

    def test_a_changed_list_item_keeps_its_list_and_its_item(self, document):
        older = published(document, "- first thing\n- second thing\n- third thing")
        newer = published(document, "- first thing\n- second item\n- third thing")

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.words("ins") == ["item"]
        assert all(m["ancestors"] == ["ul", "li"] for m in reading.marks)

    def test_a_changed_link_keeps_its_element(self, document):
        older = published(document, "Read [the old policy](https://example.com/a).")
        newer = published(document, "Read [the new policy](https://example.com/a).")

        reading = Reading(Comparison.of(older, newer).html())

        assert [m["ancestors"] for m in reading.marks] == [["p", "a"], ["p", "a"]]
        assert ("a", (("href", "https://example.com/a"),)) in reading.tags

    def test_a_removed_list_item_is_removed_whole_with_its_own_element(self, document):
        older = published(document, "- keep one\n- remove me\n- keep two")
        newer = published(document, "- keep one\n- keep two")

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.words("del") == ["remove me"]
        assert reading.marks[0]["ancestors"] == ["ul", "li"]
        assert reading.balanced

    def test_a_removed_paragraph_is_removed_whole_with_its_own_element(self, document):
        older = published(document, "Stays.\n\nGoes away entirely.\n\nAlso stays.")
        newer = published(document, "Stays.\n\nAlso stays.")

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.words("del") == ["Goes away entirely."]
        assert reading.marks[0]["ancestors"] == ["p"]
        assert reading.words("ins") == []

    def test_a_wholly_removed_list_keeps_its_wrapper_with_its_items_inside(
        self, document
    ):
        older = published(document, "Intro.\n\n- one thing\n- another thing")
        newer = published(document, "Intro.")

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.words("del") == ["one thing", "another thing"]
        assert all(m["ancestors"] == ["ul", "li"] for m in reading.marks)
        assert reading.balanced

    def test_a_removed_element_with_no_words_emits_no_tags(self, document):
        older = stored(document, "<p>Text stays.</p>\n<hr>\n<p>More stays.</p>")
        newer = stored(document, "<p>Text stays.</p>\n<p>More stays.</p>", minutes=1)

        output = Comparison.of(older, newer).html()

        assert "<hr" not in output
        assert Reading(output).marks == []

    @pytest.mark.parametrize(
        ("before", "after"),
        [
            ("- one thing\n- another thing", "1. one thing\n2. another thing"),
            ("- one thing\n- another thing", "Now a paragraph of text."),
            ("A paragraph of plain words.", "- one thing\n- another thing"),
        ],
        ids=["ul-to-ol", "list-to-paragraph", "paragraph-to-list"],
    )
    def test_every_element_closes_in_order(self, document, before, after):
        older = published(document, before)
        newer = published(document, after)

        reading = Reading(Comparison.of(older, newer).html())

        assert reading.balanced

    def test_the_newer_versions_list_wrapper_is_the_only_one(self, document):
        older = published(document, "- one thing\n- another thing")
        newer = published(document, "1. one thing\n2. another thing")

        output = str(Comparison.of(older, newer).html())

        assert "<ol" in output
        assert "<ul" not in output


@pytest.mark.django_db
class TestOutputSafety:
    def test_no_tag_appears_that_neither_version_holds(self, document):
        older = published(document, "# Title\n\nSome [link](https://example.com) here.")
        newer = published(
            document, "# Title\n\nSome [link](https://example.com) there.\n\n- new"
        )

        output = Comparison.of(older, newer).html()

        assert tags_of(output) <= tags_of(older.html) | tags_of(newer.html)

    def test_text_that_looks_like_markup_stays_escaped(self, document):
        older = published(document, "Write `<img src=x onerror=alert(1)>` here.")
        newer = published(document, "Write `<img src=x onerror=alert(2)>` here.")

        output = str(Comparison.of(older, newer).html())

        assert "<img" not in output
        assert "&lt;img" in output

    def test_a_greater_than_inside_an_attribute_value_does_not_end_the_tag(
        self, document
    ):
        older = stored(document, '<p>Read <a href="/a" title="a > b">this</a> now</p>')
        newer = stored(
            document,
            '<p>Read <a href="/a" title="a > b">that</a> now</p>',
            minutes=1,
        )

        output = Comparison.of(older, newer).html()

        reading = Reading(output)
        assert reading.words("del") == ["this"]
        assert reading.words("ins") == ["that"]
        assert tags_of(output) <= tags_of(older.html) | tags_of(newer.html)
        assert reading.balanced

    def test_markup_written_as_text_in_a_stored_version_stays_text(self, document):
        older = stored(document, "<p>Use &lt;img src=x&gt; here</p>")
        newer = stored(document, "<p>Use &lt;img src=y&gt; here</p>", minutes=1)

        output = str(Comparison.of(older, newer).html())

        assert "<img" not in output
        assert "&lt;img" in output

    def test_the_output_is_safe_to_render_as_html(self, document):
        older = published(document, "Before")
        newer = published(document, "After")

        output = Comparison.of(older, newer).html()

        assert hasattr(output, "__html__")


@pytest.mark.django_db
class TestSame:
    def test_a_version_with_itself_is_the_same_and_marks_nothing(self, document):
        version = published(document, "One wording.")

        comparison = Comparison.of(version, version)

        assert comparison.same
        assert Reading(comparison.html()).marks == []

    def test_two_identical_wordings_are_the_same(self, document):
        older = stored(document, "<p>Same words.</p>")
        newer = stored(document, "<p>Same words.</p>", minutes=1)

        comparison = Comparison.of(older, newer)

        assert comparison.same
        assert Reading(comparison.html()).marks == []

    def test_a_link_with_a_new_address_is_the_same_and_marks_nothing(self, document):
        older = published(document, "See [the page](https://example.com/a).")
        newer = published(document, "See [the page](https://example.com/b).")

        comparison = Comparison.of(older, newer)

        assert comparison.same
        assert Reading(comparison.html()).marks == []

    def test_a_word_in_a_new_wrapping_element_is_the_same_and_marks_nothing(
        self, document
    ):
        older = published(document, "Some important words.")
        newer = published(document, "Some **important** words.")

        comparison = Comparison.of(older, newer)

        assert comparison.same
        assert Reading(comparison.html()).marks == []

    def test_a_difference_in_whitespace_alone_is_the_same(self, document):
        older = published(document, "One two three")
        newer = published(document, "One  two   three")

        assert Comparison.of(older, newer).same

    def test_a_changed_word_is_not_the_same(self, document):
        older = published(document, "One two three")
        newer = published(document, "One two four")

        assert not Comparison.of(older, newer).same


@pytest.mark.django_db
class TestSpeed:
    @staticmethod
    def items(count: int, prefix: str) -> str:
        """A list of ``count`` items of fifteen words each, every word unique."""
        return (
            "<ul>\n"
            + "\n".join(
                "<li>" + " ".join(f"{prefix}{n}x{w}" for w in range(15)) + "</li>"
                for n in range(count)
            )
            + "\n</ul>"
        )

    @staticmethod
    def paragraphs(count: int, shift: int) -> str:
        """``count`` paragraphs of fifteen words, every other word offset by ``shift``."""
        return "\n".join(
            "<p>"
            + " ".join(
                f"w{n}x{w}" if (w + shift) % 2 else f"v{n}x{w}y{shift}"
                for w in range(15)
            )
            + "</p>"
            for n in range(count)
        )

    def test_the_pairing_comparisons_are_bounded_by_elements_times_the_window(
        self, document
    ):
        older = stored(document, self.items(1000, "a"))
        newer = stored(document, self.items(1000, "b"), minutes=1)
        comparison = Comparison.of(older, newer)
        original = Comparison.alike
        calls = []

        def counting(self, old, new):
            calls.append(1)
            return original(self, old, new)

        with mock.patch.object(Comparison, "alike", counting):
            comparison.html()

        assert 0 < len(calls) <= 1000 * Comparison.window

    def test_fifteen_thousand_words_that_share_nothing_compare_in_under_a_second(
        self, document
    ):
        older = stored(document, self.items(1000, "a"))
        newer = stored(document, self.items(1000, "b"), minutes=1)
        comparison = Comparison.of(older, newer)

        started = time.perf_counter()
        comparison.html()

        assert time.perf_counter() - started < 1

    def test_fifteen_thousand_words_changed_throughout_compare_in_under_a_second(
        self, document
    ):
        older = stored(document, self.paragraphs(1000, 0))
        newer = stored(document, self.paragraphs(1000, 1), minutes=1)
        comparison = Comparison.of(older, newer)

        started = time.perf_counter()
        comparison.html()

        assert time.perf_counter() - started < 1
