/* Film Cinemas Australia: load the map only when it is needed (M-11).
   Leaflet, the marker-cluster plugin, the Natural Earth basemap (about 300 KB) and the cinema dataset are fetched
   when a map comes within 300 px of the screen, when the page is opened at #map or with ?focus=<id>,
   or when a hidden map (Explore's map view) is shown. Until then the page paints without them.
   All files are self-hosted; versions are pinned by file name and the ?v= stamp. */
(function () {
  "use strict";
  var maps = document.querySelectorAll("[data-real-map]");
  if (!maps.length) return;
  var V = "1795740000";
  var base = (document.currentScript && document.currentScript.src || "").replace(/assets\/map-loader\.js.*$/, "");
  var CSS = ["assets/vendor/leaflet/leaflet.css", "assets/vendor/leaflet/MarkerCluster.css"];
  var JS = ["assets/vendor/leaflet/leaflet.js", "assets/vendor/leaflet/leaflet.markercluster.js", "assets/map/basemap-au.js",
            "assets/map/cinema-sites.js?v=" + V, "assets/map/archive-pins.js?v=" + V, "assets/map.js?v=" + V];
  var started = false;

  function css(href) {
    if (document.querySelector('link[href="' + base + href + '"]')) return;
    var l = document.createElement("link"); l.rel = "stylesheet"; l.href = base + href; document.head.appendChild(l);
  }
  function js(i) {
    if (i >= JS.length) return;
    var s = document.createElement("script"); s.src = base + JS[i];
    s.onload = function () { js(i + 1); };
    s.onerror = function () {
      Array.prototype.forEach.call(maps, function (m) {
        m.innerHTML = '<p class="notice n-warn" style="margin:1rem">The map could not be loaded. Every cinema is listed in <a href="' + base + 'explore.html">Explore cinemas</a>.</p>';
      });
    };
    document.body.appendChild(s);
  }
  function load() {
    if (started) return; started = true;
    CSS.forEach(css); js(0);
  }

  var p = new URLSearchParams(window.location.search);
  if (p.get("focus") || window.location.hash === "#map" || p.get("view") === "map" || window.location.hash === "#view-map") { load(); return; }
  if (!("IntersectionObserver" in window)) { load(); return; }
  var io = new IntersectionObserver(function (entries) {
    if (entries.some(function (e) { return e.isIntersecting; })) { io.disconnect(); load(); }
  }, { rootMargin: "300px 0px" });
  Array.prototype.forEach.call(maps, function (m) { io.observe(m); });
  window.addEventListener("hashchange", function () { if (window.location.hash === "#map") load(); });
})();
