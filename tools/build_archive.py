#!/usr/bin/env python3
"""Build approved archive listings (Phase C, verification levels C and D).

Archive listings are records an editor has approved: identity confirmed, an original summary approved,
and at least one source opened and checked. They sit between the genuine records and the research leads.
  input   assets/data/archive-listings.json  (exported from the editorial staging database; never edited by hand)
  output  archive/<id>.html                   one page per listing
          explore.html                        list between <!-- ARCHIVE-RESULTS:START --> and <!-- ARCHIVE-RESULTS:END -->
          index.html                          state tile counts (records, archive listings, research leads)
Rules carried through: level C may show an address labelled provisional; level D never shows an address;
no listing gets a map pin; only checked sources are linked; no excerpts or images.
Run after tools/build_leads.py (tools/build_genuine.py runs both).
"""
import glob, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
E = html.escape
STATE_NAME = {"QLD": "Queensland", "NSW": "New South Wales", "VIC": "Victoria", "WA": "Western Australia", "SA": "South Australia",
              "TAS": "Tasmania", "NT": "Northern Territory", "ACT": "Australian Capital Territory"}
APPROVED = "26 November 2026"

raw = open("assets/map/cinema-sites.js", encoding="utf-8").read()
SITES = json.loads(raw[raw.index("window.APA_SITES = ") + 19:].strip().rstrip(";"))["sites"]
LEADS = [l for f in sorted(glob.glob("assets/data/leads-*.json")) for l in json.load(open(f, encoding="utf-8"))]
ARCH = json.load(open("assets/data/archive-listings.json", encoding="utf-8")) if os.path.exists("assets/data/archive-listings.json") else []
ids = [a["id"] for a in ARCH]
assert len(ids) == len(set(ids)), "duplicate archive ids"
assert not set(ids) & ({s["id"] for s in SITES} | {l["id"] for l in LEADS}), "archive id clashes with a record or lead"
for a in ARCH:
    assert a["level"] in ("C", "D") and a["summary"] and a["sources"], a["id"]
    assert a["level"] == "C" or "address" not in a, f"{a['id']}: level D must not carry an address"
    assert not any(k in a for k in ("lat", "lon", "loc")), f"{a['id']}: archive listings have no coordinates"

INFO = '<path d="M12 8v5M12 16.5h.01"/><circle cx="12" cy="12" r="9.5"/>'
def svg(p):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true" focusable="false">' + p + "</svg>")
BADGE = {"C": ("b-prelim", "Archive listing, address provisional"), "D": ("b-unknown", "Archive listing, place only")}
def badge(level):
    c, t = BADGE[level]
    return f'<span class="badge {c}"><span class="badge-ico">{svg(INFO)}</span>{t}</span>'
def norm(t):
    t = (t or "").lower().replace("&", " and ")
    t = re.sub(r"[’'`]", "", t)
    t = re.sub(r"[àáâãäå]", "a", t); t = re.sub(r"[èéêë]", "e", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()
def year(a):
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b", a["summary"])
    return int(m.group(1)) if m else None
def era(y):
    if y is None: return "unknown"
    return "pre1930" if y < 1930 else "1930s40s" if y < 1950 else "1950s60s" if y < 1970 else "1970s80s" if y < 1990 else "1990on"

# ---------------------------------------------------------------- page shell (same as record and lead pages)
research = open("research.html", encoding="utf-8").read()
pre = research[:research.index("<main")]
post = research[research.index("</main>") + len("</main>"):]
def rebase(fragment):
    def fix(m):
        attr, q, url = m.group(1), m.group(2), m.group(3)
        if re.match(r"^(https?:|mailto:|tel:|#|data:|/|\.\./)", url) or url == "": return m.group(0)
        return f'{attr}={q}{"../" if url == "./" else "../" + url}{q}'
    return re.sub(r'\b(href|src)=(["\'])([^"\']*)\2', fix, fragment)
def shell(title, desc):
    p = re.sub(r"<title>.*?</title>", f"<title>{E(title)}</title>", pre, count=1, flags=re.S)
    p = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{E(desc)}">', p, count=1)
    p = p.replace('<body data-page="research">', '<body data-page="record">')
    p = re.sub(r'<link rel="stylesheet" href="assets/vendor/leaflet/[^"]+">\n?', "", p)
    p = re.sub(r'(<a href="explore.html")>', r'\1 aria-current="page">', p, count=1)
    p = re.sub(r'(<li><a href="research.html") aria-current="page"', r"\1", p)
    q = post
    for pat in (r'<script src="assets/vendor/leaflet/[^"]+"></script>\n?', r'<script src="assets/map/[^"]+"></script>\n?',
                r'<script src="assets/map\.js[^"]*"></script>\n?', r'<script src="assets/map-loader\.js[^"]*"></script>\n?'):
        q = re.sub(pat, "", q)
    return rebase(p), rebase(q)

os.makedirs("archive", exist_ok=True)
for f in os.listdir("archive"):
    if f.endswith(".html"): os.remove(os.path.join("archive", f))
for a in ARCH:
    sn = STATE_NAME[a["state"]]
    where = ", ".join(x for x in (a["locality"], a["state"]) if x)
    p, q = shell(f"{a['name']}, {a['locality'] or sn} · Film Cinemas Australia", f"{a['name']} ({where}): an archive listing in Film Cinemas Australia, with its checked sources.")
    lede = (f'<p class="lede">{E(a["address"])}, {E(where)}</p><p class="cite-meta">Address provisional: the exact property has not been verified.</p>'
            if a.get("address") else f'<p class="lede">{E(where)}</p>')
    srcs = "".join(f'<li><a href="{E(s["url"])}" rel="noopener">{E(s["title"])}</a></li>' for s in a["sources"])
    detail = ("The address comes from the checked sources, but which property it was has not yet been confirmed, so treat it as provisional. "
              if a["level"] == "C" and a.get("address") else
              "The checked sources confirm the venue and its town or suburb. Its street address has not been verified, so it is not shown. " if a["level"] == "D" else
              "The checked sources confirm the venue and its street; the street number has not been verified, so it is not shown. ")
    main = f'''<main id="main" tabindex="-1">
<section class="record-head" aria-labelledby="rec-title"><div class="wrap" style="grid-template-columns:1fr">
  <div class="stack">
    <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../index.html">Home</a></li><li><a href="../explore.html?state={a["state"].lower()}">Explore cinemas</a></li><li aria-current="page">{E(a["name"])}</li></ol></nav>
    <p class="eyebrow">Archive listing · {E(sn)}</p>
    <h1 id="rec-title">{E(a["name"])}</h1>
    {lede}
    <dl class="rec-keyfacts">
      <div><dt>Verification</dt><dd>{badge(a["level"])}</dd></div>
      <div><dt>Location</dt><dd>Not on the map</dd></div>
    </dl>
    <div class="btn-row rec-actions"><a class="btn btn-secondary" href="../explore.html?state={a["state"].lower()}">More in {E(sn)}</a><a class="btn btn-secondary" href="../share.html">Share a memory or correction</a></div>
  </div>
</div></section>
<div class="wrap rec-body">
  <section class="rec-notes" aria-labelledby="how-title">
    <h2 id="how-title" class="visually-hidden">How sure we are</h2>
    <div class="notice n-info"><p><strong>{E(a["notice"])}</strong></p>
    <p>{detail}Only verified properties get a map pin, so this listing is not on the map.</p></div>
  </section>
  <article class="site-rec rec-article" aria-labelledby="rec-title" data-archive-id="{E(a["id"])}">
    <h2>About this listing</h2>
    <p>{E(a["summary"])}</p>
    <h2>Sources</h2>
    <p>Each source below was opened and checked by Film Cinemas Australia before this listing was approved.</p>
    <ul>{srcs}</ul>
  </article>
  <p class="cite-meta rec-meta">Archive ID <code>{E(a["id"])}</code> · verification level {a["level"]} · approved {APPROVED}</p>
</div>
</main>'''
    open(f"archive/{a['id']}.html", "w", encoding="utf-8").write(p + main + q)

# ---------------------------------------------------------------- Explore
items = []
for a in sorted(ARCH, key=lambda x: (x["name"].lower(), x["locality"].lower())):
    y = year(a)
    search = norm(" ".join([a["name"], a.get("address", ""), a["locality"], a["state"], STATE_NAME[a["state"]], "archive listing"]))
    items.append(f'''<li class="gx-item" data-id="{E(a["id"])}" data-state="{a["state"].lower()}" data-status="closed" data-evidence="archive" data-loc="notmapped" data-era="{era(y)}" data-search="{E(search)}">
  <h3 class="gx-name"><a href="archive/{E(a["id"])}.html">{E(a["name"])}</a></h3>
  <p class="gx-place">{E(a["locality"])}, {E(a["state"])} · archive listing, level {a["level"]}</p>
  <p class="gx-badges">{badge(a["level"])}<span class="gx-loc">Not on the map</span></p>
</li>''')
block = "<!-- ARCHIVE-RESULTS:START -->\n<ul class=\"gx-list\" data-list>\n" + "\n".join(items) + "\n</ul>\n<!-- ARCHIVE-RESULTS:END -->"
ex = open("explore.html", encoding="utf-8").read()
if "<!-- ARCHIVE-RESULTS:START -->" in ex:
    ex = re.sub(r"<!-- ARCHIVE-RESULTS:START -->.*?<!-- ARCHIVE-RESULTS:END -->", lambda m: block, ex, flags=re.S)
else:
    ex = ex.replace("<!-- LEAD-RESULTS:START -->", block + "\n<!-- LEAD-RESULTS:START -->", 1)
if 'value="archive"' not in ex:
    ex = ex.replace('<label class="choice"><input type="checkbox" name="evidence" value="lead" checked>',
                    '<label class="choice"><input type="checkbox" name="evidence" value="archive" checked> Archive listing (sources checked, address provisional or not shown)</label><label class="choice"><input type="checkbox" name="evidence" value="lead" checked>', 1)
total = len(SITES) + len(ARCH) + len(LEADS)
ex = re.sub(r'<p class="result-count" role="status" aria-live="polite" data-count>[^<]*</p>',
            f'<p class="result-count" role="status" aria-live="polite" data-count>{total} cinemas</p>', ex, count=1)
ex = re.sub(r"Search and filter the archive's (?:genuine cinema records|\d+ cinema records)[^<]*</p>",
            f"Search and filter the archive's {len(SITES)} cinema records, {len(ARCH)} archive listings and {len(LEADS)} research leads: names and former names, towns and suburbs, states and status today. Every record and archive listing shows its checked sources and how sure we are. Research leads are unverified and are labelled as such.</p>", ex, count=1)
open("explore.html", "w", encoding="utf-8").write(ex)

# ---------------------------------------------------------------- homepage state tiles
idx = open("index.html", encoding="utf-8").read()
def tile(m):
    code = re.search(r"<strong>([A-Z]+)</strong>", m.group(0)).group(1)
    g = sum(1 for s in SITES if s["state"] == code); a = sum(1 for x in ARCH if x["state"] == code); n = sum(1 for l in LEADS if l["state"] == code)
    parts = ([f"{g} record{'s' if g != 1 else ''}"] if g else []) + ([f"{a} archive listing{'s' if a != 1 else ''}"] if a else []) + ([f"{n} research lead{'s' if n != 1 else ''}"] if n else [])
    inner = re.sub(r'<span class="st-count">[^<]*</span>', f'<span class="st-count">{" · ".join(parts) if parts else "No records yet"}</span>', m.group(2))
    return (f'<a class="state-tile" href="explore.html?state={code.lower()}">' + inner + "</a>") if parts else ('<div class="state-tile st-empty">' + inner + "</div>")
idx = re.sub(r'<(a|div) class="state-tile[^"]*"[^>]*>(.*?)</(?:a|div)>(?=<a class="state-tile|<div class="state-tile|</div>)', tile, idx, flags=re.S)
open("index.html", "w", encoding="utf-8").write(idx)
print(f"{len(ARCH)} archive listing pages written to archive/ (" + ", ".join(f"{k} {sum(1 for a in ARCH if a['state'] == k)}" for k in STATE_NAME if any(a['state'] == k for a in ARCH)) + ")")
