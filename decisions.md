## Publish link on the change form (US-4)

**Decision**: Add a **Publish** entry to the change form's object tools, alongside T035's
**Preview** entry, visible only for a draft to a caller holding `publish_version`.

**Why**: No task in the brief names this addition directly, but T035's own row in `tasks.md`
says the object-tools block gets "the **Publish** link US-4 adds," and FR-013's "the confirmation
page is the only route" only holds meaning if there is a route to it. Without a link, reaching the
confirmation page requires typing its address by hand, which contradicts the feature's own premise
of a surface a non-developer can use. It is not a form field, a checkbox, or a changelist action,
so it does not touch the FR-013 prohibition on anything else that publishes.

**Revisit if**: A future story adds its own navigation to the publish address and this becomes
redundant, or the object-tools pattern changes shape.
