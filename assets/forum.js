/* Cinema Community forums. Talks to Supabase (config in assets/forum-config.js).
   All text from the database is inserted with textContent, never as HTML. */
(function () {
  "use strict";
  var cfg = window.FCA_FORUM || {};
  var root = document.querySelector("[data-forum]");
  if (!root) return;
  var mode = root.getAttribute("data-forum");
  var off = document.querySelector("[data-forum-off]");

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
    try { return new Date(iso).toLocaleString("en-AU", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }); }
    catch (e) { return iso; }
  }
  function say(box, text, kind) {
    box.hidden = false; box.className = "notice " + (kind === "error" ? "n-alert" : kind === "ok" ? "n-ok" : "n-info");
    box.textContent = text;
  }
  function param(k) { return new URLSearchParams(location.search).get(k); }

  if (!cfg.url || !cfg.anonKey || !window.supabase) {
    if (off) off.hidden = false;
    root.querySelectorAll("form button, form input, form select, form textarea").forEach(function (x) { x.disabled = true; });
    var l = root.querySelector("[data-list]"); if (l) l.textContent = "The forums open soon.";
    return;
  }
  var sb = window.supabase.createClient(cfg.url, cfg.anonKey);
  var me = { user: null, profile: null };
  var authBox = document.querySelector("[data-auth]");

  async function loadMe() {
    var s = await sb.auth.getSession();
    me.user = s.data.session ? s.data.session.user : null;
    me.profile = null;
    if (me.user) {
      var p = await sb.from("profiles").select("id, display_name, role").eq("id", me.user.id).maybeSingle();
      me.profile = p.data || null;
    }
    renderAuth();
    document.querySelectorAll("[data-needs-member]").forEach(function (n) { n.hidden = !me.profile; });
    document.querySelectorAll("[data-needs-signin]").forEach(function (n) { n.hidden = !!me.profile; });
  }

  function renderAuth() {
    if (!authBox) return;
    authBox.textContent = "";
    var msg = el("p", { class: "notice", hidden: true, role: "status" });
    if (!me.user) {
      var email = el("input", { type: "email", id: "fm-email", required: true, autocomplete: "email" });
      var form = el("form", { class: "stack fm-auth", onsubmit: async function (e) {
        e.preventDefault();
        var r = await sb.auth.signInWithOtp({ email: email.value.trim(), options: { emailRedirectTo: location.href.split("#")[0] } });
        if (r.error) say(msg, "We couldn't send the link: " + r.error.message, "error");
        else say(msg, "Check your email for a sign-in link. It works once and expires after an hour.", "ok");
      } }, [
        el("h2", { class: "cc-h2", text: "Sign in or join" }),
        el("p", { class: "cc-muted", text: "Free member account. We email you a sign-in link, so there's no password to remember." }),
        el("div", { class: "field" }, [el("label", { for: "fm-email", text: "Email address" }), email]),
        el("div", { class: "btn-row" }, [el("button", { type: "submit", class: "btn btn-primary", text: "Email me a sign-in link" })]),
        msg
      ]);
      authBox.appendChild(form);
      return;
    }
    if (!me.profile) {
      var name = el("input", { type: "text", id: "fm-name", required: true, minlength: "2", maxlength: "40", autocomplete: "nickname" });
      var age = el("input", { type: "checkbox", id: "fm-age", required: true });
      var rules = el("input", { type: "checkbox", id: "fm-rules", required: true });
      var f2 = el("form", { class: "stack fm-auth", onsubmit: async function (e) {
        e.preventDefault();
        var r = await sb.from("profiles").insert({ id: me.user.id, display_name: name.value.trim(), age_16_confirmed: age.checked });
        if (r.error) say(msg, r.error.code === "23505" ? "That display name is taken. Try another." : "We couldn't save your profile: " + r.error.message, "error");
        else loadMe().then(refresh);
      } }, [
        el("h2", { class: "cc-h2", text: "Set up your member profile" }),
        el("div", { class: "field" }, [el("label", { for: "fm-name", text: "Display name (shown on your posts)" }), name,
          el("span", { class: "cc-muted", text: "Use a nickname if you prefer. Don't use your email address." })]),
        el("label", { class: "cc-check", for: "fm-age" }, [age, " I am 16 or older"]),
        el("label", { class: "cc-check", for: "fm-rules" }, [rules, " I agree to the ", el("a", { href: "community-guidelines.html", text: "community guidelines and privacy notice" })]),
        el("div", { class: "btn-row" }, [el("button", { type: "submit", class: "btn btn-primary", text: "Create profile" }),
          el("button", { type: "button", class: "btn btn-secondary", text: "Sign out", onclick: signOut })]),
        msg
      ]);
      authBox.appendChild(f2);
      return;
    }
    var bits = [el("span", {}, ["Signed in as ", el("strong", { text: me.profile.display_name })])];
    if (me.profile.role !== "member") bits.push(el("a", { href: "moderation.html", text: "Moderation" }));
    bits.push(el("button", { type: "button", class: "btn btn-secondary", text: "Sign out", onclick: signOut }));
    authBox.appendChild(el("div", { class: "fm-whoami" }, bits));
  }
  async function signOut() { await sb.auth.signOut(); await loadMe(); refresh(); }

  // ------------------------------------------------------------ thread list
  var cats = [];
  async function loadCats() {
    var r = await sb.from("forum_categories").select("id, slug, name, description").order("sort");
    cats = r.data || [];
    var sel = document.getElementById("fm-cat");
    if (sel && !sel.options.length) cats.forEach(function (c) { sel.appendChild(el("option", { value: String(c.id), text: c.name })); });
    var chips = document.querySelector("[data-cats]");
    if (chips && !chips.children.length) {
      var cur = param("cat") || "all";
      [{ slug: "all", name: "All topics" }].concat(cats).forEach(function (c) {
        chips.appendChild(el("a", { class: "cc-chip fm-chip", href: c.slug === "all" ? "forums.html" : "forums.html?cat=" + c.slug, "aria-current": c.slug === cur ? "page" : null, text: c.name }));
      });
    }
  }
  function catName(id) { var c = cats.filter(function (x) { return x.id === id; })[0]; return c ? c.name : ""; }

  async function renderList() {
    var list = root.querySelector("[data-list]");
    list.textContent = "Loading discussions…";
    var q = sb.from("forum_threads").select("id, title, category_id, cinema_name, reply_count, last_post_at, status, author:profiles(display_name)")
      .neq("status", "deleted").order("last_post_at", { ascending: false }).limit(60);
    var slug = param("cat");
    var cat = cats.filter(function (c) { return c.slug === slug; })[0];
    if (cat) q = q.eq("category_id", cat.id);
    var r = await q;
    list.textContent = "";
    if (r.error) { list.textContent = "The discussions couldn't be loaded. Please try again later."; return; }
    if (!r.data.length) { list.appendChild(el("p", { class: "empty", text: "No discussions here yet. Start the first one." })); return; }
    var ul = el("ul", { class: "fm-threads" });
    r.data.forEach(function (t) {
      var meta = [catName(t.category_id), t.cinema_name, "by " + (t.author ? t.author.display_name : "member"),
        t.reply_count + (t.reply_count === 1 ? " reply" : " replies"), "last activity " + when(t.last_post_at)].filter(Boolean).join(" · ");
      ul.appendChild(el("li", { class: "fm-thread" }, [
        el("a", { href: "thread.html?id=" + t.id, class: "fm-thread-title", text: t.title }),
        t.status === "pending" ? el("span", { class: "badge cc-prop", text: "Waiting for a moderator" }) : null,
        t.status === "hidden" ? el("span", { class: "badge cc-off", text: "Hidden by a moderator" }) : null,
        el("span", { class: "cc-muted", text: meta })
      ]));
    });
    list.appendChild(ul);
  }

  function wireNewThread() {
    var f = document.getElementById("fm-new");
    if (!f || f.dataset.wired) return; f.dataset.wired = "1";
    var msg = f.querySelector("[data-msg]");
    f.addEventListener("submit", async function (e) {
      e.preventDefault();
      var btn = f.querySelector("button[type=submit]"); btn.disabled = true;
      var row = { category_id: Number(f.elements.category.value), title: f.elements.title.value.trim(), body: f.elements.body.value.trim(),
                  cinema_name: f.elements.cinema.value.trim() || null };
      var r = await sb.from("forum_threads").insert(row).select("id, status").single();
      btn.disabled = false;
      if (r.error) { say(msg, r.error.message.indexOf("check constraint") > -1 ? "Please give a title of at least 5 characters and a message of at least 10." : r.error.message, "error"); return; }
      f.reset();
      say(msg, r.data.status === "pending" ? "Thanks. Your first posts are checked by a moderator before they appear; this usually takes a day or two." : "Posted.", "ok");
      renderList();
    });
  }

  // ------------------------------------------------------------ one thread
  async function renderThread() {
    var id = Number(param("id"));
    var box = root.querySelector("[data-thread]");
    if (!id) { box.textContent = "Discussion not found."; return; }
    var t = await sb.from("forum_threads").select("id, title, body, category_id, cinema_name, status, created_at, edited_at, author_id, author:profiles(display_name)").eq("id", id).maybeSingle();
    box.textContent = "";
    if (t.error || !t.data || t.data.status === "deleted") { box.appendChild(el("p", { class: "empty", text: "This discussion isn't available. It may have been removed." })); return; }
    t = t.data;
    document.title = t.title + " · Forums · Film Cinemas Australia";
    var h = document.getElementById("fm-title"); if (h) h.textContent = t.title;
    var crumb = document.querySelector("[data-crumb]"); if (crumb) crumb.textContent = catName(t.category_id) + (t.cinema_name ? " · " + t.cinema_name : "");
    box.appendChild(postCard("thread", t));
    var p = await sb.from("forum_posts").select("id, body, status, created_at, edited_at, author_id, author:profiles(display_name)").eq("thread_id", id).neq("status", "deleted").order("created_at");
    var replies = el("section", { class: "stack", "aria-label": "Replies" });
    (p.data || []).forEach(function (x) { replies.appendChild(postCard("post", x)); });
    if (!(p.data || []).length) replies.appendChild(el("p", { class: "cc-muted", text: "No replies yet." }));
    box.appendChild(el("h2", { class: "cc-h2", text: "Replies" })); box.appendChild(replies);
    var f = document.getElementById("fm-reply");
    if (f) {
      f.hidden = !(me.profile && t.status === "visible");
      if (!f.dataset.wired) {
        f.dataset.wired = "1";
        var msg = f.querySelector("[data-msg]");
        f.addEventListener("submit", async function (e) {
          e.preventDefault();
          var r = await sb.from("forum_posts").insert({ thread_id: id, body: f.elements.body.value.trim() }).select("status").single();
          if (r.error) { say(msg, r.error.message.indexOf("check constraint") > -1 ? "Replies need at least 2 characters." : r.error.message, "error"); return; }
          f.reset();
          say(msg, r.data.status === "pending" ? "Thanks. Your reply will appear once a moderator has checked it." : "Reply posted.", "ok");
          renderThread();
        });
      }
    }
  }

  function postCard(kind, x) {
    var mine = me.user && x.author_id === me.user.id;
    var head = el("p", { class: "fm-meta" }, [el("strong", { text: x.author ? x.author.display_name : "Member" }), " · " + when(x.created_at) + (x.edited_at ? " · edited" : "")]);
    var art = el("article", { class: "panel fm-post", id: kind + "-" + x.id }, [head]);
    if (x.status === "pending") art.appendChild(el("span", { class: "badge cc-prop", text: "Waiting for a moderator (only you and moderators can see this)" }));
    if (x.status === "hidden") art.appendChild(el("span", { class: "badge cc-off", text: "Hidden by a moderator" }));
    art.appendChild(el("div", { class: "fm-body", text: x.body }));
    var actions = el("div", { class: "fm-actions" });
    if (me.profile && !mine) actions.appendChild(el("button", { type: "button", class: "fm-link", text: "Report", onclick: function () { reportForm(art, kind, x.id); } }));
    if (mine) {
      var del = el("button", { type: "button", class: "fm-link", text: "Delete", onclick: async function () {
        if (del.dataset.armed !== "1") { del.dataset.armed = "1"; del.textContent = "Select again to delete"; return; }
        var tbl = kind === "thread" ? "forum_threads" : "forum_posts";
        var r = await sb.from(tbl).update({ status: "deleted" }).eq("id", x.id);
        if (r.error) { del.textContent = "Couldn't delete"; return; }
        if (kind === "thread") location.href = "forums.html"; else renderThread();
      } });
      actions.appendChild(del);
    }
    if (actions.children.length) art.appendChild(actions);
    return art;
  }

  function reportForm(art, kind, id) {
    if (art.querySelector(".fm-report")) return;
    var reason = el("select", { class: "cc-select", id: "rep-" + kind + id }, [["spam", "Spam or advertising"], ["abuse", "Abusive or harassing"], ["personal-information", "Shares someone's personal information"],
      ["illegal", "Illegal or harmful content"], ["off-topic", "Off-topic"], ["other", "Something else"]].map(function (o) { return el("option", { value: o[0], text: o[1] }); }));
    var detail = el("textarea", { rows: "2", maxlength: "1000", id: "repd-" + kind + id });
    var msg = el("p", { hidden: true, role: "status" });
    var f = el("form", { class: "fm-report stack", onsubmit: async function (e) {
      e.preventDefault();
      var r = await sb.from("forum_reports").insert({ target_type: kind, target_id: id, reason: reason.value, detail: detail.value.trim() || null });
      if (r.error && r.error.code === "23505") say(msg, "You've already reported this. Thank you.", "ok");
      else if (r.error) say(msg, r.error.message, "error");
      else { say(msg, "Thanks. A moderator will look at this.", "ok"); f.querySelector("button").disabled = true; }
    } }, [el("label", { for: "rep-" + kind + id, text: "Why are you reporting this?" }), reason,
          el("label", { for: "repd-" + kind + id, text: "More detail (optional)" }), detail,
          el("div", { class: "btn-row" }, [el("button", { type: "submit", class: "btn btn-secondary", text: "Send report" })]), msg]);
    art.appendChild(f); reason.focus();
  }

  // ------------------------------------------------------------ moderation
  async function renderModeration() {
    var box = root.querySelector("[data-mod]");
    box.textContent = "";
    if (!me.profile || me.profile.role === "member") { box.appendChild(el("p", { class: "empty", text: "This page is for forum moderators. Sign in with a moderator account." })); return; }
    async function act(tbl, id, status) { var r = await sb.from(tbl).update({ status: status }).eq("id", id); if (r.error) alertBox(r.error.message); renderModeration(); }
    function alertBox(t) { box.prepend(el("p", { class: "notice n-alert", role: "alert", text: t })); }
    var th = await sb.from("forum_threads").select("id, title, body, status, created_at, author:profiles(display_name)").in("status", ["pending", "hidden"]).order("created_at");
    var po = await sb.from("forum_posts").select("id, thread_id, body, status, created_at, author:profiles(display_name)").in("status", ["pending", "hidden"]).order("created_at");
    var rp = await sb.from("forum_reports").select("id, target_type, target_id, reason, detail, status, created_at, reporter:profiles(display_name)").eq("status", "open").order("created_at");
    function item(kind, x) {
      var tbl = kind === "thread" ? "forum_threads" : "forum_posts";
      var link = kind === "thread" ? "thread.html?id=" + x.id : "thread.html?id=" + x.thread_id + "#post-" + x.id;
      return el("article", { class: "panel fm-post" }, [
        el("p", { class: "fm-meta" }, [el("strong", { text: (x.author ? x.author.display_name : "Member") }), " · " + kind + " · " + when(x.created_at) + " · " + x.status]),
        x.title ? el("h3", { text: x.title }) : null, el("div", { class: "fm-body", text: x.body }),
        el("div", { class: "btn-row" }, [
          el("button", { type: "button", class: "btn btn-primary", text: "Approve and show", onclick: function () { act(tbl, x.id, "visible"); } }),
          x.status !== "hidden" ? el("button", { type: "button", class: "btn btn-secondary", text: "Hide", onclick: function () { act(tbl, x.id, "hidden"); } }) : null,
          el("a", { class: "btn btn-secondary", href: link, text: "Open" })])]);
    }
    box.appendChild(el("h2", { class: "cc-h2", text: "Waiting or hidden (" + ((th.data || []).length + (po.data || []).length) + ")" }));
    (th.data || []).forEach(function (x) { box.appendChild(item("thread", x)); });
    (po.data || []).forEach(function (x) { box.appendChild(item("post", x)); });
    box.appendChild(el("h2", { class: "cc-h2", text: "Open reports (" + (rp.data || []).length + ")" }));
    (rp.data || []).forEach(function (x) {
      var tbl = x.target_type === "thread" ? "forum_threads" : "forum_posts";
      box.appendChild(el("article", { class: "panel fm-post" }, [
        el("p", { class: "fm-meta" }, [el("strong", { text: x.reason }), " · " + x.target_type + " " + x.target_id + " · reported by " + (x.reporter ? x.reporter.display_name : "member") + " · " + when(x.created_at)]),
        x.detail ? el("div", { class: "fm-body", text: x.detail }) : null,
        el("div", { class: "btn-row" }, [
          el("button", { type: "button", class: "btn btn-primary", text: "Hide the post and close", onclick: async function () {
            await sb.from(tbl).update({ status: "hidden" }).eq("id", x.target_id);
            await sb.from("forum_reports").update({ status: "actioned" }).eq("id", x.id); renderModeration(); } }),
          el("button", { type: "button", class: "btn btn-secondary", text: "Dismiss", onclick: async function () {
            await sb.from("forum_reports").update({ status: "dismissed" }).eq("id", x.id); renderModeration(); } })])]));
    });
  }

  async function refresh() {
    if (mode === "list") { await loadCats(); wireNewThread(); renderList(); }
    if (mode === "thread") { await loadCats(); renderThread(); }
    if (mode === "moderation") renderModeration();
  }
  sb.auth.onAuthStateChange(function () { loadMe().then(refresh); });
  loadMe().then(refresh);
})();
