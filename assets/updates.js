/* Member suggestions for cinema records ("Suggest an update"), plus the moderators' review queue.
   Talks to Supabase (config in assets/forum-config.js; table from supabase/cinema_updates_schema.sql).
   A suggestion never changes the archive: it waits for a moderator, and accepted suggestions are applied
   by an editor through staging. All text from the database is inserted with textContent, never as HTML. */
(function () {
  "use strict";
  var cfg = window.FCA_FORUM || {};
  var root = document.querySelector("[data-updates]");
  if (!root) return;
  var mode = root.getAttribute("data-updates");
  var off = root.querySelector("[data-forum-off]");

  var TOPIC = { location: "Where it stood", name: "Name", dates: "Dates", today: "What's there today", description: "Description", other: "Something else" };
  var BASIS = { worked: "Worked there", visited: "Went there", family: "Family history", research: "Own research", document: "Document or newspaper", other: "Other" };
  var STATUS = { pending: "Waiting for review", accepted: "Accepted: an editor will update the record", declined: "Declined", needs_info: "More information needed",
                 applied: "Applied to the archive", withdrawn: "Withdrawn" };
  var KIND = { record: "cinema record", archive: "archive listing", lead: "research lead", "new": "new cinema" };

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "text") n.textContent = attrs[k];
      else if (k === "class") n.className = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) n.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return n;
  }
  function when(iso) {
    try { return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" }); } catch (e) { return iso; }
  }
  function say(box, text, kind) {
    box.hidden = false; box.className = "notice " + (kind === "error" ? "n-alert" : kind === "ok" ? "n-ok" : "n-info");
    box.textContent = text;
  }

  // What the suggestion is about, from the link on a record page: ?type=record|archive|lead&id=<id>&name=<name>
  var q = new URLSearchParams(location.search);
  var target = { type: q.get("type"), id: q.get("id"), name: (q.get("name") || "").slice(0, 120) };
  if (!/^(record|archive|lead)$/.test(target.type || "") || !/^[a-z0-9-]{2,60}$/.test(target.id || "") || target.name.length < 2) {
    target = { type: "new", id: null, name: "" };
  }
  if (mode === "form") {
    var lede = document.querySelector("[data-up-target]");
    if (lede && target.type !== "new") {
      var back = (target.type === "record" ? "cinemas/" : target.type === "archive" ? "archive/" : "leads/") + target.id + ".html";
      lede.textContent = "";
      lede.appendChild(document.createTextNode("Suggesting an update to the " + KIND[target.type] + " "));
      lede.appendChild(el("a", { href: back, text: target.name }));
      lede.appendChild(document.createTextNode(". An editor checks every suggestion before the archive changes."));
    } else if (lede) {
      var nn = root.querySelector("[data-up-newname]"); if (nn) nn.hidden = false;
      var h = root.querySelector("#up-h"); if (h) h.textContent = "Tell us about a cinema we don't have";
    }
  }

  if (!cfg.url || !cfg.anonKey || !window.supabase) {
    if (off) off.hidden = false;
    root.querySelectorAll("form button, form input, form select, form textarea").forEach(function (x) { x.disabled = true; });
    var a = root.querySelector("[data-auth]"); if (a) a.textContent = "Member sign-in opens soon.";
    var pf = root.querySelector("#up-form"); if (pf) pf.hidden = false;  // show the form, switched off, so visitors can see what's coming
    return;
  }
  var sb = window.supabase.createClient(cfg.url, cfg.anonKey);
  var me = { user: null, profile: null };
  var authBox = root.querySelector("[data-auth]");

  async function loadMe() {
    var s = await sb.auth.getSession();
    me.user = s.data.session ? s.data.session.user : null;
    me.profile = null;
    if (me.user) { var p = await sb.rpc("my_profile").maybeSingle(); me.profile = p.data || null; }
    renderAuth();
    root.querySelectorAll("[data-needs-member]").forEach(function (n) { n.hidden = !me.profile; });
  }
  function renderAuth() {
    if (!authBox) return;
    authBox.textContent = "";
    var msg = el("p", { class: "notice", hidden: true, role: "status" });
    if (!me.user) {
      var email = el("input", { type: "email", id: "up-email", required: true, autocomplete: "email" });
      authBox.appendChild(el("form", { class: "stack", onsubmit: async function (e) {
        e.preventDefault();
        var r = await sb.auth.signInWithOtp({ email: email.value.trim(), options: { emailRedirectTo: location.href.split("#")[0] } });
        if (r.error) say(msg, "We couldn't send the link: " + r.error.message, "error");
        else say(msg, "Check your email for a sign-in link. It works once and expires after an hour.", "ok");
      } }, [
        el("h2", { class: "cc-h2", text: "Sign in to suggest an update" }),
        el("p", { class: "cc-muted", text: "Suggestions need a free member account, so we can thank you and ask follow-up questions. We email you a sign-in link; there's no password." }),
        el("div", { class: "field" }, [el("label", { for: "up-email", text: "Email address" }), email]),
        el("div", { class: "btn-row" }, [el("button", { type: "submit", class: "btn btn-primary", text: "Email me a sign-in link" })]), msg]));
      return;
    }
    if (!me.profile) {
      authBox.appendChild(el("div", { class: "stack" }, [
        el("h2", { class: "cc-h2", text: "One more step" }),
        el("p", { text: "Create your member profile (a display name and the community guidelines), then come back to this page." }),
        el("div", { class: "btn-row" }, [el("a", { class: "btn btn-primary", href: "forums.html", text: "Create my profile" }),
          el("button", { type: "button", class: "btn btn-secondary", text: "Sign out", onclick: signOut })])]));
      return;
    }
    if (me.profile.suspended_until && new Date(me.profile.suspended_until) > new Date()) {
      authBox.appendChild(el("p", { text: "Your account is paused until " + when(me.profile.suspended_until) + ", so you can't send suggestions for now." }));
      root.querySelectorAll("[data-needs-member]").forEach(function (n) { n.remove(); });
      return;
    }
    var bits = [el("span", {}, ["Signed in as ", el("strong", { text: me.profile.display_name })])];
    if (me.profile.role !== "member") bits.push(el("a", { href: "moderation.html#updates", text: "Review suggestions" }));
    bits.push(el("button", { type: "button", class: "btn btn-secondary", text: "Sign out", onclick: signOut }));
    authBox.appendChild(el("div", { class: "fm-whoami" }, bits));
  }
  async function signOut() { await sb.auth.signOut(); await loadMe(); refresh(); }

  // ------------------------------------------------------------ member form
  function readForm(f) {
    var topics = Array.prototype.map.call(f.querySelectorAll("input[name=topics]:checked"), function (x) { return x.value; });
    var v = function (n) { var x = f.elements[n]; return x && x.value.trim() ? x.value.trim() : null; };
    return {
      target_type: target.type, target_id: target.id,
      target_name: target.type === "new" ? (v("target_name") || "") : target.name,
      topics: topics, details: v("details") || "", address: v("address"), locality: v("locality"), state: v("state"),
      basis: v("basis") || "", source_url: v("source_url"), source_note: v("source_note"),
      credit_me: f.elements.credit_me.checked, own_words: f.elements.own_words.checked
    };
  }
  function problems(r) {
    var p = [];
    if (r.target_name.length < 2) p.push("Give the cinema's name.");
    if (!r.topics.length) p.push("Choose at least one thing to update.");
    if (r.details.length < 20) p.push("Tell us a little more (at least 20 characters).");
    if (!r.basis) p.push("Tell us how you know.");
    if (r.source_url && !/^https?:\/\/\S+$/.test(r.source_url)) p.push("The source link should start with https://");
    if (!r.own_words) p.push("Confirm the suggestion is in your own words.");
    return p;
  }
  function wireForm() {
    var f = root.querySelector("#up-form"); if (!f) return;
    var msg = root.querySelector("[data-up-msg]");
    f.addEventListener("submit", async function (e) {
      e.preventDefault();
      var r = readForm(f), p = problems(r);
      if (p.length) { say(msg, p.join(" "), "error"); return; }
      var btn = f.querySelector("button[type=submit]"); btn.disabled = true;
      var res = await sb.from("cinema_updates").insert(r).select("id").single();
      btn.disabled = false;
      if (res.error) { say(msg, "We couldn't send it: " + res.error.message, "error"); return; }
      f.reset();
      say(msg, "Thank you. Your suggestion is in the queue, and you'll see the result below once a moderator has read it.", "ok");
      renderMine();
    });
  }
  async function renderMine() {
    var box = root.querySelector("[data-up-mine]"); if (!box || !me.profile) return;
    var r = await sb.from("cinema_updates").select("id, target_type, target_name, topics, status, review_note, created_at")
      .eq("author_id", me.user.id).order("created_at", { ascending: false }).limit(50);
    box.textContent = "";
    if (r.error) { box.textContent = "Your suggestions couldn't be loaded."; return; }
    if (!r.data.length) { box.appendChild(el("p", { class: "cc-muted", text: "You haven't sent any suggestions yet." })); return; }
    box.appendChild(el("ul", { class: "stack", style: "gap:.75rem;list-style:none;padding:0" }, r.data.map(function (x) {
      var kids = [el("strong", { text: x.target_name }), " · " + x.topics.map(function (t) { return TOPIC[t]; }).join(", "),
        el("br"), el("span", { class: "cc-muted", text: "Sent " + when(x.created_at) + " · " + STATUS[x.status] })];
      if (x.review_note) kids.push(el("br"), el("span", { text: "Moderator's note: " + x.review_note }));
      if (x.status === "pending") kids.push(el("br"), el("button", { type: "button", class: "btn btn-secondary", text: "Withdraw", onclick: async function () {
        await sb.from("cinema_updates").update({ status: "withdrawn" }).eq("id", x.id); renderMine(); } }));
      return el("li", { class: "panel" }, kids);
    })));
  }

  // ------------------------------------------------------------ moderators' queue
  async function renderQueue() {
    var box = root.querySelector("[data-up-queue]"); if (!box) return;
    box.textContent = "";
    if (!me.profile || me.profile.role === "member") { box.appendChild(el("p", { class: "cc-muted", text: "Sign in as a moderator to review member suggestions." })); return; }
    var filter = root.querySelector("[data-up-filter]");
    var st = filter ? filter.value : "pending";
    var r = await sb.from("cinema_updates").select("*, author:profiles!cinema_updates_author_id_fkey(display_name)")
      .eq("status", st).order("created_at").limit(200);
    if (r.error) { box.textContent = "The suggestions couldn't be loaded: " + r.error.message; return; }
    if (!r.data.length) { box.appendChild(el("p", { class: "cc-muted", text: "Nothing here." })); return; }
    r.data.forEach(function (x) {
      var note = el("textarea", { rows: "2", maxlength: "1000", "aria-label": "Note to the member" }); note.value = x.review_note || "";
      var link = x.target_type === "new" ? null : el("a", { href: (x.target_type === "record" ? "cinemas/" : x.target_type === "archive" ? "archive/" : "leads/") + x.target_id + ".html", text: "open the page" });
      var src = x.source_url ? el("a", { href: x.source_url, rel: "noopener nofollow ugc", target: "_blank", text: x.source_url }) : null;
      function act(s) { return async function () {
        var u = await sb.from("cinema_updates").update({ status: s, review_note: note.value.trim() || null }).eq("id", x.id);
        if (u.error) alertBox.textContent = u.error.message; else renderQueue(); }; }
      var alertBox = el("p", { class: "cc-muted", role: "status" });
      box.appendChild(el("article", { class: "panel stack", style: "gap:.5rem" }, [
        el("h3", { class: "cc-h2" }, [x.target_name + " ", el("span", { class: "cc-muted", text: "(" + KIND[x.target_type] + ")" })]),
        el("p", { class: "cc-muted" }, ["From " + (x.author ? x.author.display_name : "a member") + " · " + when(x.created_at) + " · " + BASIS[x.basis] +
          (x.credit_me ? " · wants credit" : "") + (link ? " · " : ""), link]),
        el("p", { text: "About: " + x.topics.map(function (t) { return TOPIC[t]; }).join(", ") }),
        el("p", { style: "white-space:pre-wrap", text: x.details }),
        (x.address || x.locality || x.state) ? el("p", { text: "Address given: " + [x.address, x.locality, x.state].filter(Boolean).join(", ") }) : null,
        src || x.source_note ? el("p", {}, ["Source: ", src, src && x.source_note ? " · " : "", x.source_note || ""]) : null,
        el("div", { class: "field" }, [note]),
        el("div", { class: "btn-row" }, [
          el("button", { type: "button", class: "btn btn-primary", text: "Accept", onclick: act("accepted") }),
          el("button", { type: "button", class: "btn btn-secondary", text: "Needs more information", onclick: act("needs_info") }),
          el("button", { type: "button", class: "btn btn-secondary", text: "Decline", onclick: act("declined") }),
          x.status === "accepted" ? el("button", { type: "button", class: "btn btn-secondary", text: "Mark applied", onclick: act("applied") }) : null]),
        alertBox]));
    });
  }
  // Editors download accepted suggestions as a file for the staging workflow (tools/import_member_updates.py).
  async function download() {
    var r = await sb.from("cinema_updates").select("*, author:profiles!cinema_updates_author_id_fkey(display_name)").eq("status", "accepted").order("created_at");
    if (r.error) return;
    var out = r.data.map(function (x) { var y = Object.assign({}, x); y.author_name = x.credit_me && x.author ? x.author.display_name : null; delete y.author; delete y.author_id; return y; });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: "application/json" }));
    a.download = "accepted-member-updates-" + new Date().toISOString().slice(0, 10) + ".json";
    document.body.appendChild(a); a.click(); a.remove();
  }

  function refresh() {
    if (mode === "form") renderMine();
    if (mode === "moderation") renderQueue();
  }
  if (mode === "form") wireForm();
  if (mode === "moderation") {
    var f = root.querySelector("[data-up-filter]"); if (f) f.addEventListener("change", renderQueue);
    var d = root.querySelector("[data-up-download]"); if (d) d.addEventListener("click", download);
  }
  loadMe().then(refresh);
  sb.auth.onAuthStateChange(function () { loadMe().then(refresh); });
})();
