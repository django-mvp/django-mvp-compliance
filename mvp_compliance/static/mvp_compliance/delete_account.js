// The page for deleting an account: the delete button stays disabled until the
// person has typed what the field asks for. A convenience only. The server
// refuses a submission that does not match.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("delete-account-form");
  if (!form) return;
  const field = form.querySelector("input[data-expected]");
  const button = form.querySelector('[type="submit"]');
  if (!field || !button) return;
  const expected = field.dataset.expected.trim().toLowerCase();
  const update = () => {
    button.disabled = field.value.trim().toLowerCase() !== expected;
  };
  field.addEventListener("input", update);
  update();
});
