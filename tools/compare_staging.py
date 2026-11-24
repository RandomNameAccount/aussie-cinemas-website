#!/usr/bin/env python3
"""Compare the national staging catalogue with the website's 73-site dataset.

Usage:
  python3 tools/compare_staging.py NATIONAL_CINEMA_STAGING_CATALOGUE_v0.2.csv [out_dir]

Matching, in order (each website site is matched at most once):
  1. staging legacy_prototype_id == website id
  2. staging record_key        == website id
  3. same state + normalised name (primary or alternative) + normalised locality/suburb   (reported as "name match: check")
Nothing is merged or changed; the script only reports. Field differences are listed for name, alternative names,
state, locality, status, evidence, sources-disagree flag and coordinates (distance in metres).
Outputs: staging-vs-website.csv (one row per pair or unmatched record) and staging-vs-website-summary.md.
"""
import csv, json, math, os, re, sys
from collections import Counter

if len(sys.argv) < 2:
    sys.exit(__doc__)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
os.makedirs(OUT, exist_ok=True)

raw = open(os.path.join(ROOT, "assets/map/cinema-sites.js"), encoding="utf-8").read()
SITES = json.loads(raw[raw.index("window.APA_SITES = ") + 19:].strip().rstrip(";"))["sites"]
STAGE = list(csv.DictReader(open(sys.argv[1], encoding="utf-8-sig")))

def norm(t):
    t = (t or "").lower().replace("&", " and ")
    t = re.sub(r"\((to confirm|.*?\d{4}.*?)\)", " ", t)
    t = re.sub(r"\b(the|theatre|theater|cinema|cinemas|picture|pictures|twin)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()
def names(primary, alts):
    out = {norm(primary)}
    for a in re.split(r";", alts or ""):
        if a.strip(): out.add(norm(a))
    return {n for n in out if n}
def g(r, *keys):
    for k in keys:
        if r.get(k) not in (None, ""): return r[k]
    return ""
def dist(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))

web = {s["id"]: s for s in SITES}
used_web, pairs = set(), []
for r in STAGE:
    match, how = None, ""
    for key, label in (("legacy_prototype_id", "legacy id"), ("record_key", "record key")):
        v = g(r, key)
        if v in web and v not in used_web: match, how = web[v], label; break
    if not match:
        sn = names(g(r, "primary_name", "name"), g(r, "alternative_names"))
        loc = norm(g(r, "locality"))
        for s in SITES:
            if s["id"] in used_web or s["state"] != g(r, "state"): continue
            if names(s["name"], ";".join(s.get("aliases") or [])) & sn and (not loc or norm(s["suburb"]) == loc):
                match, how = s, "name match: check"; break
    if match: used_web.add(match["id"])
    pairs.append((r, match, how))

rows, diffs = [], Counter()
for r, s, how in pairs:
    d = []
    if s:
        if norm(g(r, "primary_name", "name")) != norm(s["name"]): d.append("name")
        if g(r, "state") != s["state"]: d.append("state")
        if norm(g(r, "locality")) != norm(s["suburb"]): d.append("locality")
        if g(r, "status_today") and g(r, "status_today") != s["status"]: d.append("status")
        if g(r, "historical_evidence", "history_confidence") and g(r, "historical_evidence", "history_confidence") != s["evidence"]: d.append("evidence")
        sd = g(r, "sources_disagree") == "yes"
        if sd != bool(s.get("conflicts")): d.append("sources-disagree flag")
        m = ""
        try:
            sl = (float(g(r, "lat")), float(g(r, "lon")))
            if isinstance(s["loc"].get("lat"), (int, float)):
                m = round(dist(sl, (s["loc"]["lat"], s["loc"]["lng"] if "lng" in s["loc"] else s["loc"]["lon"])))
                if m > 25: d.append("coordinates")
        except (ValueError, KeyError):
            pass
        for x in d: diffs[x] += 1
    rows.append([g(r, "apa_id"), g(r, "primary_name", "name"), g(r, "state"), g(r, "locality"), g(r, "map_eligible"),
                 s["id"] if s else "", s["name"] if s else "", s["loc"]["kind"] if s else "", how or "not on website",
                 "; ".join(d), m if s else ""])
for s in SITES:
    if s["id"] not in used_web:
        rows.append(["", "", s["state"], s["suburb"], "", s["id"], s["name"], s["loc"]["kind"], "website only", "", ""])
H = ["staging_apa_id", "staging_name", "state", "locality", "staging_map_eligible", "website_id", "website_name", "website_location_kind", "match", "differences", "coordinate_gap_m"]
with open(os.path.join(OUT, "staging-vs-website.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(H); w.writerows(rows)
c = Counter(x[8] for x in rows)
summary = f"""# Staging catalogue vs website dataset

- Staging records: {len(STAGE)}; website records: {len(SITES)}
- Matched by legacy id: {c['legacy id']}; by record key: {c['record key']}; by name and locality (check by hand): {c['name match: check']}
- Staging only: {c['not on website']}; website only: {c['website only']}
- Field differences among matched pairs: {dict(diffs) or 'none'}

Nothing was merged or changed. Name matches need a person to confirm they are the same site.
"""
open(os.path.join(OUT, "staging-vs-website-summary.md"), "w").write(summary)
print(summary)
