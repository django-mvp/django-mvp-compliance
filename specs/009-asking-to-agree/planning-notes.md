# Planning notes — 009 Asking a signed-in person to agree to what is outstanding

Notes from the maintainer for the prototype and the plan. `spec.md` says what the feature does and
never how. This file is where how is welcome. Each note is to be answered by name when the feature
is planned.

A list row carries no status badge. If the page lists the outstanding documents, a row says what
it has to say in words or by its position, not with a badge.

An alert goes above the page title. That covers the message shown after an acceptance could not be
recorded, and any other message about the page as a whole.

A form never starts with a titled fieldset. The request to agree is not wrapped in a fieldset
whose legend repeats the page's title.

A reusable piece of a template is a Cotton component. If the block that shows one document with
its request to agree is used more than once, it is a component and not an include.
