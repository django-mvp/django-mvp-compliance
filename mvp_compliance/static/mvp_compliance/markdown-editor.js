/* Turns every textarea carrying the marker attribute into an EasyMDE editor.
 *
 * The toolbar is never hard-coded here: it is read off `data-toolbar`,
 * which `MarkdownEditorWidget` serialises from its own `TOOLBAR` list, so
 * the button set on the page can only ever be the one the widget declared
 * (D2, D9). No preview, side-by-side or full-screen control is wired up —
 * the preview is a separate, server-rendered page (D3, R6).
 */
(function () {
  "use strict";

  var ACTIONS = {
    heading: "toggleHeadingSmaller",
    bold: "toggleBold",
    italic: "toggleItalic",
    "unordered-list": "toggleUnorderedList",
    "ordered-list": "toggleOrderedList",
    link: "drawLink",
    quote: "toggleBlockquote",
  };

  function buildToolbar(entries) {
    return entries.map(function (entry) {
      return {
        name: entry.name,
        action: EasyMDE[ACTIONS[entry.name]],
        className: "mvp-compliance-toolbar-" + entry.name,
        title: entry.title,
      };
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document
      .querySelectorAll("[data-mvp-compliance-markdown-editor]")
      .forEach(function (textarea) {
        var toolbar = buildToolbar(JSON.parse(textarea.dataset.toolbar));
        new EasyMDE({
          element: textarea,
          toolbar: toolbar,
          spellChecker: false,
          status: false,
        });
      });
  });
})();
