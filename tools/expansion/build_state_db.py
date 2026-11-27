#!/usr/bin/env python3
"""State archive expansion (Victoria, New South Wales, ...): build one consolidated database from the raw source extracts.
Run with FCA_STATE=VIC (default) or FCA_STATE=NSW; files live in research/<state>/.

Inputs (research/vic/, extracts saved from the sources; re-run any time, the build is idempotent)
  caarp-part*.json         CAARP venue list + venue pages (CC BY-NC-SA 3.0)
  cinematreasures.json     Cinema Treasures Victoria list + theatre pages (facts only)
  vhd.json                 Victorian Heritage Database search + place pages (name, address, listing)
  vic-localities.json      GeoNames VIC postal localities (CC BY 4.0), optional, for postcodes and regions
Outputs
  <state>-master.json / .csv   one row per unique cinema (FCA-VIC-nnnn)
  <state>-duplicates.csv               every merge and every match to an existing website record
  <state>-progress.json                resumable progress: what is collected, what is still missing
Rules: unknown stays unknown; nothing is inferred beyond what a source states; every field keeps its source.
"""
import csv, glob, json, os, re, unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = os.environ.get("FCA_STATE", "VIC").upper()
R = os.path.join(ROOT, "research", STATE.lower())
PC_OK = {"VIC": lambda p: p[:1] in "38", "NSW": lambda p: p[:1] == "2" and not (2600 <= int(p) <= 2620 or 2900 <= int(p) <= 2920)}[STATE]
STATE_WORD = {"VIC": "victoria", "NSW": "new south wales"}[STATE]
os.chdir(ROOT)

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\bst\.?\s", "saint ", s) if False else s
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

GENERIC = set("the theatre theater theatres cinema cinemas picture pictures picturetheatre hall palace house theatrette "
              "complex centre center former and of de luxe deluxe new old photoplay photoplays drive in drivein open air "
              "gardens garden pty ltd co hoyts village union greater news newsreel twin centre center event reading united".split())
STREET_ABBR = {"st": "street", "rd": "road", "ave": "avenue", "av": "avenue", "pde": "parade", "hwy": "highway", "tce": "terrace",
               "cres": "crescent", "ct": "court", "pl": "place", "dr": "drive", "blvd": "boulevard", "hwy": "highway", "cnr": "corner"}

def plain_name(name, locality=""):
    loc = set(norm(locality).split())
    return " ".join(w for w in norm(name).split() if w not in loc and w not in {"the", "theatre", "cinema", "pictures", "picture"})

def core_tokens(name, locality=""):
    loc = set(norm(locality).split())
    return {t for t in norm(name).split() if t not in GENERIC and t not in loc and not t.isdigit() and len(t) > 1}

def street_key(addr):
    """('435', 'melbourne road') or (None, 'melbourne road') from a free-text address."""
    a = norm(addr)
    a = " ".join(STREET_ABBR.get(w, w) for w in a.split())
    a = re.sub(r"\b(corner|cnr|near|off|opposite|lit|little)\b", lambda m: "little" if m.group(1) in ("lit", "little") else "", a)
    a = re.sub(r"\b([nsew])\b(?= [a-z])", lambda m: {"n": "north", "s": "south", "e": "east", "w": "west"}[m.group(1)], a)
    a = re.sub(r"\s+", " ", a).strip()
    m = re.search(r"(?:(\d+)[a-z]?(?: \d+[a-z]?)? )?([a-z][a-z ]*? (?:street|road|avenue|parade|highway|terrace|crescent|place|drive|boulevard|lane|way|esplanade|grove|square|circuit|walk|arcade|promenade|court|track))\b", a)
    if not m:
        return None, ""
    return m.group(1), m.group(2).strip()

def pc_region(pc, locality=""):
    try:
        p = int(pc)
    except (TypeError, ValueError):
        return ""
    if STATE == "NSW":                            # regions named in the NSW expansion brief, assigned by postcode
        for a, b, r in [(2000, 2001, "Sydney CBD"), (2002, 2009, "Inner West"), (2010, 2011, "Eastern Suburbs"), (2012, 2020, "Inner West"),
                        (2021, 2036, "Eastern Suburbs"), (2037, 2051, "Inner West"), (2052, 2052, "Eastern Suburbs"), (2055, 2083, "North Shore"),
                        (2084, 2108, "Northern Beaches"), (2109, 2122, "North Shore"), (2123, 2129, "Western Sydney"), (2130, 2140, "Inner West"),
                        (2141, 2161, "Western Sydney"), (2162, 2179, "South-West Sydney"), (2190, 2200, "South-West Sydney"), (2203, 2204, "Inner West"),
                        (2205, 2234, "St George and Sutherland"), (2555, 2574, "South-West Sydney"), (2740, 2772, "Western Sydney"),
                        (2773, 2786, "Blue Mountains"), (2250, 2263, "Central Coast"), (2264, 2339, "Newcastle and Hunter Valley"),
                        (2500, 2551, "Illawarra and South Coast")]:
            if a <= p <= b:
                return r
        return "Regional and rural NSW" if 2000 <= p <= 2999 else ""
    if 3000 <= p <= 3006 or p == 3008:
        return "Melbourne CBD"
    metro = [(3000, 3207), (3335, 3338), (3427, 3429), (3750, 3755), (3757, 3761), (3765, 3815), (3910, 3920), (3926, 3944), (3975, 3978), (3800, 3810), (8000, 8999)]
    if any(a <= p <= b for a, b in metro):
        return "Metropolitan Melbourne"
    for a, b, r in [(3211, 3249, "Geelong and Barwon"), (3250, 3319, "Western District"), (3320, 3399, "Ballarat and Central Highlands"),
                    (3400, 3426, "Wimmera"), (3430, 3499, "Macedon Ranges and Central Victoria"), (3500, 3599, "Loddon Mallee and Bendigo"),
                    (3600, 3699, "Goulburn Valley and Hume"), (3700, 3749, "North East"), (3756, 3756, "Macedon Ranges and Central Victoria"),
                    (3762, 3764, "Goulburn Valley and Hume"), (3816, 3909, "Gippsland"), (3921, 3925, "Gippsland"), (3945, 3974, "Gippsland"),
                    (3979, 3999, "Gippsland")]:
        if a <= p <= b:
            return r
    return ""

# ---------- load sources ----------
caarp_list, caarp_det = [], {}
for f in sorted(glob.glob(os.path.join(R, "caarp-part*.json")) or glob.glob(os.path.join(ROOT, "research", "vic", "caarp-part*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    caarp_list = caarp_list or d.get("list", [])
    for x in d.get("details", []):
        caarp_det[x["id"]] = x
CTF = os.path.join(R, "cinematreasures.json")
CT = json.load(open(CTF, encoding="utf-8"))["theaters"] if os.path.exists(CTF) else []
FIXF = os.path.join(R, "cinematreasures-fix.json")
FIX = json.load(open(FIXF, encoding="utf-8"))["fix"] if os.path.exists(FIXF) else {}
for i, t in enumerate(CT):                       # the first 142 rows came from the 'Open' listing; detail parse may have blanked status
    f = FIX.get(t["id"])
    if f and f.get("pc"):
        t["addr"] = f"{f['addr']}, {f.get('st') or STATE} {f['pc']}"; t["size"] = f.get("size") or t.get("size")
        t["status"] = "Open" if f.get("status", "").startswith("Open") else (f.get("status") or "").split(" ")[0]
    if not t.get("status"):
        t["status"] = "Open" if i < 142 else ""
VHD = json.load(open(os.path.join(R, "vhd.json"), encoding="utf-8"))["places"] if os.path.exists(os.path.join(R, "vhd.json")) else []
GEO, PC2 = defaultdict(list), defaultdict(list)          # GeoNames VIC postal localities (CC BY 4.0)
GF = os.path.join(R, f"geonames-{STATE.lower()}.json")
for pc, place, lat, lon in (json.load(open(GF, encoding="utf-8"))["rows"] if os.path.exists(GF) else []):
    GEO[norm(place)].append([lat, lon, place, pc]); PC2[pc].append(place)
CBD = {"VIC": {"3000", "3001", "3002", "3003", "3004", "3005", "3006", "3008"}, "NSW": {"2000", "2001"}}[STATE]
CAPITAL = {"VIC": "melbourne", "NSW": "sydney"}[STATE]
METRO_CT = lambda city, pc: norm(city) == CAPITAL and pc and pc not in CBD
# NSW discovery batch 01 (76 candidates; 73 already published as leads, 3 identified as existing records)
B01 = []
if STATE == "NSW" and os.path.exists(os.path.join(R, "NSW_CANDIDATES.json")):
    B01 = json.load(open(os.path.join(R, "NSW_CANDIDATES.json"), encoding="utf-8"))

raw = open("assets/map/cinema-sites.js", encoding="utf-8").read()
SITES = [s for s in json.loads(raw[raw.index("window.APA_SITES = ") + 19:].strip().rstrip(";"))["sites"] if s["state"] == STATE]
# already published in this state: archive listings and research leads (not this expansion's own export)
for a in json.load(open("assets/data/archive-listings.json", encoding="utf-8")):
    if a["state"] == STATE:
        SITES.append({"id": "archive:" + a["id"], "name": a["name"], "aliases": [], "suburb": a["locality"], "address": a.get("address", "")})
for f in glob.glob("assets/data/leads-*.json"):
    if f.endswith(f"leads-{STATE.lower()}-expansion.json") or f.endswith("leads-vic.json"):
        continue
    for l in json.load(open(f, encoding="utf-8")):
        if l["state"] == STATE:
            SITES.append({"id": "lead:" + l["id"], "name": l["name"], "aliases": l.get("aliases", []), "suburb": l["locality"], "address": l.get("address", "")})

def is_vic_caarp(v, det):
    pc = (re.match(r"\d{4}", v.get("pc") or "") or [""])[0]
    if pc:
        return PC_OK(pc)
    return bool(det and any(norm(x) == STATE_WORD for x in det.get("addr", [])))

# ---------- candidate rows (one per source entry) ----------
cands = []
for v in caarp_list:
    det = caarp_det.get(v["id"])
    if not is_vic_caarp(v, det):
        continue
    full = v["name"]
    base, _, place = full.partition(", ")
    names = [n.strip() for n in base.split(" / ") if n.strip()]
    loc = (v.get("suburb") or place or "").strip()
    c = {"src": "caarp", "sid": v["id"], "name": names[0] if names else full, "aliases": names[1:], "locality": loc,
         "address": (v.get("address") or "").strip().rstrip(","), "postcode": (re.match(r"\d{4}", v.get("pc") or "") or [""])[0], "url": f"https://caarp.com.au/venue/view/{v['id']}"}
    if det:
        evn = []
        for e in det.get("ev", []):
            n = (e[1] or "").strip()
            if n and n not in evn:
                evn.append(n)
        c["aliases"] += [n for n in evn if norm(n) != norm(c["name"])]
        m = re.match(r"(\d{4}-\d{2}-\d{2}) - (\d{4}-\d{2}-\d{2})", det.get("dates") or "")
        if m:
            c["open_listed"] = m.group(1)
            c["close_listed"] = "" if m.group(2).startswith("9999") else m.group(2)
            c["still_listed"] = m.group(2).startswith("9999")
        c["capacity"] = det.get("cap") or ""
        c["screens"] = det.get("screens") or ""
        c["purpose"] = det.get("purpose") or ""
        c["setting"] = det.get("sc") or ""
        c["caarp_note"] = det.get("comment") or ""
        c["caarp_refs"] = det.get("refs") or []
        ll = [(e[3], e[4]) for e in det.get("ev", []) if re.fullmatch(r"-?\d+\.\d+", e[3] or "") and re.fullmatch(r"-?\d+\.\d+", e[4] or "")]
        if ll:
            c["caarp_geocode"] = [float(ll[0][0]), float(ll[0][1])]
        c["detail"] = True
    cands.append(c)

for t in CT:
    city = (t.get("city") or "").replace(", Australia", "").strip()
    pcm = re.search(r"\b(?:VIC|NSW|ACT) (\d{4})\b", t.get("addr") or "")
    parts = [x.strip() for x in (t.get("addr") or "").split(",") if x.strip()]
    if parts and re.match(r"(?:VIC|NSW|ACT) \d{4}", parts[-1]):
        parts = parts[:-1]
    if len(parts) >= 2 and norm(parts[-1]) == norm(city):
        parts = parts[:-1]
    addr = ", ".join(parts)
    if pcm and METRO_CT(city, pcm.group(1)):
        places = sorted(set(PC2.get(pcm.group(1), [])))
        hit = [x for x in places if norm(x) and re.search(r"\b" + re.escape(norm(x)) + r"\b", norm(t["name"] + " " + addr))]
        city = max(hit, key=len) if hit else (places[0] if len(places) == 1 else "")   # Cinema Treasures files metro venues under the capital
    info = t.get("info") or ""
    prev = re.search(r"Previous Names: \| ([^|]+)", info)
    ops = re.search(r"(?:Previously operated by|Operated by): \| ([^|]+)", info)
    sty = re.search(r"Styles: \| ([^|]+)", info); arch = re.search(r"Architects: \| ([^|]+)", info)
    seats = re.search(r"(\d[\d,]*) seats", t.get("size") or "")
    cars = re.search(r"(\d[\d,]*) cars", t.get("size") or "")
    if pcm and not PC_OK(pcm.group(1)):
        continue
    cands.append({"src": "ct", "sid": t["id"], "name": t["name"], "aliases": [x.strip() for x in prev.group(1).split(",")] if prev else [],
                  "locality": city, "address": addr if re.search(r"\d|street|road|avenue|parade|highway", addr, re.I) else "",
                  "postcode": pcm.group(1) if pcm else "", "ct_status": t.get("status") or "",
                  "operators": [x.strip() for x in ops.group(1).split(",")] if ops else [],
                  "style": sty.group(1).strip() if sty else "", "architects": arch.group(1).strip() if arch else "",
                  "capacity": (seats.group(1).replace(",", "") if seats else (cars.group(1).replace(",", "") + " cars" if cars else "")),
                  "screens": t.get("screens") or "", "url": f"https://cinematreasures.org/theaters/{t['id']}"})

for b in B01:
    cands.append({"src": "b01", "sid": b["candidate_id"], "name": b["name"].split(" / ")[0], "aliases": [x.strip() for x in b["name"].split(" / ")[1:]],
                  "locality": b["locality"], "address": "", "postcode": "", "url": b["source_url"], "b01_level": b["verification_level"]})
KNOWN_LOC = {norm(c["locality"]) for c in cands if c["locality"]} | set(GEO) | \
    {k.split("|")[0] for k in json.load(open(os.path.join(ROOT, "assets", "data", "au-localities.json"), encoding="utf-8")) if k.endswith("|" + STATE)}
LOC2PC = {}
for c in cands:
    if c["locality"] and c["postcode"]:
        LOC2PC.setdefault(norm(c["locality"]), c["postcode"])
CINEMA_WORDS = re.compile(r"cinema|picture|drive.?in|theatrette|photoplay|kinema|movie|biograph", re.I)
for p in VHD:
    if p.get("err") or not p.get("title"):
        continue
    if re.search(r"organ|wurlitzer|service station|lecture", p["title"], re.I):
        continue
    raw_a = p.get("addr") or ""
    if raw_a.startswith("All information"):
        raw_a = ""
    pcv = ""
    m = re.match(r"(.*?),*\s*([A-Za-z][A-Za-z' ]+?)\s+VIC\s+(\d{4})", raw_a)
    if m:
        street, loc, pcv = m.group(1).strip(" ,"), m.group(2).title(), m.group(3)
    else:
        a = raw_a.split(",")[0]
        tm = re.search(r",\s*([^,]+)$", p["title"])
        words = norm(a).split()
        loc = ""
        for k in range(min(4, len(words)), 0, -1):
            cand = " ".join(words[-k:])
            if cand in KNOWN_LOC:
                loc = cand; break
        if not loc and tm and norm(tm.group(1)) in KNOWN_LOC:
            loc = norm(tm.group(1))
        street = " ".join(a.split()[:len(words) - len(loc.split())]) if loc and a else a
        loc = loc.title()
    auth = p.get("authority") or ""
    if auth not in ("Victorian Heritage Register", "Victorian Heritage Inventory", "National Trust"):
        auth = "Local heritage listing"
    title = re.sub(r"\s*\((former)\)|^former\s+|,\s*[^,]*\d[^,]*,\s*[^,]+$", "", p["title"], flags=re.I).strip()
    cands.append({"src": "vhd", "sid": p["id"], "name": title.title() if title.isupper() else title, "aliases": [], "locality": loc,
                  "address": street.title() if street.isupper() else street, "postcode": pcv, "listing": auth,
                  "vhr": p.get("vhr") if auth == "Victorian Heritage Register" else "", "ho": p.get("ho") or "",
                  "cinema_word": bool(CINEMA_WORDS.search(p["title"])), "url": f"https://vhd.heritagecouncil.vic.gov.au/places/{p['id']}"})

# ---------- matching ----------
def same_place(a, b):
    for x, y in ((a, b), (b, a)):                     # one side has only a postcode, the other only a locality
        if x["postcode"] and not x["locality"] and y["locality"] and not y["postcode"]:
            return norm(y["locality"]) in {norm(p) for p in PC2.get(x["postcode"], [])}
    if a["postcode"] and b["postcode"]:
        if a["postcode"] != b["postcode"]:
            return False
        return (not a["locality"] or not b["locality"] or norm(a["locality"]) == norm(b["locality"]))
    return bool(norm(a["locality"])) and norm(a["locality"]) == norm(b["locality"])

def match(a, b):
    """Return a reason string if a and b describe the same venue, else ''."""
    if not same_place(a, b):
        return ""
    na, sa = street_key(a["address"]); nb, sb = street_key(b["address"])
    ta = core_tokens(a["name"], a["locality"]) | {t for x in a["aliases"] for t in core_tokens(x, a["locality"])}
    tb = core_tokens(b["name"], b["locality"]) | {t for x in b["aliases"] for t in core_tokens(x, b["locality"])}
    name_hit = bool(ta & tb)
    loc_words = set(norm(a["locality"]).split())
    def plain(n): return " ".join(w for w in norm(n).split() if w not in loc_words and not w.isdigit())
    pa = {plain(x) for x in [a["name"]] + a["aliases"]} - {""}; pb = {plain(x) for x in [b["name"]] + b["aliases"]} - {""}
    if not ta and not tb and pa & pb:
        name_hit = True                                  # e.g. "Garfield Picture Theatre" / "Garfield Picture Theatre"
    drive = lambda c: bool(re.search(r"drive.?in", " ".join([c["name"]] + c["aliases"]), re.I))
    if drive(a) and drive(b) and name_hit:
        return "drive-in with the same name in the same locality"
    if sa and sb:
        if sa != sb:
            import difflib
            if na and nb and na == nb and difflib.SequenceMatcher(None, sa, sb).ratio() >= 0.85:
                return "same street number, street name spelt differently"
            return ""
        if na and nb and na != nb:
            return "same street, nearby number, same name" if name_hit and abs(int(na) - int(nb)) <= 10 else ""
        return "same street address" if (na and nb) else ("same street and name" if name_hit else "")
    if name_hit:
        cbd = {a["postcode"], b["postcode"]} & CBD or norm(a["locality"]) == CAPITAL
        if cbd and not (pa & pb):
            return ""                                  # central Melbourne: too many venues to match on a partial name without an address
        return "same name and locality (no address to compare)"
    if not ta and not tb and norm(a["name"]) == norm(b["name"]) and plain(a["name"]):
        return "identical name and locality"
    return ""

parent = list(range(len(cands)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
dups = []
by_loc = defaultdict(list)
for i, c in enumerate(cands):
    by_loc[c["postcode"] or norm(c["locality"])].append(i)
    if c["postcode"] and c["locality"]:
        by_loc[norm(c["locality"])].append(i)          # also compare with rows that only have a locality
members = defaultdict(set)
for i, c in enumerate(cands):
    members[i].add(f"{c['src']}:{c['sid']}")
for loc, idx in by_loc.items():
    for x in range(len(idx)):
        for y in range(x + 1, len(idx)):
            a, b = cands[idx[x]], cands[idx[y]]
            if a["src"] == b["src"] == "caarp" and a["address"] and b["address"] and norm(a["address"]) != norm(b["address"]):
                continue
            r = match(a, b)
            if r:
                ra, rb = find(idx[x]), find(idx[y])
                if ra == rb:
                    continue
                srcs_a = {m.split(":")[0] for m in members[ra] if m.split(":")[0] != "vhd"}
                srcs_b = {m.split(":")[0] for m in members[rb] if m.split(":")[0] != "vhd"}
                if srcs_a & srcs_b and r != "same street address":
                    continue                              # two distinct venues from the same source: only merge on a street address
                if len(members[ra]) + len(members[rb]) > 6:
                    continue                              # guard against chains
                if True:
                    parent[rb] = ra; members[ra] |= members[rb]
                    dups.append([f"{a['src']}:{a['sid']}", a["name"], f"{b['src']}:{b['sid']}", b["name"], loc, r])

groups = defaultdict(list)
for i in range(len(cands)):
    groups[find(i)].append(cands[i])

# ---------- consolidate ----------
STATUS_LABEL = {"operating": "Operating cinema", "repurposed": "Building survives, other use", "demolished": "Demolished", "closed": "Closed or not stated"}
existing = []
recs = []
for g in groups.values():
    g.sort(key=lambda c: {"caarp": 0, "ct": 1, "vhd": 2, "b01": 3}[c["src"]])
    srcs = {c["src"] for c in g}
    if srcs == {"vhd"} and not any(c.get("cinema_word") for c in g):
        continue                                  # heritage place with no evidence of film exhibition
    if not any(c["locality"] or c["postcode"] for c in g):
        continue                                  # no usable place (a heritage page without an address)
    if all(c["src"] == "caarp" and not c["postcode"] for c in g) and not any(norm(c["locality"]) in GEO for c in g):
        continue                                  # CAARP row without a Victorian postcode or locality (e.g. Parap, NT)
    first = g[0]
    names = []
    for c in g:
        for n in [c["name"]] + c["aliases"]:
            n = n.strip()
            if n and norm(n) not in {norm(x) for x in names}:
                names.append(n)
    loc = next((c["locality"] for c in g if c["locality"] and not (norm(c["locality"]) == CAPITAL and c["postcode"] and c["postcode"] not in CBD)), "")
    pc = next((c["postcode"] for c in g if c["postcode"]), "")
    if not loc and pc and not PC2.get(pc):                 # capital-city filing with a suburban postcode and no gazetteer: use a suburb named in the venue name
        inname = sorted((k for k in KNOWN_LOC if k and k != CAPITAL and any(re.search(r"\b" + re.escape(k) + r"\b", norm(n)) for n in names)), key=len, reverse=True)
        loc = inname[0].title() if inname else ""
    if not loc and pc:
        places = sorted({x for x in PC2.get(pc, []) if not re.search(r"\b(po|dc|mc|bc|lpo|mail centre|delivery centre)\b", x, re.I)})
        named = [x for x in places if any(norm(x) and norm(x) in norm(n) for n in names)]
        loc = named[0] if named else (places[0] if len(places) == 1 else "")
        loc_note = "" if loc else f"{CAPITAL.title()} (postcode {pc})"
    else:
        loc_note = ""
    if not pc:
        pc = LOC2PC.get(norm(loc), "")
    if not pc and norm(loc) in GEO:
        pcs = {x[3] for x in GEO[norm(loc)]}
        pc = pcs.pop() if len(pcs) == 1 else ""
    addrs = [c["address"] for c in g if c["address"]]
    ct = next((c for c in g if c["src"] == "ct"), None)
    vh = [c for c in g if c["src"] == "vhd"]
    ca = next((c for c in g if c["src"] == "caarp"), None)
    status, status_src = "closed", "No source states the current status"
    if ct and ct.get("ct_status") == "Open":
        status, status_src = "operating", "Cinema Treasures lists it as open"
    elif any(v.get("listing") in ("Victorian Heritage Register", "Victorian Heritage Inventory") or v.get("ho") for v in vh):
        status, status_src = "repurposed", "The building is heritage-listed (Victorian Heritage Database); current use not checked"
    elif ct and ct.get("ct_status") == "Closed":
        status, status_src = "closed", "Cinema Treasures lists it as closed (it does not say whether the building survives)"
    nm = " ".join(names).lower()
    kind = "drive-in" if re.search(r"drive.?in", nm) else "open-air" if re.search(r"open.?air|picture garden|gardens", nm) else \
           "hall" if (ca and ca.get("purpose") in ("Hall", "Mechanics Institute", "Dance Hall")) or re.search(r"\bhall\b|institute", nm) else "cinema"
    if any(c.get("purpose") == "Live Theatre" for c in g) and kind == "cinema":
        kind = "theatre"
    primary = next((n for n in names if norm(n) != norm(loc) and plain_name(n, loc)), names[0])
    names = [primary] + [n for n in names if n != primary]
    rec = {
        "name": names[0], "aliases": names[1:], "locality": loc, "locality_note": loc_note, "postcode": pc, "state": STATE,
        "region": pc_region(pc) or pc_region(next((x[3] for x in GEO.get(norm(loc), [])), "")) or (f"Metropolitan {CAPITAL.title()}" if ca and ca.get("setting") in ("City", "Suburb") else f"Regional {STATE}" if ca and ca.get("setting") == "Country" else ""),
        "address": addrs[0] if addrs else "", "other_addresses": sorted(set(addrs[1:]) - {addrs[0]}) if addrs else [],
        "type": kind,
        "first_listed": ca.get("open_listed", "") if ca else "", "last_listed": ca.get("close_listed", "") if ca else "",
        "dates_basis": "CAARP operation dates (usually first and last directory or newspaper listing)" if ca and ca.get("open_listed") else "",
        "status": status, "status_label": STATUS_LABEL[status], "status_basis": status_src,
        "capacity": next((c["capacity"] for c in g if c.get("capacity")), ""), "screens": next((c["screens"] for c in g if c.get("screens")), ""),
        "operators": sorted({o for c in g for o in c.get("operators", [])}),
        "heritage": [{"listing": v.get("listing"), "vhr": v.get("vhr"), "ho": v.get("ho"), "url": v["url"]} for v in vh],
        "geocode_unverified": ca.get("caarp_geocode") if ca else None,
        "sources": [{"source": {"caarp": "CAARP", "ct": "Cinema Treasures", "vhd": "Victorian Heritage Database", "b01": "NSW discovery batch 01"}[c["src"]], "id": c["sid"], "url": c["url"]} for c in g],
        "style": next((c["style"] for c in g if c.get("style")), ""), "architects": next((c["architects"] for c in g if c.get("architects")), ""),
        "photographs": "none cleared for use",
        "caarp_note": ca.get("caarp_note", "") if ca else "", "caarp_refs": ca.get("caarp_refs", []) if ca else [],
        "detail_collected": bool(ca and ca.get("detail")) if ca else None,
    }
    n_src = len(srcs)
    rec["evidence"] = ("heritage register names the place" if vh and any(v.get("cinema_word") for v in vh) else
                       "two independent sources agree" if n_src >= 2 else "single source")
    numbered = any(street_key(a)[0] for a in addrs)
    conflict = len({street_key(a)[1] for a in addrs if street_key(a)[1]}) > 1
    if conflict:
        rec["proposed_level"] = "E"; rec["level_reason"] = "sources give different addresses"
    elif (vh and numbered) or (n_src >= 2 and numbered):
        rec["proposed_level"] = "B"; rec["level_reason"] = "street address documented by a heritage listing or by two independent sources"
    elif rec["address"]:
        rec["proposed_level"] = "C"; rec["level_reason"] = "provisional historical address from one source"
    else:
        rec["proposed_level"] = "D"; rec["level_reason"] = "cinema name and locality established; no address"
    rec["review"] = "awaiting editorial review"
    # existing website record?
    hit = None; rec_possible = False
    b01_own = {"lead:" + c["sid"].lower() for c in g if c["src"] == "b01"}
    own = next((s for s in SITES if s["id"] in b01_own), None)
    for s in ([own] if own else SITES):
        if norm(s["suburb"]) != norm(loc):
            continue
        st = core_tokens(s["name"], loc) | {t for a in s.get("aliases", []) for t in core_tokens(a, loc)}
        primary = core_tokens(names[0], loc)
        same_addr = s.get("address") and any(street_key(a)[0] and street_key(a) == street_key(s["address"]) for a in addrs)
        nums_r = {street_key(a)[0] for a in addrs if street_key(a)[0]}
        num_s = street_key(s.get("address") or "")[0]
        if num_s and nums_r and all(abs(int(n) - int(num_s)) > 10 for n in nums_r):
            continue                                      # same name, different building (e.g. Capitol 2 at 125 Swanston Street)
        b01_ids = {c["sid"].lower() for c in g if c["src"] == "b01"}
        if s["id"].startswith("lead:") and s["id"][5:] in b01_ids:
            hit = s; rec_possible = False; break           # the batch-01 candidate that became this published lead
        if (st & primary) or same_addr:
            hit = s
            # research leads have no addresses to compare: a name and locality match is treated as the same venue
            rec_possible = not same_addr and not (num_s and nums_r) and not s["id"].startswith("lead:")
            break
    if hit:
        existing.append([hit["id"], hit["name"], names[0], loc, "; ".join(f"{x['source']}:{x['id']}" for x in rec["sources"])])
        rec["existing_record"] = hit["id"]
        rec["existing_match"] = "possible, check" if rec_possible else "same venue"
        if rec_possible:
            rec["proposed_level"] = "E"; rec["level_reason"] = f"possible identity conflict with existing {hit['id']}"
    recs.append(rec)

by_hit = defaultdict(list)
for r in recs:
    if r.get("existing_match") == "same venue":
        by_hit[r["existing_record"]].append(r)
for hid, rs in by_hit.items():
    if len(rs) < 2:
        continue
    streets = {street_key(r["address"])[1] for r in rs if r["address"] and street_key(r["address"])[1]}
    if len(streets) <= 1:
        continue                                     # same street or no addresses: same venue under different names
    keep = next((r for r in rs if any(s["source"] == "NSW discovery batch 01" for s in r["sources"])), rs[0])
    keep_street = street_key(keep["address"])[1]
    for r in rs:
        if r is keep or not r["address"] or street_key(r["address"])[1] == keep_street:
            continue
        r["existing_match"] = "possible, check"; r["proposed_level"] = "E"
        r["level_reason"] = f"same name as existing {hid} in this locality but a different address; may be a second venue"
recs.sort(key=lambda r: (norm(r["locality"]), norm(r["name"])))
# stable ids: keep any id already assigned to the same first source in a previous build
prev = {}
if os.path.exists(os.path.join(R, f"{STATE.lower()}-master.json")):
    for r in json.load(open(os.path.join(R, f"{STATE.lower()}-master.json"), encoding="utf-8"))["records"]:
        for s in r["sources"]:
            prev[f"{s['source']}:{s['id']}"] = r["fca_id"]
used, nxt = set(), 1 + max([int(v.split("-")[-1]) for v in prev.values() if re.fullmatch(r"FCA-[A-Z]+-\d{4}", v)] or [0])
for r in recs:
    pid = next((prev[f"{s['source']}:{s['id']}"] for s in r["sources"] if f"{s['source']}:{s['id']}" in prev and prev[f"{s['source']}:{s['id']}"] not in used), None)
    if not pid:
        pid = f"FCA-{STATE}-{nxt:04d}"; nxt += 1
    used.add(pid); r["fca_id"] = pid

new = [r for r in recs if not r.get("existing_record")]
summary = {
    "state": STATE, "original_records": sum(1 for s in SITES if ":" not in s["id"]), "original_archive_listings": sum(1 for s in SITES if s["id"].startswith("archive:")),
    "original_research_leads": sum(1 for s in SITES if s["id"].startswith("lead:")), "original_ids": [s["id"] for s in SITES],
    "source_rows": dict(Counter(c["src"] for c in cands)),
    "caarp_details_collected": sum(1 for c in cands if c["src"] == "caarp" and c.get("detail")),
    "caarp_details_missing": [c["sid"] for c in cands if c["src"] == "caarp" and not c.get("detail")],
    "merges_between_source_rows": len(dups), "matched_existing_records": len(existing),
    "unique_records": len(recs), "new_unique_records": len(new),
    "by_region": dict(Counter(r["region"] or "Unknown" for r in new)), "by_status": dict(Counter(r["status"] for r in new)),
    "by_type": dict(Counter(r["type"] for r in new)), "by_proposed_level": dict(Counter(r["proposed_level"] for r in new)),
    "by_evidence": dict(Counter(r["evidence"] for r in new)),
}
json.dump({"generated_by": "tools/expansion/build_state_db.py", "summary": summary, "records": recs}, open(os.path.join(R, f"{STATE.lower()}-master.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
cols = ["fca_id", "name", "aliases", "locality", "postcode", "region", "address", "other_addresses", "type", "first_listed", "last_listed", "dates_basis",
        "status_label", "status_basis", "capacity", "screens", "operators", "heritage", "evidence", "proposed_level", "review", "existing_record", "sources"]
with open(os.path.join(R, f"{STATE.lower()}-master.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(cols)
    for r in recs:
        w.writerow([("; ".join(r.get(k) or []) if k in ("aliases", "other_addresses", "operators") else
                     "; ".join(f"{h['listing']} {h['vhr'] or h['ho']}".strip() for h in r["heritage"]) if k == "heritage" else
                     "; ".join(s["url"] for s in r["sources"]) if k == "sources" else r.get(k, "")) for k in cols])
with open(os.path.join(R, f"{STATE.lower()}-duplicates.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["kind", "a", "a_name", "b", "b_name", "locality", "reason"])
    for d in dups: w.writerow(["merged source rows"] + d)
    for e in existing: w.writerow(["already on the website", f"record:{e[0]}", e[1], e[4], e[2], e[3], "same name and locality"])
json.dump(summary, open(os.path.join(R, f"{STATE.lower()}-progress.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k not in ("caarp_details_missing", "original_ids")}, indent=1))
print("CAARP details still missing:", len(summary["caarp_details_missing"]))
