#!/usr/bin/env python3
"""Export the Victorian master database (research/vic/vic-master.json) to the website's research-lead format
(assets/data/leads-vic.json), and add Victorian towns to the approximate-location gazetteer.

Every Victorian entry is published to staging as a research lead awaiting editorial review. Records that are the
same venue as an existing website record are not exported (the record already covers them). Facts carry their source;
nothing is filled in that a source does not state.
"""
import json, os, re, unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(ROOT)
STATE = os.environ.get("FCA_STATE", "VIC").upper()
M = json.load(open(f"research/{STATE.lower()}/{STATE.lower()}-master.json", encoding="utf-8"))["records"]
OUT = {"VIC": "assets/data/leads-vic.json"}.get(STATE, f"assets/data/leads-{STATE.lower()}-expansion.json")
MONTHS = "January February March April May June July August September October November December".split()

def nice_date(d):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", d or "")
    if not m: return ""
    y, mo, da = m.groups()
    if mo == "01" and da == "01": return y                      # CAARP uses 1 January when only the year is known
    return f"{int(da)} {MONTHS[int(mo) - 1]} {y}"

def basis(r):
    srcs = [s["source"] for s in r["sources"]]
    n = len(set(srcs))
    if r["evidence"] == "heritage register names the place":
        return "A Victorian heritage listing names this place, and the other details come from the sources listed below. Nothing has been checked by an editor yet."
    if n >= 2:
        return f"Recorded independently by {' and '.join(sorted(set(srcs)))}, which agree on the name and place. Dates and other details are as those sources give them and are not yet checked."
    if "CAARP" in srcs:
        return "Recorded in the CAARP research database (Cinema and Audience Research Project), usually from directory and newspaper listings. Not yet checked against a second source."
    if "Cinema Treasures" in srcs:
        return "Listed on Cinema Treasures, a volunteer-edited directory. Needs a primary source for this venue."
    return "Named in the Victorian Heritage Database; film exhibition and dates are not yet checked."

def summary(r):
    """One or two plain sentences written from the structured facts (no source text is copied)."""
    kind = {"drive-in": "drive-in", "open-air": "open-air picture venue", "hall": "hall used for film screenings", "theatre": "theatre that screened films"}.get(r["type"], "cinema")
    where = f" at {r['address']}" if r["address"] else ""
    loc = r["locality"] or r.get("locality_note") or ""
    s1 = f"{r['name']} was a {kind}{where}{', ' + loc if loc else ''}."
    if r["status"] == "operating":
        s1 = f"{r['name']} is a {kind}{where}{', ' + loc if loc else ''}, listed as operating."
    bits = []
    if r["first_listed"] and r["last_listed"]:
        bits.append(f"CAARP lists it from {nice_date(r['first_listed'])} to {nice_date(r['last_listed'])}")
    elif r["first_listed"]:
        bits.append(f"CAARP first lists it in {nice_date(r['first_listed'])}")
    if r["capacity"]:
        bits.append(f"with {r['capacity']}{'' if 'car' in r['capacity'] else ' seats'} recorded")
    if r["aliases"]:
        bits.append(f"it was also known as {', '.join(r['aliases'][:3])}")
    return s1 + (" " + "; ".join(bits).capitalize() + "." if bits else "")

out = []
for r in M:
    if r.get("existing_match") == "same venue":
        continue                                   # already on the site as a record, archive listing or research lead
    facts = []
    if r["first_listed"]:
        facts.append(["Opened", f"{nice_date(r['first_listed'])} (first listing in CAARP, not verified)"])
    if r["last_listed"]:
        facts.append(["Closed", f"{nice_date(r['last_listed'])} (last listing in CAARP, not verified)"])
    if r["capacity"]:
        facts.append(["Capacity", f"{r['capacity']}{'' if 'car' in r['capacity'] else ' seats'} (as recorded by {('CAARP' if any(s['source']=='CAARP' for s in r['sources']) else 'Cinema Treasures')})"])
    if r["screens"] and r["screens"] not in ("", "1"):
        facts.append(["Screens", r["screens"]])
    if r.get("style"):
        facts.append(["Architectural style", r["style"] + " (Cinema Treasures)"])
    if r.get("architects"):
        facts.append(["Architects", r["architects"] + " (Cinema Treasures)"])
    if r["operators"]:
        facts.append(["Operators", ", ".join(r["operators"]) + " (Cinema Treasures)"])
    for h in r["heritage"]:
        ref = h.get("vhr") or h.get("ho") or ""
        facts.append(["Heritage listing", f"{h['listing']}{' ' + ref if ref else ''} (Victorian Heritage Database)"])
    if r["other_addresses"]:
        facts.append(["Other addresses recorded", "; ".join(r["other_addresses"][:4])])
    conflicts = []
    if r.get("existing_match") == "possible, check":
        conflicts.append(f"May be the same venue as, or closely linked to, the website record '{r['existing_record']}'; an editor needs to check.")
    if len(r["other_addresses"]) >= 1:
        conflicts.append("The sources give more than one address.")
    sources = []
    for s in r["sources"]:
        lab = {"CAARP": f"CAARP venue {s['id']} (CC BY-NC-SA 3.0)", "Cinema Treasures": f"Cinema Treasures theatre {s['id']}",
               "Victorian Heritage Database": f"Victorian Heritage Database place {s['id']}",
               "NSW discovery batch 01": f"NSW discovery batch 01, {s['id']} (catalogue reference)"}[s["source"]]
        sources.append({"label": lab, "url": s["url"]})
    for ref in r.get("caarp_refs", [])[:4]:
        sources.append({"label": "Cited by CAARP: " + ref[:180], "url": ""})
    status_word = {"operating": "Operating cinema", "repurposed": "Building survives (heritage-listed)", "closed": "Closed or not stated"}[r["status"]]
    out.append({
        "aliases": r["aliases"][:8], "address": r["address"], "type": r["type"] if r["type"] != "cinema" else "",
        "facts": facts, "notes": [], "sources": sources, "conflicts": conflicts, "related": [],
        "nationalId": r["fca_id"], "candidateIds": [f"{s['source']}:{s['id']}" for s in r["sources"]],
        "id": r["fca_id"].lower(), "state": STATE, "name": r["name"],
        "locality": r["locality"] or (r.get("locality_note") or ""),
        "basis": basis(r), "published": "staging, not published",
        "status": r["status"], "statusNote": f"{status_word} ({r['status_basis'][0].lower() + r['status_basis'][1:] if not r['status_basis'].startswith(('Cinema Treasures', 'CAARP')) else r['status_basis']}; not verified)",
        "region": r["region"] or "", "postcode": r["postcode"],
        "level": r["proposed_level"], "levelReason": r.get("level_reason", ""), "review": r["review"],
        "summary": summary(r),
        "noApprox": STATE == "NSW",                # NSW brief: no approximate coordinates; map pins only where validated
    })
out.sort(key=lambda l: l["id"])
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# Victorian towns for approximate markers (GeoNames, CC BY 4.0), in the format build_approx.py reads
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\bst\.?\s", "saint ", s); s = re.sub(r"\bmt\.?\s", "mount ", s)
    s = s.replace("&", " and "); s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()
L = json.load(open("assets/data/au-localities.json", encoding="utf-8"))
want = {norm(l["locality"]) for l in out if l["locality"]}
add = 0
GF = f"research/{STATE.lower()}/geonames-{STATE.lower()}.json"
for pc, place, lat, lon in (json.load(open(GF, encoding="utf-8"))["rows"] if os.path.exists(GF) and STATE != "NSW" else []):
    k = norm(place)
    if k in want:
        key = k + "|" + STATE
        if key not in L or not any(x[2] == place and abs(x[0] - lat) < 1e-4 for x in L[key]):
            L.setdefault(key, []).append([lat, lon, place]); add += 1
json.dump(dict(sorted(L.items())), open("assets/data/au-localities.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"{len(out)} {STATE} research leads written to {OUT}; {add} locality points added")
