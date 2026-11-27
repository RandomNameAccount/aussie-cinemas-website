#!/usr/bin/env python3
"""Build the research-lead pages and add them to Explore and the homepage state tiles.

Research leads are unverified Phase B research (SA, ACT, QLD round 2, TAS, WA) published with the
owner's approval. They are kept apart from the genuine records:
  inputs   assets/data/leads-<state>.json   (exported from the staging databases)
  outputs  leads/<id>.html                  one page per lead
           explore.html                     list between <!-- LEAD-RESULTS:START --> and <!-- LEAD-RESULTS:END -->
           index.html                       state tile counts (records plus research leads)

Leads never get map pins, photographs or personal details. Run after tools/build_genuine.py
(build_genuine.py calls this script at the end).
"""
from urllib.parse import quote
import glob, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
E = html.escape
STATE_NAME = {"QLD": "Queensland", "NSW": "New South Wales", "VIC": "Victoria", "WA": "Western Australia", "SA": "South Australia",
              "TAS": "Tasmania", "NT": "Northern Territory", "ACT": "Australian Capital Territory"}
PUBLISHED = "26 November 2026"

raw = open("assets/map/cinema-sites.js", encoding="utf-8").read()
SITES = json.loads(raw[raw.index("window.APA_SITES = ") + 19:].strip().rstrip(";"))["sites"]
LEADS = []
for f in sorted(glob.glob("assets/data/leads-*.json")):
    LEADS += json.load(open(f, encoding="utf-8"))
ids = [l["id"] for l in LEADS]
assert len(ids) == len(set(ids)), "duplicate lead ids"
assert not set(ids) & {s["id"] for s in SITES}, "lead id clashes with a genuine record id"

QMARK = '<path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4.5M12 18h.01"/><circle cx="12" cy="12" r="9.5"/>'
XMARK = '<path d="M18 6 6 18M6 6l12 12"/>'
def svg(p):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true" focusable="false">' + p + "</svg>")
LEAD_BADGE = f'<span class="badge b-unverified"><span class="badge-ico">{svg(QMARK)}</span>Research lead, not verified</span>'
OPEN_BADGE = f'<span class="badge b-conflict"><span class="badge-ico">{svg(XMARK)}</span>Open questions</span>'

def norm(t):
    t = (t or "").lower().replace("&", " and ")
    t = re.sub(r"[’'`]", "", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()
def year(l):
    for k, v in l["facts"]:
        if k.lower().startswith("opened"):
            m = re.search(r"(1[89]\d\d|20\d\d)", v)
            if m: return int(m.group(1))
    return None
def era(y):
    if y is None: return "unknown"
    return "pre1930" if y < 1930 else "1930s40s" if y < 1950 else "1950s60s" if y < 1970 else "1970s80s" if y < 1990 else "1990on"
def place(l):
    return ", ".join(x for x in (l["address"], l["locality"]) if x)

# ---------------------------------------------------------------- page shell (same header and footer as the record pages)
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

os.makedirs("leads", exist_ok=True)
for f in os.listdir("leads"):
    if f.endswith(".html"): os.remove(os.path.join("leads", f))

for l in LEADS:
    sn = STATE_NAME[l["state"]]
    p, q = shell(f"{l['name']}, {l['locality']} (research lead) · Film Cinemas Australia",
                 f"{l['name']} ({l['locality']}, {l['state']}): an unverified research lead in the Film Cinemas Australia archive.")
    aliases = f'<p class="rec-aliases">Also recorded as {E("; ".join(l["aliases"]))}</p>' if l["aliases"] else ""
    facts = "".join(f"<li><strong>{E(k)}:</strong> {E(v)}</li>" for k, v in l["facts"])
    notes = "".join(f"<li>{E(n)}</li>" for n in l["notes"])
    said = (f"<ul>{facts}{notes}</ul>" if facts or notes else "<p>The research so far records only the name and place.</p>")
    oq = "".join(f"<li>{E(c)}</li>" for c in l["conflicts"] + l["related"])
    srcs = "".join((f'<li><a href="{E(s["url"])}" rel="noopener">{E(s["label"])}</a></li>' if s["url"] else f"<li>{E(s['label'])}</li>") for s in l["sources"])
    ids_line = " · ".join(x for x in (f"Lead id <code>{E(l['id'])}</code>",
                                       f"national catalogue id <code>{E(l['nationalId'])}</code>" if l["nationalId"] else "",
                                       "research id " + ", ".join(f"<code>{E(c)}</code>" for c in l["candidateIds"]) if l["candidateIds"] else "") if x)
    main = f'''<main id="main" tabindex="-1">
<section class="record-head" aria-labelledby="rec-title"><div class="wrap" style="grid-template-columns:1fr">
  <div class="stack">
    <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../index.html">Home</a></li><li><a href="../explore.html?state={l["state"].lower()}">Explore cinemas</a></li><li aria-current="page">{E(l["name"])}</li></ol></nav>
    <p class="eyebrow">Research lead · {E(sn)}</p>
    <h1 id="rec-title">{E(l["name"])}</h1>
    {aliases}
    <p class="lede">{E(place(l))} {E(l["state"])}</p>
    <dl class="rec-keyfacts">
      <div><dt>Status today</dt><dd>Not verified</dd></div>
      <div><dt>Opened</dt><dd>{E(str(year(l))) + " (as recorded, not verified)" if year(l) else "Not recorded"}</dd></div>
      <div><dt>Evidence</dt><dd>{LEAD_BADGE} {OPEN_BADGE if oq else ""}</dd></div>
      <div><dt>Location</dt><dd>Not on the map</dd></div>
    </dl>
    <div class="btn-row rec-actions"><a class="btn btn-secondary" href="../explore.html?state={l["state"].lower()}">More in {E(sn)}</a><a class="btn btn-primary" href="../update.html?type=lead&amp;id={E(l["id"])}&amp;name={E(quote(l["name"]))}">Suggest an update</a><a class="btn btn-secondary" href="../share.html">Share a memory</a></div>
  </div>
</div></section>
<div class="wrap rec-body">
  <section class="rec-notes" aria-labelledby="how-title">
    <h2 id="how-title" class="visually-hidden">How sure we are</h2>
    <div class="notice n-info"><p><strong>This is a research lead, not a confirmed record.</strong> {E(l["basis"])}</p>
    <p>Nothing on this page has been checked against its sources by Film Cinemas Australia yet. Names, dates and places may be wrong, and this lead may turn out to be the same cinema as another lead or record.</p>
    <p><strong>Location:</strong> not mapped. No coordinates have been checked for this lead.</p></div>
  </section>
  <article class="site-rec rec-article" aria-labelledby="rec-title" data-lead-id="{E(l["id"])}">
    <h2 id="events-title">What the research notes say</h2>
    {said}
    {f'<h2 id="open-title">Open questions</h2><ul>{oq}</ul>' if oq else ""}
    <h2 id="sources-title">Sources</h2>
    {f"<ul>{srcs}</ul>" if srcs else "<p>No source has been attached to this lead yet.</p>"}
  </article>
  <p class="cite-meta rec-meta">{ids_line} · published {PUBLISHED} as unverified research with the owner's approval; details will change as each lead is checked.</p>
</div>
</main>'''
    open(f"leads/{l['id']}.html", "w", encoding="utf-8").write(p + main + q)

# ---------------------------------------------------------------- Explore
items = []
for l in sorted(LEADS, key=lambda x: (x["name"].lower(), x["locality"].lower())):
    y = year(l)
    search = norm(" ".join([l["name"], " ".join(l["aliases"]), l["address"], l["locality"], l["state"], STATE_NAME[l["state"]], "research lead not verified"]))
    items.append(f'''<li class="gx-item" data-id="{E(l["id"])}" data-state="{l["state"].lower()}" data-status="closed" data-evidence="lead" data-loc="notmapped" data-era="{era(y)}" data-search="{E(search)}">
  <h3 class="gx-name"><a href="leads/{E(l["id"])}.html">{E(l["name"])}</a></h3>
  {f'<p class="gx-alias">Also recorded as {E("; ".join(l["aliases"]))}</p>' if l["aliases"] else ""}
  <p class="gx-place">{E(l["locality"])}, {E(l["state"])} · Status not verified{f" · opened {y} (as recorded)" if y else ""}</p>
  <p class="gx-badges">{LEAD_BADGE}{OPEN_BADGE if (l["conflicts"] or l["related"]) else ""}<span class="gx-loc">Not on the map</span></p>
</li>''')
block = "<!-- LEAD-RESULTS:START -->\n<ul class=\"gx-list\" data-list>\n" + "\n".join(items) + "\n</ul>\n<!-- LEAD-RESULTS:END -->"
ex = open("explore.html", encoding="utf-8").read()
if "<!-- LEAD-RESULTS:START -->" in ex:
    ex = re.sub(r"<!-- LEAD-RESULTS:START -->.*?<!-- LEAD-RESULTS:END -->", lambda m: block, ex, flags=re.S)
else:
    ex = ex.replace("<!-- GENUINE-RESULTS:END -->", "<!-- GENUINE-RESULTS:END -->\n" + block, 1)
# evidence filter choice for leads
if 'value="lead"' not in ex:
    ex = ex.replace('Single secondary source (preliminary)</label>',
                    'Single secondary source (preliminary)</label><label class="choice"><input type="checkbox" name="evidence" value="lead" checked> Research lead, not yet verified</label>', 1)
# state choices: enable every state that has records or leads
total = {k: sum(1 for s in SITES if s["state"] == k) + sum(1 for l in LEADS if l["state"] == k) for k in STATE_NAME}
def opt(m):
    code, name = m.group(1), STATE_NAME[m.group(1).upper()]
    return f'<option value="{code}">{name}</option>' if total[code.upper()] else f'<option value="{code}" disabled>{name} (no records yet)</option>'
ex = re.sub(r'<option value="(qld|nsw|vic|wa|sa|tas|nt|act)"(?: disabled)?>[^<]*</option>', opt, ex)
ex = re.sub(r'<p class="result-count" role="status" aria-live="polite" data-count>[^<]*</p>',
            f'<p class="result-count" role="status" aria-live="polite" data-count>{len(SITES) + len(LEADS)} cinemas</p>', ex, count=1)
if LEADS: ex = re.sub(r"Search and filter the archive's (?:genuine cinema records|\d+ cinema records)[^<]*</p>",
            f"Search and filter the archive's {len(SITES)} cinema records and {len(LEADS)} research leads: names and former names, towns and suburbs, states and status today. Every record shows its sources and how sure we are. Research leads are unverified and are labelled as such.</p>", ex, count=1)
open("explore.html", "w", encoding="utf-8").write(ex)

# ---------------------------------------------------------------- homepage state tiles
idx = open("index.html", encoding="utf-8").read()
def tile(m):
    code = re.search(r"<strong>([A-Z]+)</strong>", m.group(0)).group(1)
    g = sum(1 for s in SITES if s["state"] == code); n = sum(1 for l in LEADS if l["state"] == code)
    parts = ([f"{g} record{'s' if g != 1 else ''}"] if g else []) + ([f"{n} research lead{'s' if n != 1 else ''}"] if n else [])
    inner = re.sub(r'<span class="st-count">[^<]*</span>', f'<span class="st-count">{" · ".join(parts) if parts else "No records yet"}</span>', m.group(2))
    return (f'<a class="state-tile" href="explore.html?state={code.lower()}">' + inner + "</a>") if parts else ('<div class="state-tile st-empty">' + inner + "</div>")
idx = re.sub(r'<(a|div) class="state-tile[^"]*"[^>]*>(.*?)</(?:a|div)>(?=<a class="state-tile|<div class="state-tile|</div>)', tile, idx, flags=re.S)
open("index.html", "w", encoding="utf-8").write(idx)
print(f"{len(LEADS)} research-lead pages written to leads/ (" + ", ".join(f"{k} {sum(1 for l in LEADS if l['state'] == k)}" for k in STATE_NAME if any(l['state'] == k for l in LEADS)) + ")")
