#!/usr/bin/env python3
"""Build the 'Chains still screening film' section of equipment.html from assets/data/film-chains.json.
Rule: a chain is listed only with a dated 2026 source showing a public film-print screening; kept projectors do not count.
Writes between <!-- FILM-CHAINS:START --> and <!-- FILM-CHAINS:END --> (inserted after the Film formats section the first time)."""
import html, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
E = html.escape
d = json.load(open("assets/data/film-chains.json", encoding="utf-8"))
rows = []
for c in d["chains"]:
    for i, v in enumerate(c["venues"]):
        src = "; ".join(f'<a href="{E(s["url"])}" rel="noopener">{E(s["title"])}</a>' for s in v["sources"])
        flag = ' <span class="badge b-prelim">To confirm</span>' if v.get("flag") == "check" else ""
        rows.append(f'<tr><th scope="row" data-label="Chain">{E(c["chain"])}</th><td data-label="Venue">{E(v["venue"])}<br><span class="cite-meta">{E(v["place"])}</span></td>'
                    f'<td data-label="Film formats">{E(v["formats"])}</td><td data-label="Evidence (2026)">{E(v["evidence"])}{flag}<br><span class="cite-meta">{src}</span></td></tr>')
nl = "".join(f"<li>{E(x)}</li>" for x in d["not_listed"])
block = f'''<!-- FILM-CHAINS:START -->
<section class="section" aria-labelledby="chains-title" id="film-chains"><div class="wrap"><div class="section-head"><h2 id="chains-title">Cinema chains still screening film</h2>
<p class="lede">Australian chains with at least one venue that has run public screenings from 35mm or 70mm prints in 2026. Checked {E(d["checked"])}.</p></div>
<div class="notice n-info"><p>{E(d["rule"])} Programs change: check with the cinema before you go.</p></div>
<div class="table-wrap"><table class="research-table chains-table"><caption class="visually-hidden">Cinema chains with venues screening film prints in 2026</caption>
<thead><tr><th scope="col">Chain</th><th scope="col">Venue</th><th scope="col">Film formats</th><th scope="col">Evidence (2026)</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<h3>Not on this list</h3><ul>{nl}</ul>
</div></section>
<!-- FILM-CHAINS:END -->'''
t = open("equipment.html", encoding="utf-8").read()
if "<!-- FILM-CHAINS:START -->" in t:
    t = re.sub(r"<!-- FILM-CHAINS:START -->.*?<!-- FILM-CHAINS:END -->", lambda m: block, t, flags=re.S)
else:
    i = t.index('id="fmt-title"'); e = t.index("</section>", i) + len("</section>")
    t = t[:e] + "\n" + block + t[e:]
open("equipment.html", "w", encoding="utf-8").write(t)
print(sum(len(c["venues"]) for c in d["chains"]), "venues in", len(d["chains"]), "chains")
