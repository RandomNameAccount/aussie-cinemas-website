/* Cinema Partners ad spaces. Each element with data-ad-slot="<placement>" keeps its normal content
   unless Supabase returns a live, in-date ad for that placement (see the advertising section of
   supabase/forum_schema.sql). Ads are always labelled Sponsored. Nothing is tracked. */
(function () {
  "use strict";
  var cfg = window.FCA_FORUM || {};
  var slots = document.querySelectorAll("[data-ad-slot]");
  if (!slots.length || !cfg.url || !cfg.anonKey || !window.fetch) return;
  var base = cfg.url.replace(/\/+$/, "") + "/rest/v1/ads";
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text) n.textContent = text; return n; }
  function safe(u) { return typeof u === "string" && /^https:\/\//.test(u) ? u : null; }
  slots.forEach(function (slot) {
    var key = slot.getAttribute("data-ad-slot");
    var now = new Date().toISOString();
    var q = base + "?select=advertiser,headline,body,link_url,image_url&status=eq.live" +
      "&placement=eq." + encodeURIComponent(key) +
      "&starts_at=lte." + encodeURIComponent(now) + "&ends_at=gte." + encodeURIComponent(now);
    fetch(q, { headers: { apikey: cfg.anonKey, Authorization: "Bearer " + cfg.anonKey } })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (ads) {
        if (!ads || !ads.length) return;
        var ad = ads[Math.floor(Math.random() * ads.length)];
        var link = safe(ad.link_url); if (!link) return;
        slot.textContent = "";
        slot.hidden = false;
        slot.classList.add("cc-banner");
        slot.setAttribute("aria-label", "Sponsored");
        var text = el("div", "stack"); text.style.gap = ".4rem";
        text.appendChild(el("span", "badge cc-sp", "Sponsored"));
        text.appendChild(el("strong", null, ad.headline));
        if (ad.body) text.appendChild(el("span", "cc-muted", ad.body));
        text.appendChild(el("span", "cc-muted", "From " + ad.advertiser));
        var img = safe(ad.image_url);
        if (img) { var i = el("img", "cc-ad-img"); i.src = img; i.alt = ""; i.loading = "lazy"; slot.appendChild(i); }
        slot.appendChild(text);
        var a = el("a", "btn btn-secondary", "Visit " + ad.advertiser);
        a.href = link; a.target = "_blank"; a.rel = "sponsored noopener noreferrer";
        slot.appendChild(a);
      })
      .catch(function () { /* keep the normal content */ });
  });
})();
