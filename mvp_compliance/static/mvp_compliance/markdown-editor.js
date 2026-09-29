/* The toolbar comes from `data-toolbar`, never from here, so it is the widget's own
 * list. No preview control: the preview is a server-rendered page (FS-002). */
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
