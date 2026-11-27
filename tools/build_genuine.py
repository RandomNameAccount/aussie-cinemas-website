#!/usr/bin/env python3
"""Build the genuine cinema record pages and the Explore results list.

Inputs (both already in the repository):
  assets/map/cinema-sites.js   genuine dataset (73 sites, stable ids)
  research.html                cited write-up for each site (<article class="site-rec" id="site-<id>">)

Outputs:
  cinemas/<id>.html            one record page per site
  explore.html                 results list between <!-- GENUINE-RESULTS:START --> and <!-- GENUINE-RESULTS:END -->
  research.html                withheld locations shown as withheld; table names link to record pages

Re-run after any change to the dataset or the research write-ups:  python3 tools/build_genuine.py
Nothing here invents data: every fact on a record page comes from the dataset or the research write-up.
"""
from urllib.parse import quote
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def load_sites():
    raw = open("assets/map/cinema-sites.js", encoding="utf-8").read()
    j = raw[raw.index("window.APA_SITES = ") + len("window.APA_SITES = "):].strip().rstrip(";")
    return json.loads(j)

DATA = load_sites()
SITES = DATA["sites"]
STATE_NAME = {"QLD": "Queensland", "NSW": "New South Wales", "VIC": "Victoria", "WA": "Western Australia", "SA": "South Australia", "TAS": "Tasmania", "NT": "Northern Territory", "ACT": "Australian Capital Territory"}
E = html.escape

ICON = {
    "confirmed": '<path d="M20 6 9 17l-5-5"/>',
    "strong": '<path d="M12 3 3 7.5l9 4.5 9-4.5zM3 12l9 4.5 9-4.5M3 16.5 12 21l9-4.5"/>',
    "prelim": '<path d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.3-4.3"/>',
    "conflict": '<path d="M18 6 6 18M6 6l12 12"/>',
}
def svg(path):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true" focusable="false">' + path + "</svg>")
def badge(kind, label):
    return f'<span class="badge b-{kind}"><span class="badge-ico">{svg(ICON[kind])}</span>{E(label)}</span>'

# What each evidence level means, in plain words. Preliminary research is never described as confirmed.
EVIDENCE_MEANING = {
    "confirmed": "An official heritage register entry was read directly and confirms the cinema's name and address. Individual dates and events are cited to their own sources below and are only as reliable as those sources.",
    "strong": "Two independent published sources agree on the cinema's identity and address. This is not a heritage register confirmation.",
    "prelim": "Preliminary research: based on a single secondary source, usually the volunteer-edited Cinema Treasures. Treat the details as unconfirmed until a second source is found.",
}
LOC_MEANING = {
    "site": "Published site point. The source of the coordinates is named below. It has not been checked against the historic footprint or entrance.",
    "city": "Approximate: placed at the Natural Earth populated-place point for the city centre (public domain), not at the building.",
    "suburb": "Approximate: placed at a suburb reference point, not at the building.",
    "none": "Not mapped: the sources do not give enough to place this cinema.",
    "withheld": "Location withheld from the public map while the coordinate's licence or provenance is reviewed.",
}
STATUS_GROUP = {"operating": "Operating cinema", "repurposed": "Building survives, other use", "demolished": "Demolished", "closed": "Closed or not stated"}

def opened_year(s):
    for d, what in s["events"]:
        if re.search(r"\bopen", what, re.I):
            m = re.search(r"(1[89]\d\d|20\d\d)", d)
            if m: return int(m.group(1))
    return None

def era(y):
    if y is None: return "unknown"
    if y < 1930: return "pre1930"
    if y < 1950: return "1930s40s"
    if y < 1970: return "1950s60s"
    if y < 1990: return "1970s80s"
    return "1990on"

def norm(t):
    t = t.lower().replace("&", " and ")
    t = re.sub(r"[’'`]", "", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

def mappable(s):
    return s["loc"]["kind"] in ("site", "city", "suburb") and isinstance(s["loc"].get("lat"), (int, float))

# ---------------------------------------------------------------- research.html updates
research = open("research.html", encoding="utf-8").read()

def update_research(doc):
    for s in SITES:
        sid = s["id"]
        # article Location row
        a0 = doc.find(f'<article class="site-rec" id="site-{sid}"')
        if a0 < 0: sys.exit(f"research.html has no write-up for {sid}")
        a1 = doc.index("</article>", a0)
        art = doc[a0:a1]
        if s["loc"]["kind"] == "withheld":
            art2 = re.sub(r'(<div><dt>Location</dt><dd>).*?(</dd></div>)', lambda m: m.group(1) + "Location withheld. " + E(s["loc"]["note"]) + m.group(2), art, count=1, flags=re.S)
            doc = doc[:a0] + art2 + doc[a1:]
            # table cell
            r0 = doc.find(f'<a href="#site-{sid}">')
            if r0 < 0: r0 = doc.find(f'<a href="cinemas/{sid}.html">')
            r1 = doc.index("</tr>", r0)
            row = doc[r0:r1]
            row2 = re.sub(r"<td>(Published site point|Suburb only|City centre only|Location withheld[^<]*)</td>", "<td>Location withheld (under review)</td>", row, count=1)
            doc = doc[:r0] + row2 + doc[r1:]
        # table name links to the record page
        doc = doc.replace(f'<th scope="row"><a href="#site-{sid}">', f'<th scope="row"><a href="cinemas/{sid}.html">', 1)
        # write-up heading links to the record page
        h = f'<h3 id="h-{sid}">'
        i = doc.find(h)
        if i >= 0 and doc[i:i + 400].find(f'href="cinemas/{sid}.html"') < 0:
            j = doc.index("</h3>", i)
            doc = doc[:j] + f' <a class="rec-link" href="cinemas/{sid}.html">Open record<span class="visually-hidden">: {E(s["name"])}</span></a>' + doc[j:]
    return doc

research = update_research(research)
counts = {}
for s in SITES:
    if mappable(s): counts[s["region"]] = counts.get(s["region"], 0) + 1
mapped = sum(counts.values())
withheld = sum(1 for s in SITES if s["loc"]["kind"] == "withheld")
unmapped = sum(1 for s in SITES if s["loc"]["kind"] == "none")
region_text = ", ".join(f"{r} {counts.get(r, 0)}" for r in ["Brisbane", "Sydney", "Melbourne", "Regional Queensland", "Regional NSW"])
research = re.sub(r"\d+ sites, \d+ on the map:[^.]*\.( \d+ more are listed but not yet mapped\.)?( \d+ more [^.]*\.)*( \d+ have no placeable location and \d+ have their location withheld [^.]*\.)*",
                  f"{len(SITES)} sites, {mapped} on the map: {region_text}. {unmapped} have no placeable location and {withheld} have their location withheld while its licence or provenance is reviewed.",
                  research, count=1)
open("research.html", "w", encoding="utf-8").write(research)

# ---------------------------------------------------------------- page shell for records
def shell_parts(doc):
    head_end = doc.index("<main")
    main_end = doc.index("</main>") + len("</main>")
    return doc[:head_end], doc[main_end:]

pre, post = shell_parts(research)

def rebase(fragment):
    """Make relative URLs work from the cinemas/ folder."""
    def fix(m):
        attr, q, url = m.group(1), m.group(2), m.group(3)
        if re.match(r"^(https?:|mailto:|tel:|#|data:|/|\.\./)", url) or url == "":
            return m.group(0)
        if url == "./": url = "../"
        else: url = "../" + url
        return f'{attr}={q}{url}{q}'
    return re.sub(r'\b(href|src)=(["\'])([^"\']*)\2', fix, fragment)

def page_shell(title, desc):
    p = pre
    p = re.sub(r"<title>.*?</title>", f"<title>{E(title)}</title>", p, count=1, flags=re.S)
    p = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{E(desc)}">', p, count=1)
    p = p.replace('<body data-page="research">', '<body data-page="record">')
    # Leaflet styles are not needed on record pages
    p = re.sub(r'<link rel="stylesheet" href="assets/vendor/leaflet/[^"]+">\n?', "", p)
    p = re.sub(r'(<a href="explore.html")>', r'\1 aria-current="page">', p, count=1)
    p = re.sub(r'(<li><a href="research.html") aria-current="page"', r"\1", p)
    q = post
    q = re.sub(r'<script src="assets/vendor/leaflet/[^"]+"></script>\n?', "", q)
    q = re.sub(r'<script src="assets/map/[^"]+"></script>\n?', "", q)
    q = re.sub(r'<script src="assets/map\.js[^"]*"></script>\n?', "", q)
    q = re.sub(r'<script src="assets/map-loader\.js[^"]*"></script>\n?', "", q)
    return rebase(p), rebase(q)

def article_body(sid):
    a0 = research.find(f'<article class="site-rec" id="site-{sid}"')
    a1 = research.index("</article>", a0)
    art = research[a0:a1]
    art = art[art.index(">") + 1:]                       # drop <article ...>
    art = re.sub(r"<h3[^>]*>.*?</h3>", "", art, count=1, flags=re.S)
    art = re.sub(r'<p class="cite-meta">Also known as.*?</p>', "", art, count=1, flags=re.S)
    art = art.replace("<h4>What the sources say</h4>", '<h2 id="events-title">What the sources say</h2>')
    art = art.replace("<h4>Sources</h4>", '<h2 id="sources-title">Sources</h2>')
    return art.strip()

os.makedirs("cinemas", exist_ok=True)
for f in os.listdir("cinemas"):
    if f.endswith(".html"): os.remove(os.path.join("cinemas", f))

for s in SITES:
    sid = s["id"]
    y = opened_year(s)
    title = f"{s['name']}, {s['suburb']} · Film Cinemas Australia"
    desc = f"{s['name']} ({s['suburb']}, {s['state']}): status, dated events and cited sources from the Film Cinemas Australia archive."
    p, q = page_shell(title, desc)
    k = s["loc"]["kind"]
    actions = []
    if mappable(s):
        actions.append(f'<a class="btn btn-secondary" href="../index.html?focus={E(sid)}#map">Show on the map</a>')
    actions.append(f'<a class="btn btn-secondary" href="../research.html#site-{E(sid)}">Research table entry</a>')
    actions.append(f'<a class="btn btn-primary" href="../update.html?type=record&amp;id={E(sid)}&amp;name={E(quote(s["name"]))}">Suggest an update</a>')
    actions.append(f'<a class="btn btn-secondary" href="../share.html?cinema={E(sid)}">Share a memory</a>')
    conflict = badge("conflict", "Sources disagree") if s.get("conflicts") else ""
    aliases = f'<p class="rec-aliases">Also known as {E("; ".join(s["aliases"]))}</p>' if s.get("aliases") else ""
    main = f'''<main id="main" tabindex="-1">
<section class="record-head" aria-labelledby="rec-title"><div class="wrap" style="grid-template-columns:1fr">
  <div class="stack">
    <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../index.html">Home</a></li><li><a href="../explore.html">Explore cinemas</a></li><li aria-current="page">{E(s["name"])}</li></ol></nav>
    <p class="eyebrow">Genuine cinema record · {E(s["region"])}, {E(STATE_NAME.get(s["state"], s["state"]))}</p>
    <h1 id="rec-title">{E(s["name"])}</h1>
    {aliases}
    <p class="lede">{E(s["address"])}, {E(s["suburb"])} {E(s["state"])}</p>
    <dl class="rec-keyfacts">
      <div><dt>Status today</dt><dd>{E(s["statusLabel"])}</dd></div>
      <div><dt>Opened</dt><dd>{E(str(y)) if y else "No opening date recorded; see the dated events"}</dd></div>
      <div><dt>Evidence</dt><dd>{badge(s["evidence"], s["evidenceLabel"])} {conflict}</dd></div>
      <div><dt>Location</dt><dd>{E(s["locLabel"])}</dd></div>
    </dl>
    <div class="btn-row rec-actions">{"".join(actions)}</div>
  </div>
</div></section>
<div class="wrap rec-body">
  <section class="rec-notes" aria-labelledby="how-title">
    <h2 id="how-title" class="visually-hidden">How sure we are</h2>
    <div class="notice n-info"><p><strong>Evidence:</strong> {E(EVIDENCE_MEANING[s["evidence"]])}</p>
    <p><strong>Location:</strong> {E(s["loc"]["note"] if k == "none" and s["loc"].get("note", "").startswith("Not on the map.") else LOC_MEANING[k])}</p>
    {"<p><strong>Sources disagree:</strong> both versions are kept below. Neither has been chosen.</p>" if s.get("conflicts") else ""}</div>
  </section>
  <article class="site-rec rec-article" aria-labelledby="rec-title" data-cinema-id="{E(sid)}">
  {rebase(article_body(sid))}
  </article>
  <p class="cite-meta rec-meta">Record id <code>{E(sid)}</code> · sources read on {E(DATA.get("readOn", ""))} · summaries are written in our own words; facts are cited to their sources.</p>
</div>
</main>'''
    open(f"cinemas/{sid}.html", "w", encoding="utf-8").write(p + main + q)

# ---------------------------------------------------------------- Explore results list
def search_text(s):
    parts = [s["name"], " ".join(s.get("aliases") or []), s["address"], s["suburb"], s["region"], s["state"], STATE_NAME.get(s["state"], ""), s["statusLabel"], STATUS_GROUP.get(s["status"], "")]
    return norm(" ".join(parts))

def loc_group(s):
    k = s["loc"]["kind"]
    return "site" if k == "site" else ("approx" if k in ("city", "suburb") else "notmapped")

items = []
for s in sorted(SITES, key=lambda x: (x["name"].lower(), x["suburb"].lower())):
    y = opened_year(s)
    items.append(f'''<li class="gx-item" data-id="{E(s["id"])}" data-state="{E(s["state"].lower())}" data-status="{E(s["status"])}" data-evidence="{E(s["evidence"])}" data-loc="{loc_group(s)}" data-era="{era(y)}" data-search="{E(search_text(s))}">
  <h3 class="gx-name"><a href="cinemas/{E(s["id"])}.html">{E(s["name"])}</a></h3>
  {f'<p class="gx-alias">Also known as {E("; ".join(s["aliases"]))}</p>' if s.get("aliases") else ""}
  <p class="gx-place">{E(s["suburb"])}, {E(s["state"])} · {E(s["statusLabel"])}{f" · opened {y}" if y else ""}</p>
  <p class="gx-badges">{badge(s["evidence"], s["evidenceLabel"])}{badge("conflict", "Sources disagree") if s.get("conflicts") else ""}<span class="gx-loc">{E(s["locLabel"])}</span></p>
</li>''')
block = '<!-- GENUINE-RESULTS:START -->\n<ul class="gx-list" data-list>\n' + "\n".join(items) + "\n</ul>\n<!-- GENUINE-RESULTS:END -->"
ex = open("explore.html", encoding="utf-8").read()
if "<!-- GENUINE-RESULTS:START -->" in ex:
    ex = re.sub(r"<!-- GENUINE-RESULTS:START -->.*?<!-- GENUINE-RESULTS:END -->", lambda m: block, ex, flags=re.S)
    open("explore.html", "w", encoding="utf-8").write(ex)
    print("explore.html list updated")
else:
    print("explore.html has no GENUINE-RESULTS markers; list not inserted")
# ---------------------------------------------------------------- Homepage blocks
BY_ID = {x["id"]: x for x in SITES}
PIN = '<path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"/>'
CAL = '<path d="M4 6h16v14H4zM4 10h16M8 3v4M16 3v4"/>'
GO = '<svg class="go" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m9 6 6 6-6 6"/></svg>'
FEATURED = ["regent", "state-sydney", "qhr-601743", "shr-01401"]   # editorial choice; any ids from the dataset work

def featured_card(x):
    y = opened_year(x)
    plate = (f'<span class="plate-k">Opened</span><span class="plate-y">{y}</span>' if y else '<span class="plate-k">Opening date</span><span class="plate-y plate-none">not recorded</span>')
    return f'''<article class="card card-row">
  <div class="card-art art-plate" aria-hidden="true"><span class="plate-state">{E(x["state"])}</span>{plate}<span class="plate-status">{E(STATUS_GROUP.get(x["status"], ""))}</span></div>
  <div class="card-body">
    <h3><a href="cinemas/{E(x["id"])}.html">{E(x["name"])}</a></h3>
    <p class="card-line">{svg(PIN)}<span>{E(x["suburb"])}, {E(x["state"])}<span class="visually-hidden"> ({E(STATE_NAME.get(x["state"], ""))})</span></span></p>
    <p class="card-line muted">{svg(CAL)}<span>{E("Opened " + str(y) if y else "No opening date recorded; see the dated events")} · {E(x["statusLabel"])}</span></p>
    <div class="card-foot"><span>{badge(x["evidence"], x["evidenceLabel"])}{badge("conflict", "Sources disagree") if x.get("conflicts") else ""}</span>{GO}</div>
  </div>
</article>'''

DISAGREE = ["shr-01401", "red-hill", "merthyr"]
def disagree_item(x):
    return (f'<li><div class="stack" style="gap:.45rem"><a href="cinemas/{E(x["id"])}.html">{E(x["name"])}, {E(x["suburb"])} {E(x["state"])}</a>'
            f'<p>{E(x["conflicts"][0])}</p><div class="meta">{badge("conflict", "Sources disagree")}</div></div></li>')

def map_list():
    groups = {}
    for x in SITES:
        if mappable(x): groups.setdefault(x["region"], []).append(x)
    out = []
    for r in ["Brisbane", "Sydney", "Melbourne", "Regional Queensland", "Regional NSW"]:
        g = sorted(groups.get(r, []), key=lambda x: x["name"].lower())
        if not g: continue
        lis = "".join(f'<li><a href="cinemas/{E(x["id"])}.html">{E(x["name"])}</a>, {E(x["suburb"])} <span class="ml-meta">· {E(x["statusLabel"])} · {E("approximate location" if x["loc"]["kind"] != "site" else "site point")}</span></li>' for x in g)
        out.append(f'<h3 class="ml-region">{E(r)} <span class="ml-n">({len(g)})</span></h3><ul class="ml-items">{lis}</ul>')
    return "".join(out)

STATE_ORDER = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"]
state_counts = {k: sum(1 for x in SITES if x["state"] == k) for k in STATE_ORDER}

idx = open("index.html", encoding="utf-8").read()
def fill(doc, name, content):
    a, b = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    if a not in doc: print(f"index.html: no {name} markers"); return doc
    return re.sub(re.escape(a) + ".*?" + re.escape(b), lambda m: a + content + b, doc, flags=re.S)
idx = fill(idx, "FEATURED", "".join(featured_card(BY_ID[i]) for i in FEATURED))
idx = fill(idx, "DISAGREE", "".join(disagree_item(BY_ID[i]) for i in DISAGREE))
idx = fill(idx, "MAP-LIST", map_list())
idx = fill(idx, "MAP-COUNT", f"{mapped} of the archive's {len(SITES)} genuine cinema records are on the map: " + ", ".join(f"{r} ({counts[r]})" for r in ["Brisbane", "Sydney", "Regional Queensland", "Regional NSW"] if counts.get(r)) + ".")
# state tiles: real counts; states with no records are shown but not linked
def tile(m):
    code = m.group(2); n = state_counts.get(code, 0)
    inner = re.sub(r'<span class="st-count">[^<]*</span>', f'<span class="st-count">{n} record{"s" if n != 1 else ""}</span>' if n else '<span class="st-count">No records yet</span>', m.group(3))
    return (f'<a class="state-tile" href="explore.html?state={code.lower()}">' + inner + "</a>") if n else ('<div class="state-tile st-empty">' + inner + "</div>")
idx = re.sub(r'<(a|div) class="state-tile[^"]*"[^>]*>(?=.*?<strong>([A-Z]+)</strong>)(.*?)</(?:a|div)>', lambda m: tile(m) if True else m.group(0), idx, flags=re.S)
open("index.html", "w", encoding="utf-8").write(idx)

# ---------------------------------------------------------------- Share form: cinema choices
sh = open("share.html", encoding="utf-8").read()
opts = '<option value="">It\'s not listed, or I\'m not sure</option>' + "".join(
    f'<option value="{E(s["id"])}">{E(s["name"])}, {E(s["suburb"])} {E(s["state"])}</option>'
    for s in sorted(SITES, key=lambda x: (x["name"].lower(), x["suburb"].lower())))
sh2 = re.sub(r'(<select id="s-cinema" name="cinema">).*?(</select>)', lambda m: m.group(1) + opts + m.group(2), sh, count=1, flags=re.S)
if sh2 != sh:
    open("share.html", "w", encoding="utf-8").write(sh2); print("share.html cinema list updated")

print(f"{len(SITES)} record pages written to cinemas/; {mapped} mapped, {withheld} withheld, {unmapped} unmapped")

# ---------------------------------------------------------------- Research leads (kept separate from genuine records)
import runpy
runpy.run_path(os.path.join(ROOT, "tools", "build_leads.py"), run_name="__main__")
runpy.run_path(os.path.join(ROOT, "tools", "build_archive.py"), run_name="__main__")
