# NSW historical cinema expansion: staging report

Status: **staging only** (branch `staging/vic-expansion`, alongside the Victorian expansion). Nothing is on the production site. Publishing needs Tony Matarazzo's approval.

## Acceptance figures

| Measure | Result |
|---|---|
| Original NSW cinema count | **94**: 17 records, 4 archive listings, 73 research leads (discovery batch 01) |
| Batch 01 (76 candidates) | Imported and reconciled: all 73 published leads matched to their candidates; the other 3 are existing records (Roxy Parramatta, Roxy Leeton, Victoria Newcastle). Existing identifiers, sources and markers preserved. |
| Additional candidates discovered | 843 source rows: CAARP 251, Cinema Treasures 516, batch 01 76 |
| Duplicate identities identified | 153 merges between source rows; 92 groups matched to 88 existing NSW entries (not added again); 3 kept separate and flagged as possible second venues (level E) rather than merged |
| **New unique records accepted into staging** | **599** (target 500) |
| **Updated NSW cinema count (staging)** | **693** |
| Records awaiting editorial review | All 599 |
| Proposed verification level | B 65 · C 499 · D 27 · E 8 · A 0 (no land-title verification) |
| Verified map locations | 0 new. As the brief requires, no approximate coordinates were created for the new NSW entries; the 43 existing verified record pins and the 70 batch-01 town markers are unchanged. All 599 are searchable in Explore. |
| Status (as sources report it, not verified) | Operating 114 · closed or not stated 485 |
| Type | Cinema 461 · hall with film screenings 72 · drive-in 47 · open-air 18 · theatre 1 |
| Field coverage | Address 572 · alternative names 304 · operators 211 · capacity 190 · architectural style 146 · opening/closing dates: pending (CAARP NSW venue pages being collected, see below) |

## Regional coverage (new records; brief's indicative target in brackets)

| Region | New | Target | |
|---|---|---|---|
| Sydney CBD | 46 | 40 | met |
| Inner West | 68 | 50 | met |
| Eastern Suburbs | 53 | 30 | met |
| Western Sydney | 40 | 50 | short 10 |
| South-West Sydney | 33 | 35 | short 2 |
| North Shore | 38 | 30 | met |
| Northern Beaches | 17 | 25 | short 8 |
| St George and Sutherland | 34 | 30 | met |
| Blue Mountains | 10 | 10 | met |
| Central Coast | 10 | 30 | short 20 |
| Newcastle and Hunter Valley | 23 | 50 | short 27 |
| Illawarra and South Coast | 101 | 40 | met |
| Regional and rural NSW | 126 | 80 | met |

Regions are assigned from postcodes. **Coverage gaps:** Newcastle and Hunter, Central Coast, Northern Beaches and Western Sydney are under-represented in CAARP and Cinema Treasures. The best sources to close them are CATHS's NSW listings (needs permission), Trove advertisements, and local studies collections (Newcastle Libraries, Central Coast Council, Blacktown and Penrith libraries).

## Source and copyright register (both states)

| Source | Used for | Rights | Action needed |
|---|---|---|---|
| CAARP | Names, addresses, operating dates, capacity, screens, name changes, cited references | CC BY-NC-SA 3.0: credit, non-commercial, share-alike | **Escalation:** before advertising (Cinema Partners), get CAARP's permission or remove CAARP-derived fields. CAARP's free-text notes (which name private people) are kept in the research database only. |
| Cinema Treasures | Names, previous names, address, open/closed, size, operators, architects, style | Facts only; descriptions, comments and photos not copied | None for facts; link each venue (done) |
| NSW discovery batch 01 | 76 candidates, State Library of NSW catalogue references | References only; no images | None |
| Victorian Heritage Database | Place names, addresses, listing numbers (Victoria) | Facts only | None |
| GeoNames | Suburb and postcode lookup (both states); approximate markers (Victoria only) | CC BY 4.0 | Credit on the map (done) |
| CATHS | **Not used** | © CATHS, no reuse statement | **Escalation:** ask CATHS for permission; it is the strongest NSW listing |
| NSW State Heritage Inventory, Museums of History NSW, Trove, State Library of NSW, council heritage studies, historical societies | Not bulk-searched | Varies | Use for editorial confirmation of individual records |
| Photographs | None used | Not cleared | Placeholder icons shown |

## Website (staging)

Searchable by name, former name, suburb, postcode and region; region filter with live counts; status filter uses reported status; opening and closing dates shown on pages and in Explore where known; each page shows a generated factual summary, "Other cinemas in <suburb>", its sources, its proposed verification level with the reason, and a placeholder icon. Research leads remain labelled and filterable separately from records and archive listings.

## Testing and integrity

- Site tests (headless Chromium): 26 of 26 passed (both states; see `test-output.txt`).
- Database integrity: 17 of 17 checks passed (unique ids, a page for every lead, sources on every lead, A–E level with a reason on every lead, no repeated name+locality+address, no repeat of an existing record, no invented NSW coordinates, existing pins and record pages unchanged; see `integrity.txt`).

## Still to do (resumable)

- CAARP NSW venue pages (251) are being collected; save them as `research/vic/caarp-part3.json` and rerun
  `FCA_STATE=NSW python3 tools/expansion/build_state_db.py && FCA_STATE=NSW python3 tools/expansion/export_state_leads.py && python3 tools/build_genuine.py`
  to add opening and closing dates and capacities. Ids stay stable.
- Editorial review, starting with the 65 at level B and the 8 at level E.
- 55 Sydney cinemas are known only by postcode (Cinema Treasures files them under "Sydney"); an editor should set the suburb.
