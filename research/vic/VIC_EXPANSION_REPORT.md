# Victorian archive expansion: staging report

Status: **staging only** (branch `staging/vic-expansion`). Nothing is on the production site. Publishing needs Tony's approval.

## Acceptance figures

| Measure | Result |
|---|---|
| Original Victorian website records | 5 (Astor St Kilda, Capitol Melbourne, Regent Melbourne, Sun Yarraville, Palais St Kilda); no Victorian leads or archive listings |
| Source rows collected | 1,133: CAARP 477, Cinema Treasures 544, Victorian Heritage Database 112 |
| Duplicate source rows merged | 384 merges (each listed with its reason in `vic-duplicates.csv`) |
| Matches to existing website records | 6 rows: 4 are the same venue (Capitol, Regent, Astor, Sun) and are not added again; 2 are possible links to the Palais record and are added with an open question |
| **New unique Victorian cinemas accepted into staging** | **737** (target 500) |
| Awaiting editorial review | All 737. Proposed verification levels (A–E): B 249, C 442, D 28, E 18 |
| Evidence | Two independent sources agree: 251 · heritage listing names the place: 28 · single source: 454 |
| Verified map locations | 0 new. 657 have approximate town or suburb markers (GeoNames centres, labelled approximate); 76 have no marker and stay searchable |
| Status (as sources report it, not verified) | Operating 135 · building survives (heritage-listed) 23 · closed or not stated 575 |
| Type | Cinema 485 · hall with film screenings 141 · drive-in 75 · open-air 24 · theatre 8 |
| Regional coverage | Metropolitan Melbourne 424 · Melbourne CBD 101 · Goulburn Valley and Hume 42 · Loddon Mallee and Bendigo 32 · Western District 31 · Gippsland 29 · Ballarat and Central Highlands 23 · Geelong and Barwon 19 · North East 13 · Macedon Ranges and Central Victoria 12 · Wimmera 7 |
| Field coverage | Address 709 · alternative names 460 · capacity 457 · opening and last-listing dates 447 · architectural style 139 · operators 178 |

Regions are assigned from postcodes (a documented approximation in `tools/vic/build_vic_db.py`).

## Sources and publication rights

| Source | What was used | Rights position |
|---|---|---|
| CAARP (Cinema and Audience Research Project) | Venue list (all 1,307 venues, 477 Victorian) and venue pages: names, addresses, dates, capacity, screens, name changes, cited references | **CC BY-NC-SA 3.0.** Reuse is encouraged with credit, but only **non-commercially** and with derived data under the **same licence**. If the site carries advertising (Cinema Partners), the CAARP-derived data needs CAARP's permission or must be removed. Credit: Deb Verhoeven with others (eds), Cinema and Audiences Research Project database. CAARP's free-text venue notes include oral-history details about named private people; they are kept in the research database only and are **not** published on pages. |
| Cinema Treasures | Names, previous names, town, address, open/closed status, size, operators | Facts only. No descriptions, comments or photographs copied. Volunteer-edited, so each venue needs a primary source. |
| Victorian Heritage Database | Place name, address, listing (VHR, Heritage Overlay, National Trust) | Names, addresses and listing numbers only; statements of significance were not copied. |
| GeoNames postal localities | Town and suburb centres, postcodes | CC BY 4.0, credited on the map. |
| CATHS venue listings | **Not used.** | © CATHS with no reuse statement. Bulk reuse needs CATHS's permission; a request is recommended. |
| Trove, PROV, State Library Victoria, council heritage studies, historical societies | Not bulk-searched in this pass. | Best used by editors to confirm individual records (Trove newspaper notices for opening dates). |

## How the site presents the Victorian entries

- Every entry is a **research lead** ("Research lead, not verified"), separate from approved records and archive listings, with its proposed evidence level and "not yet approved for publication".
- Facts carry a **Provisional** label and name their source; status says where it came from.
- Explore: Victoria filter, new **Region** filter with live counts, status filter uses the reported status, search covers every alternative name, address and postcode.
- Leads without a photograph show an outline placeholder icon (cinema, drive-in or hall).
- Leads without a placeable town stay searchable with no marker; no exact pins were added.

## Testing (headless Chromium, local copy of the staging branch)

26 of 26 site checks passed (with NSW) and 17 of 17 database integrity checks passed: Victoria count (738 = 5 records + 733 leads), alias search (Moviehouse finds Carlton Theatre), drive-in search, status filter, region filter (form and URL), evidence filter keeps records and leads apart, lead page placeholder, provisional label, staging label, aliases, drive-in placeholder, unmapped lead stays listed, homepage Victoria tile, 600+ Victorian map markers, existing Victorian record page, Queensland count unchanged, no JavaScript errors.

## Still to do (resumable)

- CAARP venue pages: 473 of 477 collected (the last few are being retried); the CAARP server answers slowly (about 30 seconds a page). The remaining ids are listed in `vic-progress.json` (`caarp_details_missing`). Save further pages as `research/vic/caarp-part2.json` (same format) and rerun:
  `python3 tools/vic/build_vic_db.py && python3 tools/vic/export_vic_leads.py && python3 tools/build_genuine.py`
  Record ids stay stable between runs.
- Editorial review: confirm or reject each lead, starting with the 279 proposed at level C.
- Ask CATHS for permission to use its Victorian listings, and confirm the CAARP licence position before any advertising.
- Palais St Kilda: two CAARP entries (Elite/Palais Pictures; Casino/Palais de Danse) may be predecessors on the same site; an editor should decide.


Current regional split: Metropolitan Melbourne 425, Melbourne CBD 103, Goulburn Valley and Hume 43, Loddon Mallee and Bendigo 31, Western District 31, Gippsland 29, Ballarat and Central Highlands 24, Geelong and Barwon 19, North East 13, Macedon Ranges and Central Victoria 12, Wimmera 7. Status: operating 135, building survives 24, closed or not stated 578. Evidence: two sources agree 259, heritage listing 28, single source 450.
