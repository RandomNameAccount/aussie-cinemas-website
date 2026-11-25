/* Front-end-only prototype behaviour. Nothing is sent or stored anywhere except an optional
   search phrase used to be kept in sessionStorage; search now uses explore.html?q= (Phase A). */
(function () {
  "use strict";
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function store(k, v) { try { if (v === undefined) return sessionStorage.getItem(k); if (v === null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, v); } catch (e) { return null; } }

  /* Navigation toggle on small screens */
  var toggle = $(".nav-toggle"), nav = $("#site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      nav.setAttribute("data-open", String(!open));
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        toggle.setAttribute("aria-expanded", "false"); nav.setAttribute("data-open", "false"); toggle.focus();
      }
    });
  }

  /* Header turns compact (56 px logo, shadow) once the page scrolls */
  var header = $("[data-site-header]");
  if (header) {
    var ticking = false;
    var setCompact = function () { header.classList.toggle("is-compact", window.scrollY > 40); ticking = false; };
    window.addEventListener("scroll", function () { if (!ticking) { ticking = true; window.requestAnimationFrame(setCompact); } }, { passive: true });
    setCompact();
  }

  /* Light and dark theme switch. The site is light (white) unless the visitor chooses dark. The choice is kept in this browser when storage is available. */
  var root = document.documentElement;
  function currentDark() { var t = root.getAttribute("data-theme"); return t === "dark"; }
  function syncToggles() { $$("[data-theme-toggle]").forEach(function (b) { b.setAttribute("aria-checked", String(currentDark())); }); }
  $$("[data-theme-toggle]").forEach(function (b) {
    b.addEventListener("click", function () {
      var next = currentDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("apa-theme", next); } catch (e) { /* storage unavailable, so the choice lasts for this page only */ }
      syncToggles();
    });
  });
  syncToggles();

  /* Homepage search is a plain GET form to explore.html?q=..., so it works without JavaScript too. */

  /* Explore: search and filters over the genuine records (built by tools/build_genuine.py), list and map views.
     Search matches every word against the name, former names, address, suburb or town, region, state and status. */
  var gx = $("[data-gx-filters]");
  if (gx) {
    var items = $$("[data-list] .gx-item"), count = $("[data-count]"), listWrap = $("[data-list-wrap]"), mapEl = $("[data-map]"), empty = $("[data-empty]");
    var mapCanvas = $("[data-map] [data-real-map]");
    var view = "list", total = items.length;
    function norm(t) { return String(t || "").toLowerCase().replace(/&/g, " and ").replace(/[\u2019'`]/g, "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim(); }
    function readUrl() {
      var p = new URLSearchParams(window.location.search);
      if (p.get("q")) gx.elements.q.value = p.get("q");
      if (p.get("state")) gx.elements.state.value = p.get("state").toLowerCase();
      var h = (window.location.hash || "").slice(1);
      if (h.indexOf("state-") === 0) gx.elements.state.value = h.slice(6);
      if (h === "view-map" || p.get("view") === "map") view = "map";
    }
    function writeUrl() {
      var p = new URLSearchParams();
      var q = gx.elements.q.value.trim(); if (q) p.set("q", q);
      if (gx.elements.state.value) p.set("state", gx.elements.state.value);
      if (view === "map") p.set("view", "map");
      var url = window.location.pathname + (p.toString() ? "?" + p.toString() : "");
      try { history.replaceState(null, "", url); } catch (e) { /* ignore */ }
    }
    function checked(name) { return $$("input[name=" + name + "]:checked", gx).map(function (i) { return i.value; }); }
    function apply() {
      var words = norm(gx.elements.q.value).split(" ").filter(Boolean);
      var st = gx.elements.state.value, loc = gx.elements.loc.value, era = gx.elements.era.value;
      var statuses = checked("status"), evid = checked("evidence");
      var shown = 0, ids = new Set();
      items.forEach(function (c) {
        var hay = c.getAttribute("data-search");
        var ok = words.every(function (w) { return hay.indexOf(w) !== -1; }) &&
          (!st || c.getAttribute("data-state") === st) && (!loc || c.getAttribute("data-loc") === loc) && (!era || c.getAttribute("data-era") === era) &&
          statuses.indexOf(c.getAttribute("data-status")) !== -1 && evid.indexOf(c.getAttribute("data-evidence")) !== -1;
        c.hidden = !ok;
        if (ok) { shown++; ids.add(c.getAttribute("data-id")); }
      });
      var filtered = words.length || st || loc || era || statuses.length < 4 || evid.length < 4;
      empty.hidden = shown !== 0;
      listWrap.hidden = view !== "list" || shown === 0;
      mapEl.hidden = view !== "map" || shown === 0;
      var onMap = mapCanvas && mapCanvas._apaFilter ? mapCanvas._apaFilter(filtered ? ids : null) : null;
      count.textContent = shown + (shown === 1 ? " cinema" : " cinemas") + (filtered ? " match" : "") +
        (view === "map" && onMap !== null ? " (" + onMap + " on the map" + (onMap < shown ? "; the rest have no public location and stay in the list" : "") + ")" : "");
      $$("[data-view]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-view") === view)); });
      writeUrl();
    }
    readUrl();
    gx.addEventListener("input", apply);
    gx.addEventListener("change", apply);
    gx.addEventListener("submit", function (ev) { ev.preventDefault(); apply(); });
    gx.addEventListener("reset", function () { setTimeout(apply, 0); });
    $("[data-clear]").addEventListener("click", function () { gx.reset(); gx.elements.q.focus(); });
    $$("[data-view]").forEach(function (b) { b.addEventListener("click", function () { view = b.getAttribute("data-view"); apply(); }); });
    window.addEventListener("hashchange", function () { readUrl(); apply(); });
    apply();
    // The map script loads after this one; filter it once it is ready.
    window.addEventListener("apa:map-ready", apply);
  }

  /* Share form: plain-language date interpretation, validation and a preview that sends nothing */
  var MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];
  function interpret(raw) {
    var s = raw.trim().toLowerCase().replace(/\s+/g, " ");
    if (!s) return { ok: true, text: "Date unknown. That's fine." };
    if (/^(not sure|unsure|don'?t know|unknown|\?)$/.test(s)) return { ok: true, text: "Date unknown. That's fine." };
    var approx = /^(about|around|circa|c\.?|approx\.?|approximately|roughly) /.test(s);
    s = s.replace(/^(about|around|circa|c\.?|approx\.?|approximately|roughly) /, "");
    var m;
    if ((m = s.match(/^(early|mid|late)[ -]?(\d{3})0s$/))) return { ok: true, text: "We'll record this as the " + m[1] + " " + m[2] + "0s." };
    if ((m = s.match(/^(\d{3})0'?s$/))) return { ok: true, text: "We'll record this as some time in the " + m[1] + "0s (" + m[1] + "0 to " + m[1] + "9)." };
    if ((m = s.match(/^(before|after) (\d{4})$/))) return { ok: true, text: "We'll record this as " + m[1] + " " + m[2] + "." };
    if ((m = s.match(/^(\d{4}) ?(-|to|–|or) ?(\d{4})$/))) {
      if (+m[3] < +m[1]) return { ok: false, text: "The second year comes before the first. Please check." };
      return { ok: true, text: m[2] === "or" ? "We'll record this as either " + m[1] + " or " + m[3] + "." : "We'll record this as some time between " + m[1] + " and " + m[3] + "." };
    }
    if ((m = s.match(/^(\d{4})$/))) return yearCheck(+m[1], (approx ? "About " : "") + m[1] + ".");
    if ((m = s.match(/^([a-z]+) (\d{4})$/)) && MONTHS.indexOf(m[1]) !== -1) return yearCheck(+m[2], (approx ? "About " : "") + cap(m[1]) + " " + m[2] + ".");
    if ((m = s.match(/^(\d{1,2}) ([a-z]+) (\d{4})$/)) && MONTHS.indexOf(m[2]) !== -1) {
      var d = new Date(+m[3], MONTHS.indexOf(m[2]), +m[1]);
      if (d.getDate() !== +m[1]) return { ok: false, text: "That day doesn't exist in that month. Please check." };
      return yearCheck(+m[3], (approx ? "About " : "") + (+m[1]) + " " + cap(m[2]) + " " + m[3] + ".");
    }
    if ((m = s.match(/^(summer|autumn|winter|spring) (\d{4})$/))) return yearCheck(+m[2], "The " + m[1] + " of " + m[2] + " (Australian seasons).");
    return { ok: true, text: "We'll keep your words exactly as you wrote them, and a volunteer will interpret them." };
    function cap(x) { return x.charAt(0).toUpperCase() + x.slice(1); }
    function yearCheck(y, t) { return y < 1890 || y > new Date().getFullYear() ? { ok: false, text: "That year is outside 1890 to today. Please check." } : { ok: true, text: "We'll record this as: " + t }; }
  }

  var form = $("[data-share-form]");
  if (form) {
    var when = $("#s-when"), out = $("#s-when-out"), errBox = $("[data-form-errors]"), errList = $("[data-error-list]"), done = $("[data-form-done]");
    var matBox = $("[data-material]");
    function updateWhen() { var r = interpret(when.value); out.textContent = r.text; out.classList.toggle("is-error", !r.ok); return r; }
    when.addEventListener("input", updateWhen);
    function updateKind() { matBox.hidden = form.elements.kind.value !== "material"; }
    $$("input[name=kind]", form).forEach(function (r) { r.addEventListener("change", updateKind); });
    var cinemaParam = new URLSearchParams(window.location.search).get("cinema") || ((window.location.hash || "").match(/^#cinema-(.+)$/) || [])[1];
    if (cinemaParam) { var sel = $("#s-cinema"); if (sel && sel.querySelector('option[value="' + cinemaParam.replace(/[^a-z0-9-]/g, "") + '"]')) sel.value = cinemaParam; }
    function setError(el, msg) {
      el.setAttribute("aria-invalid", "true");
      var id = el.id + "-err", p = document.getElementById(id);
      if (!p) { p = document.createElement("p"); p.className = "field-error"; p.id = id; el.parentNode.insertBefore(p, el); }
      p.textContent = msg;
      el.setAttribute("aria-describedby", (el.getAttribute("aria-describedby") || "").replace(id, "").trim() + " " + id);
      var li = document.createElement("li"), a = document.createElement("a");
      a.href = "#" + el.id; a.textContent = msg; li.appendChild(a); errList.appendChild(li);
    }
    function clearErrors() {
      errList.innerHTML = ""; errBox.hidden = true;
      $$("[aria-invalid]", form).forEach(function (el) { el.removeAttribute("aria-invalid"); });
      $$(".field-error", form).forEach(function (p) { p.parentNode.removeChild(p); });
    }
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      clearErrors(); done.hidden = true;
      var story = $("#s-story");
      if (story.value.trim().length < 10) setError(story, "Please write at least a sentence about your memory or material.");
      if (!$("#s-cinema").value && !$("#s-place").value.trim()) setError($("#s-place"), "Please choose a cinema or tell us its name and town. A rough description is fine.");
      if (!updateWhen().ok) setError(when, "Please check the date: " + out.textContent);
      if (errList.children.length) { errBox.hidden = false; errBox.focus(); return; }
      var cin = $("#s-cinema"), place = cin.value ? cin.options[cin.selectedIndex].text : $("#s-place").value.trim();
      $("[data-done-text]").textContent = "You would be sharing a " + { memory: "memory", identify: "request to identify a cinema", material: "offer of material" }[form.elements.kind.value] +
        " about " + place + ". " + out.textContent + " This demonstration did not send or save anything.";
      done.hidden = false; done.focus();
    });
    form.addEventListener("reset", function () { setTimeout(function () { clearErrors(); done.hidden = true; updateWhen(); updateKind(); }, 0); });
    updateKind();
  }
})();
