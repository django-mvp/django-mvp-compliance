// The page that asks a person to agree: the submit button stays disabled until
// every required document's toggle is on. A convenience only. The server
// refuses a submission that leaves a required document unagreed.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("agreement");
  if (!form) return;
  const button = form.querySelector('[type="submit"]');
  const required = Array.from(form.querySelectorAll("input[data-required]"));
  const update = () => {
    button.disabled = !required.every((toggle) => toggle.checked);
  };
  form.addEventListener("change", update);
  update();
});
