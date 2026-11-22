/* Real-site cinema map (Rounds 4 and 5). Leaflet with a self-hosted Natural Earth basemap, so the map makes no requests
   to any tile server. Site data comes from assets/map/cinema-sites.js, built from src/brisbane.py and src/nswvic.py. */
(function () {
  "use strict";
  if (!window.L || !window.APA_SITES || !window.APA_BASEMAP) return;
  var L = window.L, DATA = window.APA_SITES, BASE = window.APA_BASEMAP;
  var AUSTRALIA = [[-44.2, 112.5], [-10.2, 154.2]];
  var BRISBANE = [[-27.56, 152.93], [-27.38, 153.2]];
  // Sydney and Melbourne views are fitted to the mapped sites themselves, with a margin, so no bounds are invented.
  function regionBounds(r) {
    if (r === "brisbane") return BRISBANE;
    var pts = DATA.sites.filter(function (s) { return s.region.toLowerCase() === r && s.loc.kind !== "none"; });
    if (!pts.length) return AUSTRALIA;
    var la = pts.map(function (s) { return s.loc.lat; }), lo = pts.map(function (s) { return s.loc.lon; });
    var pad = 0.03;
    return [[Math.min.apply(0, la) - pad, Math.min.apply(0, lo) - pad], [Math.max.apply(0, la) + pad, Math.max.apply(0, lo) + pad]];
  }
  var REGION_NAME = { brisbane: "Brisbane", sydney: "Sydney", melbourne: "Melbourne", "regional queensland": "regional Queensland", "regional nsw": "regional New South Wales" };

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

  function markerHtml(s) {
    return '<span class="rm-pin rm-' + s.status + ' rm-loc-' + s.loc.kind + '" aria-hidden="true"><span class="rm-shape"></span></span>';
  }

  function popupHtml(s) {
    var evts = s.events.slice(0, 4).map(function (e) { return "<li><strong>" + esc(e[0]) + "</strong> " + esc(e[1]) + "</li>"; }).join("");
    var more = s.events.length > 4 ? '<li class="rm-more">' + (s.events.length - 4) + " more in the research record</li>" : "";
    var src = s.sources.slice(0, 3).map(function (x) { return '<li><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.label) + "</a></li>"; }).join("");
    var conflict = s.conflicts.length ? '<p class="rm-conflict"><span class="badge b-conflict">Sources disagree</span> ' + esc(s.conflicts[0]) + (s.conflicts.length > 1 ? " (+" + (s.conflicts.length - 1) + " more)" : "") + "</p>" : "";
    return '<div class="rm-pop">' +
      '<p class="rm-kicker">Real site · ' + esc(s.statusLabel) + "</p>" +
      "<h3>" + esc(s.name) + "</h3>" +
      (s.aliases.length ? '<p class="rm-alias">Also known as ' + esc(s.aliases.join(", ")) + "</p>" : "") +
      '<p class="rm-addr">' + esc(s.address) + ", " + esc(s.suburb) + "</p>" +
      '<p class="rm-status">' + esc(s.statusNote) + "</p>" +
      (evts ? '<ul class="rm-events">' + evts + more + "</ul>" : "") +
      '<dl class="rm-conf"><div><dt>Location</dt><dd>' + esc(s.locLabel) + "</dd></div><div><dt>Evidence</dt><dd>" + esc(s.evidenceLabel) + "</dd></div></dl>" +
      '<p class="rm-locnote">' + esc(s.loc.note) + "</p>" + conflict +
      '<p class="rm-srch">Sources</p><ul class="rm-sources">' + src + "</ul>" +
      '<p><a class="rm-record" href="research.html#site-' + esc(s.id) + '">Full research record</a></p></div>';
  }

  function init(el) {
    var map = L.map(el, { zoomSnap: 0.5, minZoom: 3, maxZoom: 16, attributionControl: true, worldCopyJump: false, scrollWheelZoom: false });
    map.attributionControl.setPrefix(false);
    map.attributionControl.addAttribution('Basemap: <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener">Natural Earth</a> (public domain), simplified. Not a street map. Map library: <a href="https://leafletjs.com/" target="_blank" rel="noopener">Leaflet</a>');
    var r = L.svg({ padding: 0.5 });
    L.geoJSON(BASE.layers.land, { renderer: r, interactive: false, style: { className: "rm-land", weight: 1 } }).addTo(map);
    L.geoJSON(BASE.layers.states, { renderer: r, interactive: false, style: { className: "rm-state", weight: 1, dashArray: "4 4", fill: false } }).addTo(map);
    L.geoJSON(BASE.layers.rivers, { renderer: r, interactive: false, style: { className: "rm-river", weight: 2, fill: false } }).addTo(map);

    var capitals = L.layerGroup(BASE.layers.places.map(function (f) {
      var c = f.geometry.coordinates;
      return L.marker([c[1], c[0]], { interactive: false, keyboard: false, icon: L.divIcon({ className: "rm-label rm-label-city", html: "<span>" + esc(f.properties.name) + "</span>", iconSize: [0, 0] }) });
    }));
    var suburbs = L.layerGroup(DATA.suburbs.map(function (s) {
      return L.marker([s.lat, s.lon], { interactive: false, keyboard: false, icon: L.divIcon({ className: "rm-label rm-label-suburb", html: "<span>" + esc(s.name) + "</span>", iconSize: [0, 0] }) });
    }));
    // Zoomed in, Sydney and Melbourne keep their city label (Brisbane has suburb labels instead, which sit clear of its markers).
    var cityNear = L.layerGroup(BASE.layers.places.filter(function (f) { return f.properties.name !== "Brisbane"; }).map(function (f) {
      var c = f.geometry.coordinates;
      return L.marker([c[1], c[0]], { interactive: false, keyboard: false, icon: L.divIcon({ className: "rm-label rm-label-city rm-label-near", html: "<span>" + esc(f.properties.name) + "</span>", iconSize: [0, 0] }) });
    }));
    function show(layer, on) { if (on && !map.hasLayer(layer)) map.addLayer(layer); if (!on && map.hasLayer(layer)) map.removeLayer(layer); }
    function labels() {
      var z = map.getZoom();
      show(capitals, z < 10); show(cityNear, z >= 10); show(suburbs, z >= 12);
    }

    // Popups fit small maps (phones): narrower than the map, scrolling inside when tall.
    function popOpts() {
      var w = el.clientWidth || 360, h = el.clientHeight || 440, mw = Math.max(200, Math.min(320, w - 80));
      return { maxWidth: mw, minWidth: Math.min(240, mw), maxHeight: Math.max(220, h - 110), autoPanPadding: [16, 16], className: "rm-popup" };
    }
    function refitPopups() { var o = popOpts(); cluster.eachLayer(function (m) { var p = m.getPopup(); if (p) L.Util.extend(p.options, o); }); }
    map.on("resize", refitPopups);

    var cluster = L.markerClusterGroup({
      maxClusterRadius: 44, spiderfyOnMaxZoom: true, showCoverageOnHover: false, zoomToBoundsOnClick: true,
      iconCreateFunction: function (c) {
        var n = c.getChildCount();
        return L.divIcon({ className: "rm-cluster", html: '<span aria-hidden="true">' + n + "</span>", iconSize: [44, 44] });
      }
    });
    DATA.sites.forEach(function (s) {
      if (s.loc.kind === "none") return;
      var approx = s.loc.kind === "site" ? "" : ", approximate location";
      var m = L.marker([s.loc.lat, s.loc.lon], {
        icon: L.divIcon({ className: "rm-marker", html: markerHtml(s), iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -12] }),
        title: s.name + " (" + s.statusLabel + approx + ")", alt: s.name, riseOnHover: true
      });
      m.bindPopup(popupHtml(s), popOpts());
      m.on("add", function () { var ic = m.getElement(); if (ic) { ic.setAttribute("aria-label", s.name + ", " + s.suburb + ". " + s.statusLabel + approx + ". Open details"); ic.setAttribute("role", "button"); } });
      cluster.addLayer(m);
    });
    // Cluster icons need an accessible name too: they are focusable and open on Enter.
    cluster.on("animationend spiderfied", nameClusters);
    map.on("zoomend moveend", function () { labels(); setTimeout(nameClusters, 0); });
    function nameClusters() {
      el.querySelectorAll(".rm-cluster").forEach(function (ic) {
        var n = ic.textContent.trim();
        ic.setAttribute("role", "button"); ic.setAttribute("tabindex", "0");
        ic.setAttribute("aria-label", "Group of " + n + " cinema sites. Select to zoom in");
      });
    }
    map.addLayer(cluster);

    var start = el.getAttribute("data-start") === "australia" ? AUSTRALIA : BRISBANE;
    map.fitBounds(start);
    labels(); setTimeout(nameClusters, 0);

    var fig = el.closest("[data-real-map-wrap]") || document;
    var status = fig.querySelector("[data-map-status]");
    function say(t) { if (status) status.textContent = t; }
    Array.prototype.forEach.call(fig.querySelectorAll("[data-zoom]"), function (b) {
      var r = b.getAttribute("data-zoom");
      b.addEventListener("click", function () {
        map.closePopup(); map.flyToBounds(regionBounds(r), { duration: 0.6 });
        var n = DATA.sites.filter(function (s) { return s.region.toLowerCase() === r && s.loc.kind !== "none"; }).length;
        say("Map zoomed to " + REGION_NAME[r] + ". " + n + " mapped sites in this area.");
      });
    });
    var sa = fig.querySelector("[data-show-australia]");
    if (sa) sa.addEventListener("click", function () { map.closePopup(); map.flyToBounds(AUSTRALIA, { duration: 0.6 }); say("Map shows all of Australia. Nearby sites are grouped into clusters."); });
    // Scroll-wheel zoom only once the visitor has engaged with the map, so the page still scrolls past it.
    map.on("focus click", function () { map.scrollWheelZoom.enable(); });
    map.on("blur mouseout", function () { map.scrollWheelZoom.disable(); });
    // A reduced-motion preference turns the fly animation into a jump.
    try { if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { map.flyToBounds = function (b) { map.fitBounds(b); }; } } catch (e) { /* ignore */ }
    el._apaMap = map;
    // Maps inside a hidden panel (the Explore map view) need a size refresh when shown.
    var wasHidden = el.clientWidth === 0;
    if ("ResizeObserver" in window) new ResizeObserver(function () {
      if (el.clientWidth === 0) { wasHidden = true; return; }
      map.invalidateSize();
      if (wasHidden) { wasHidden = false; map.fitBounds(start); }
    }).observe(el);
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-real-map]"), init);
})();
