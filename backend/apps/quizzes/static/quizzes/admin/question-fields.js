// Shows only the answer field that matches each question's type.
"use strict";
(function () {
  const FIELDS = {
    multiple_choice: "choices",
    true_false: "true_false_answer",
    date_ordering: "ordered_items",
    fill_blank: "accepted_answers",
  };

  function update(select) {
    const container = select.closest(".inline-related") || select.form;
    if (!container) return;
    for (const [type, field] of Object.entries(FIELDS)) {
      const row = container.querySelector(".field-" + field);
      if (row) row.hidden = select.value !== type;
    }
  }

  function updateAll(root) {
    root.querySelectorAll('select[name$="type"]').forEach(update);
  }

  document.addEventListener("change", (event) => {
    if (event.target.matches('select[name$="type"]')) update(event.target);
  });
  document.addEventListener("formset:added", (event) => updateAll(event.target));
  document.addEventListener("DOMContentLoaded", () => updateAll(document));
})();
