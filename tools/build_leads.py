#!/usr/bin/env python3
"""Build the research-lead pages and add them to Explore and the homepage state tiles.

Research leads are unverified Phase B research (SA, ACT, QLD round 2, TAS, WA, NSW discovery batch 01) published with the
owner's approval. They are kept apart from the genuine records:
  inputs   assets/data/leads-<state>.json   (exported from the staging databases)
  outputs  leads/<id>.html                  one page per lead
           explore.html                     list between <!-- LEAD-RESULTS:START --> and <!-- LEAD-RESULTS:END -->
           index.html                       state tile counts (records plus research leads)

Leads never get exact map pins, photographs or personal details (approximate town-centre markers come from build_approx.py). Run after tools/build_genuine.py
(build_genuine.py calls this script at the end).
"""
from urllib.parse import quote
import glob, html, json, os, re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
E = html.escape
STATE_NAME = {"QLD": "Queensland", "NSW": "New South Wales", "VIC": "Victoria", "WA": "Western Australia", "SA": "South Australia",
              "TAS": "Tasmania", "NT": "Northern Territory", "ACT": "Australian Capital Territory"}
PUBLISHED = "26 November 2026"

raw = open("assets/map/cinema-sites.js", encoding="utf-8").read()
SITES = json.loads(raw[raw.index("window.APA_SITES = ") + 19:].strip().rstrip(";"))["sites"]
APPROX = json.load(open("assets/data/approx-placements.json", encoding="utf-8")) if os.path.exists("assets/data/approx-placements.json") else {}
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
def closed_text(l):
    for k, v in l["facts"]:
        if k.lower() in ("closed", "last listed"):
            return v
    return ""
def era(y):
    if y is None: return "unknown"
    return "pre1930" if y < 1930 else "1930s40s" if y < 1950 else "1950s60s" if y < 1970 else "1970s80s" if y < 1990 else "1990on"
def gmaps_url(*parts):
    """Google Maps search link (no API key). Parenthetical source notes are dropped."""
    q = ", ".join(re.sub(r"\s*\([^)]*\)", "", p).strip() for p in parts if p and p.strip())
    return "https://www.google.com/maps/search/?api=1&query=" + quote(q)

def gmaps_btn(*parts):
    return f'<a class="btn btn-secondary" href="{E(gmaps_url(*parts))}" target="_blank" rel="noopener">Find on Google Maps<span class="visually-hidden"> (opens in a new tab)</span></a>'

def _icon(name):
    body = re.search(r"<svg[^>]*>(.*)</svg>", open(f"assets/icons/equip-{name}.svg", encoding="utf-8").read(), re.S).group(1)
    return ('<svg viewBox="0 0 52 52" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true" focusable="false">' + body + "</svg>")
ICONS = {"drive-in": _icon("driveins"), "open-air": _icon("driveins"), "hall": _icon("seating"), "": _icon("sites")}
def placeholder(l):
    """Outline icon for leads without a photograph (no photographs are attached to research leads)."""
    kind = l.get("type") if l.get("type") in ICONS else ""
    label = {"drive-in": "drive-in", "open-air": "open-air cinema", "hall": "hall"}.get(kind, "cinema")
    return f'<figure class="lead-ph" aria-label="No photograph yet: placeholder icon for a {label}">{ICONS[kind]}<figcaption>No photograph yet</figcaption></figure>'
STATUS_TEXT = {"operating": "Operating cinema", "repurposed": "Building survives, other use", "demolished": "Demolished", "closed": "Closed or not stated"}
def status_of(l):
    return l.get("status") if l.get("status") in STATUS_TEXT else "closed"
def region_of(l):
    return l.get("region") or ""

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

# other cinemas in the same suburb or town (records and leads), shown on each lead page
from collections import defaultdict
SAME = defaultdict(list)
for s_ in SITES:
    SAME[(norm(s_["suburb"]), s_["state"])].append((s_["name"], f"../cinemas/{s_['id']}.html", "record"))
for l_ in LEADS:
    SAME[(norm(l_["locality"]), l_["state"])].append((l_["name"], f"{l_['id']}.html", "research lead"))
def related_html(l):
    others = [x for x in SAME[(norm(l["locality"]), l["state"])] if not x[1].endswith(f"{l['id']}.html")]
    if not others or not l["locality"] or l["locality"].startswith(("Melbourne (postcode", "Sydney (postcode")):
        return ""
    lis = "".join(f'<li><a href="{E(u)}">{E(n)}</a> <span class="muted">({k})</span></li>' for n, u, k in sorted(others)[:12])
    more = f'<p><a href="../explore.html?q={quote(l["locality"])}&amp;state={l["state"].lower()}">All {len(others) + 1} in {E(l["locality"])}</a></p>' if len(others) > 12 else ""
    return f'<h2 id="related-title">Other cinemas in {E(l["locality"])}</h2><ul>{lis}</ul>{more}'

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
<section class="record-head" aria-labelledby="rec-title"><div class="wrap lead-head">
  {placeholder(l)}
  <div class="stack">
    <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../index.html">Home</a></li><li><a href="../explore.html?state={l["state"].lower()}">Explore cinemas</a></li><li aria-current="page">{E(l["name"])}</li></ol></nav>
    <p class="eyebrow">Research lead · {E(sn)}</p>
    <h1 id="rec-title">{E(l["name"])}</h1>
    {aliases}
    <p class="lede">{E(place(l))} {E(l["state"])}{(" · " + E(region_of(l))) if region_of(l) else ""}</p>
    <dl class="rec-keyfacts">
      <div><dt>Status today</dt><dd>{E(l["statusNote"]) if l.get("statusNote") else "Not verified"}</dd></div>
      <div><dt>Opened</dt><dd>{E(str(year(l))) + " (as recorded, not verified)" if year(l) else "Not recorded"}</dd></div>
      {f'<div><dt>Closed</dt><dd>{E(closed_text(l))}</dd></div>' if closed_text(l) else ""}
      <div><dt>Evidence</dt><dd>{LEAD_BADGE} {OPEN_BADGE if oq else ""}</dd></div>
      <div><dt>Location</dt><dd>{f'<a href="../index.html?focus={E(l["id"])}#map">On the map, approximately</a> (centre of {E(APPROX[l["id"]]["place"])}; the exact site is not known)' if l["id"] in APPROX else "Not on the map"}</dd></div>
    </dl>
    <div class="btn-row rec-actions"><a class="btn btn-secondary" href="../explore.html?state={l["state"].lower()}">More in {E(sn)}</a><a class="btn btn-primary" href="../update.html?type=lead&amp;id={E(l["id"])}&amp;name={E(quote(l["name"]))}">Suggest an update</a>{gmaps_btn(l["name"], l.get("locality", ""), l["state"])}<a class="btn btn-secondary" href="../share.html">Share a memory</a></div>
  </div>
</div></section>
<div class="wrap rec-body">
  <section class="rec-notes" aria-labelledby="how-title">
    <h2 id="how-title" class="visually-hidden">How sure we are</h2>
    <div class="notice n-info"><p><strong>This is a research lead, not a confirmed record.</strong> {E(l["basis"])}</p>
    <p>Nothing on this page has been checked against its sources by Film Cinemas Australia yet. Names, dates and places may be wrong, and this lead may turn out to be the same cinema as another lead or record.</p>
    <p><strong>Location:</strong> {("approximate only. The map marker sits at the centre of " + E(APPROX[l["id"]]["place"]) + "; no coordinates for the cinema itself have been checked.") if l["id"] in APPROX else "not mapped. No coordinates have been checked for this lead."}</p></div>
  </section>
  <article class="site-rec rec-article" aria-labelledby="rec-title" data-lead-id="{E(l["id"])}">
    {f'<h2 id="summary-title">Summary</h2><p>{E(l["summary"])}</p>' if l.get("summary") else ""}
    <h2 id="events-title">What the research notes say</h2>
    {'<p class="prov-note"><span class="tag-prov">Provisional</span> Every detail below is given as its named source records it. None has been confirmed by a Film Cinemas Australia editor.</p>' if facts else ""}
    {said}
    {f'<h2 id="open-title">Open questions</h2><ul>{oq}</ul>' if oq else ""}
    {related_html(l)}
    <h2 id="sources-title">Sources</h2>
    {f"<ul>{srcs}</ul>" if srcs else "<p>No source has been attached to this lead yet.</p>"}
  </article>
  <p class="cite-meta rec-meta">{ids_line} · {("staged " + str(date.today().strftime("%-d %B %Y")) + " for editorial review (proposed evidence level " + E(l.get("level", "")) + "); not yet approved for publication") if str(l.get("published", "")).startswith("staging") else ("published " + l.get("published", PUBLISHED) + " as unverified research with the owner's approval; details will change as each lead is checked")}.</p>
</div>
</main>'''
    open(f"leads/{l['id']}.html", "w", encoding="utf-8").write(p + main + q)

# ---------------------------------------------------------------- Explore
items = []
for l in sorted(LEADS, key=lambda x: (x["name"].lower(), x["locality"].lower())):
    y = year(l)
    search = norm(" ".join([l["name"], " ".join(l["aliases"]), l["address"], l["locality"], l.get("postcode", ""), region_of(l), l["state"], STATE_NAME[l["state"]], STATUS_TEXT[status_of(l)], "research lead not verified"]))
    items.append(f'''<li class="gx-item" data-id="{E(l["id"])}" data-state="{l["state"].lower()}" data-region="{E(region_of(l))}" data-status="{status_of(l)}" data-evidence="lead" data-loc="{"approx" if l["id"] in APPROX else "notmapped"}" data-era="{era(y)}" data-search="{E(search)}">
  <h3 class="gx-name"><a href="leads/{E(l["id"])}.html">{E(l["name"])}</a></h3>
  {f'<p class="gx-alias">Also recorded as {E("; ".join(l["aliases"]))}</p>' if l["aliases"] else ""}
  <p class="gx-place">{E(l["locality"])}, {E(l["state"])} · {E(STATUS_TEXT[status_of(l)] + " (not verified)") if l.get("status") else "Status not verified"}{f" · opened {y} (as recorded)" if y else ""}{(" · closed " + (re.search(r"(1[89]\d\d|20\d\d)", closed_text(l)) or [""])[0] + " (as recorded)") if re.search(r"(1[89]\d\d|20\d\d)", closed_text(l)) else ""}</p>
  <p class="gx-badges">{LEAD_BADGE}{OPEN_BADGE if (l["conflicts"] or l["related"]) else ""}<span class="gx-loc">{E("Approximate: " + APPROX[l["id"]]["place"]) if l["id"] in APPROX else "Not on the map"}</span></p>
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
# region filter: records carry their region; leads carry one where the research gives it. Counts are rebuilt every time.
REC_REGION = {s["id"]: s.get("region", "") for s in SITES}
def add_rec_region(m):
    rid = m.group(1)
    return m.group(0) if 'data-region=' in m.group(0) else m.group(0).replace('data-state=', f'data-region="{E(REC_REGION.get(rid, ""))}" data-state=', 1)
ex = re.sub(r'<li class="gx-item" data-id="([^"]+)"[^>]*>', add_rec_region, ex)
from collections import Counter
rc = Counter([s.get("region", "") for s in SITES if s.get("region")] + [region_of(l) for l in LEADS if region_of(l)])
reg_opts = '<option value="">Any region</option>' + "".join(f'<option value="{E(r)}">{E(r)} ({n})</option>' for r, n in sorted(rc.items()))
reg_field = f'<div class="field" data-region-field><label for="f-region">Region</label><select id="f-region" name="region">{reg_opts}</select></div>'
if "data-region-field" in ex:
    ex = re.sub(r'<div class="field" data-region-field>.*?</select></div>', lambda m: reg_field, ex, count=1, flags=re.S)
else:
    ex = ex.replace('<div class="field"><label for="f-loc">', reg_field + '\n    <div class="field"><label for="f-loc">', 1)
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
