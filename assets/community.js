/* Cinema Community: filters, demo voting, dashboard tabs and follow toggles. Front end only; nothing is saved. */
(function () {
  "use strict";
  document.querySelectorAll("[data-cc-filter]").forEach(function (root) {
    var state = "all";
    var chips = root.querySelectorAll(".cc-chip[data-value]");
    var checks = root.querySelectorAll("input[data-check]");
    var items = root.querySelectorAll(".cc-event");
    var empty = root.querySelector("[data-empty]");
    var count = root.querySelector("[data-count]");
    function apply() {
      var want = {};
      checks.forEach(function (c) { want[c.getAttribute("data-check")] = c.checked; });
      var shown = 0;
      items.forEach(function (it) {
        var ok = (state === "all" || it.getAttribute("data-state") === state) &&
                 (!want.followed || it.getAttribute("data-followed") === "1") &&
                 (!want.special || it.getAttribute("data-special") === "1");
        it.hidden = !ok; if (ok) shown++;
      });
      root.querySelectorAll(".cc-day").forEach(function (d) { d.hidden = !d.querySelector(".cc-event:not([hidden])"); });
      if (empty) empty.hidden = shown !== 0;
      if (count) count.textContent = shown + (shown === 1 ? " session shown" : " sessions shown");
    }
    chips.forEach(function (b) {
      b.addEventListener("click", function () {
        state = b.getAttribute("data-value");
        chips.forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
        apply();
      });
    });
    checks.forEach(function (c) { c.addEventListener("change", apply); });
    apply();
  });

  var form = document.querySelector("[data-cc-vote]");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var pick = form.querySelector("input[name=film]:checked");
      var err = form.querySelector("[data-vote-error]");
      if (!pick) { err.hidden = false; return; }
      err.hidden = true;
      var label = pick.closest("label").querySelector("strong").textContent;
      var done = document.querySelector("[data-vote-done]");
      done.querySelector("[data-vote-choice]").textContent = label;
      done.hidden = false;
      form.hidden = true;
      done.setAttribute("tabindex", "-1"); done.focus();
    });
  }
  var rt = document.querySelector("[data-results-toggle]");
  if (rt) {
    rt.addEventListener("click", function () {
      var p = document.getElementById(rt.getAttribute("aria-controls"));
      var open = rt.getAttribute("aria-expanded") === "true";
      rt.setAttribute("aria-expanded", open ? "false" : "true");
      p.hidden = open;
      rt.textContent = open ? "Preview results after the poll closes" : "Hide the results preview";
    });
  }

  document.querySelectorAll("[data-cc-tabs]").forEach(function (list) {
    var tabs = Array.prototype.slice.call(list.querySelectorAll("[role=tab]"));
    function select(t, focus) {
      tabs.forEach(function (o) {
        var on = o === t;
        o.setAttribute("aria-selected", on ? "true" : "false");
        o.tabIndex = on ? 0 : -1;
        document.getElementById(o.getAttribute("aria-controls")).hidden = !on;
      });
      if (focus) t.focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(t); });
      t.addEventListener("keydown", function (e) {
        var n = null;
        if (e.key === "ArrowRight") n = tabs[(i + 1) % tabs.length];
        if (e.key === "ArrowLeft") n = tabs[(i - 1 + tabs.length) % tabs.length];
        if (e.key === "Home") n = tabs[0];
        if (e.key === "End") n = tabs[tabs.length - 1];
        if (n) { e.preventDefault(); select(n, true); }
      });
    });
  });

  document.querySelectorAll("[data-follow]").forEach(function (b) {
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") === "true";
      b.setAttribute("aria-pressed", on ? "false" : "true");
      b.textContent = on ? "Follow" : "Following";
    });
  });
})();
