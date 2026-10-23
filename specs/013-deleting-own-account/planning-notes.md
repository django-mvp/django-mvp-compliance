# Planning notes — FS-013

Suggestions from Sam for research and planning. Each is answered by name in `research.md`.

## N1 — The declaration that serves the copy serves deletion

Carried over from FS-012's planning note N2, which Sam wrote for this feature:

> The class is the one place an app says what it holds about a person. #48 (deleting an account
> and its data) can add an `erase(user)` method to it, so research should check that nothing in
> this design makes that awkward.

FS-012 is now merged, so research checks the shipped `PersonalData` class rather than its design.
The three ways a kind can say it is deleted (FR-015 to FR-017) are what the method has to express:
delete the rows `get_queryset(user)` returns, nothing to do because the rows go with the account,
or the project's own code.
