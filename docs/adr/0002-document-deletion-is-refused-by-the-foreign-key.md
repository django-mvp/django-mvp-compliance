# ADR 0002 — Document deletion is refused by the foreign key, not by a delete override

**Status:** accepted

## Decision

`Version.document` is declared `on_delete=models.PROTECT`. A document holding any version at all, draft or published, refuses deletion and raises Django's `ProtectedError`.

There is no `Document.delete()` override and no document queryset override. A document created by mistake is removed by discarding its drafts first and then deleting it.

## Why

The alternative is `CASCADE` together with an override on `Document.delete()`. That does not hold, because `QuerySet.delete()` never calls a model's `delete()`, so it needs a second override on the queryset. Even with both, a third route stays open: a cascade reaching the document from a relation somewhere else entirely, which neither override sees.

`PROTECT` is enforced by Django's deletion collector, which every one of those routes goes through. It is also part of the field rather than of the model class, so a historical model rebuilt inside a migration carries it too — and historical models are exactly where model-level guards disappear.

The cost is one extra step when deleting a document that still holds a draft. The benefit is that the route which would destroy published wording does not exist to be missed. An immutability rule with a cascade underneath it is not an immutability rule.

## Revisit if

A version needs to be reachable from a document that can itself be deleted — for instance if documents are ever grouped under something deletable. The question then is which relation carries the protection, not whether to replace it with an override.
