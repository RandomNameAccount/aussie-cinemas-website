# Film Cinemas Australia

Film Cinemas Australia ([filmcinemas.au](https://filmcinemas.au)) is a national archive of Australia's cinemas, past and present. It maps cinema sites in every state and territory, with a page for each cinema, and labels how well each detail has been checked: verified records, archive listings and unverified research leads. It also covers projection equipment, research sources, the chains still screening film, and a Cinema Community where members of the public can suggest updates.

It is a static website (plain HTML, CSS and JavaScript) hosted on GitHub Pages.

## Run locally

It's plain HTML, CSS and JavaScript with no build step. Open `index.html` in a browser, or serve the folder:

```
python3 -m http.server 8000
```

then visit http://localhost:8000.

## Structure

- `index.html`: homepage with the map
- `cinemas/<id>.html`: verified cinema records
- `archive/<id>.html`: archive listings (Phase C)
- `leads/<id>.html`: research leads, not yet verified (Phase B)
- `explore.html`, `research.html`, `equipment.html`, `share.html`, `whats-on.html`: main pages
- `community.html`, `forums.html`, `thread.html`, `update.html`, `moderation.html` and related pages: Cinema Community (switched off until Supabase is connected)
- `assets/`: styles, scripts, map data, icons, images and vendored Leaflet and Supabase (see their licence files)
- `supabase/`: database schemas and setup notes for forums and "Suggest an update"
- `tools/`: Python build scripts that turn the approved data into pages

## Design: White Art Deco (approved Nov 2026)

- `assets/theme.css` holds every colour, font, size and spacing token. `assets/styles.css` reads only those tokens, so a rebrand is a one-file change.
- Fonts are self-hosted in `assets/fonts/` (Marcellus for headings, Manrope for body; SIL Open Font Licence, see the `OFL-*.txt` files). No Google Fonts requests.
- Logo files are in `assets/img/brand/`: `fca-logo.png` (header), `fca-logo-on-navy.png` (footer, on a white tile) and `fca-logo-1200.png` (master for documents). Replace these files to update every page.
- Dark mode is the reader's choice (footer switch); the site is white by default.

### Refinement round 1 (live from 24 November 2026)

Released at Matt's request on 24 November 2026.

- Homepage is more image-led: a larger hero picture with the panel overlapping it, a full-width story picture, and featured records as large picture-first cards (one lead record, three supporting).
- The map stays directly under the hero, with state and territory browsing straight beneath it. The map is taller, its area buttons are larger, and its zoom buttons are 44 px. On phones the area buttons scroll sideways and the key is more compact. On touch screens one finger scrolls the page and pinch zooms the map; a "Move the map" button turns one-finger panning on.
- Phones: tighter section spacing, a shorter header and menu, states in a 4-across grid, and What's On cards that swipe sideways.
- Same logo file (`assets/img/brand/fca-logo.png`) in the header and phone menu; the footer uses the same artwork on a white tile.
- Evidence labels, source citations, and the fictional/real labelling are unchanged. Member accounts, forums, giveaways and payments stay switched off.

## Research leads (Phase B)

Unverified research for SA, ACT, Queensland (round 2), Tasmania and WA is published, with the owner's approval, as **research leads**, kept separate from the genuine records:

- data: `assets/data/leads-<state>.json` (exported from the Phase B staging databases)
- pages: `leads/<id>.html`, listed in Explore with the "Research lead, not yet verified" badge and filter
- leads have no photographs or personal details, and every page says the details are not yet checked. On the map they show as hollow markers at their approximate town or suburb centre (see the 27 November release below)
- Queensland round-2 leads that match an existing QLD record are not published, so no cinema appears twice

Rebuild everything with `python3 tools/build_genuine.py` (it runs `tools/build_leads.py` at the end). To remove a state's leads, delete its JSON file and rebuild.

## NSW research leads, discovery batch 01 (live from 27 November 2026)

Published at Matt's request and approved on 27 November 2026.

- 73 NSW cinemas from discovery batch `FCA_NSW_DISCOVERY_01` (76 candidates), published as research leads in `assets/data/leads-nsw.json` (`leads/fca-nsw-d01-*.html`), with the same "Research lead, not yet verified" badge.
- 73 published in all. Three are not published because they are already in the archive under other names (Roxy Cinema Parramatta = record `roxy-parramatta`; Roxy Cinema Leeton = `shr-01747`; Victoria Cinema Newcastle = `shr-01301`). Two carry an open question on their page: `FCA-NSW-D01-019` "The Cinema", Granville (possibly the Crest Theatre) and `FCA-NSW-D01-038` Civic Theatre, Parramatta (flagged by the batch as a possible existing identity).
- Evidence is thin: 52 come from one State Library of NSW photograph-collection catalogue (photographs not inspected), 17 from a volunteer-edited directory of demolished cinemas. Each page says which.
- 70 have approximate town or suburb markers (GeoNames NSW localities added to `assets/data/au-localities.json`). Mayfield, Punchbowl and Summer Hill each name more than one NSW place, so those three leads are not placed.

## Archive listings (Phase C)

Approved archive listings (verification levels C and D) sit between the genuine records and the research leads:

- data: `assets/data/archive-listings.json`, exported from the editorial staging database after owner approval. Never edit it by hand.
- pages: `archive/<id>.html`, listed in Explore with their own evidence filter.
- level C may show its address, labelled provisional; level D never shows an address. Only sources an editor has opened and checked are linked.
- listings whose address matches official state address data (Property Address Queensland, Tasmania's LIST) are pinned at that address today; the popup says it is not the historic cinema's footprint.
- when a listing replaces a research lead, the lead is removed in the same commit.

`python3 tools/build_genuine.py` rebuilds records, then leads (`build_leads.py`), then archive listings (`build_archive.py`). To roll back a release, `git revert` its commit.

## Release: approximate markers and "Suggest an update" (live from 27 November 2026)

Approved by Tony, relayed by Matt, 27 November 2026.

- **Approximate map markers.** Cinemas without an exact site are shown at their town or suburb centre (GeoNames, CC BY 4.0) and labelled approximate; research leads are hollow markers. Both can be switched on and off on the map. This replaces the 26 November removal of approximate pins, so the public can help pin down the real locations. Data: `assets/data/approx-placements.json`, built by `tools/build_approx.py`.
- **"Suggest an update"** on every record, archive listing and lead page. Suggestions go to a moderation queue (`moderation.html`) and an editor applies them; nothing a member sends goes live by itself. Switched off until Supabase is connected (`assets/forum-config.js`, setup in `supabase/FORUM_SETUP.md`).
- **Cinema chains still screening film** on the Equipment page (Palace, Dendy, Five Star, Lido group; Dendy Canberra still to confirm). Data: `assets/data/film-chains.json`, built by `tools/build_chains.py`.

Member accounts and forums stay switched off until Supabase is connected; giveaways and payments stay off.

## Street map and Google Maps links (staged 27 November 2026)

- **Street map.** The map sits on OpenStreetMap's standard tiles (`tile.openstreetmap.org`, allowed in each page's `img-src` policy), softened in CSS to suit the palette and inverted in dark mode (`.rm-tiles` in `assets/styles.css`). It zooms to street level (zoom 19). The Natural Earth outline stays underneath and shows if the tiles cannot load. OpenStreetMap's free tiles are for light use under its tile usage policy, with the attribution kept on the map; if traffic grows, move to a tile provider with a key (MapTiler, Stadia, or CARTO, which requires a key on public sites).
- **Find on Google Maps** on every record, archive listing and lead page and in every map popup, so readers can check a place before suggesting an update. Records with an exact site also get a **Street View** button. These are plain links: no Google API key, account or charges. Records whose sources disagree on the address search by name and suburb only; level D listings never include an address.

## Victorian and NSW archive expansion (live from 27 November 2026)

733 new Victorian cinemas as research leads awaiting editorial review, from CAARP (CC BY-NC-SA 3.0), Cinema Treasures (facts only) and the Victorian Heritage Database. Raw extracts, the consolidated database and the report are in `research/vic/` (`VIC_EXPANSION_REPORT.md`). Rebuild: `python3 tools/vic/build_vic_db.py && python3 tools/vic/export_vic_leads.py && python3 tools/build_genuine.py`. Explore now has a Region filter; research leads can carry a reported status and show a placeholder icon. Approved for publication by Matt on 27 November 2026. NSW: 599 further research leads from Cinema Treasures, CAARP and discovery batch 01 (`assets/data/leads-nsw-expansion.json`, report in `research/nsw/`), with no approximate coordinates. Rebuild either state with `FCA_STATE=VIC|NSW FCA_PUBLISHED="27 November 2026" python3 tools/expansion/build_state_db.py && ... export_state_leads.py && python3 tools/build_genuine.py`. CAARP data is CC BY-NC-SA 3.0: settle permission before any advertising.
