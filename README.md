# Film Cinemas Australia

Static website prototype for a cinema heritage archive: a map-first homepage of Brisbane, Sydney and Melbourne cinema sites, individual cinema pages, equipment, research, explore and share pages.

## Run locally

It's plain HTML, CSS and JavaScript with no build step. Open `index.html` in a browser, or serve the folder:

```
python3 -m http.server 8000
```

then visit http://localhost:8000.

## Structure

- `index.html`: homepage with the map
- `cinema-*.html`: individual cinema pages
- `explore.html`, `research.html`, `equipment.html`, `share.html`, `components.html`: other pages
- `assets/`: styles, scripts, map data, icons, images and vendored Leaflet (see its licence files)

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
- leads have no map pins, photographs or personal details, and every page says the details are not yet checked
- Queensland round-2 leads that match an existing QLD record are not published, so no cinema appears twice

Rebuild everything with `python3 tools/build_genuine.py` (it runs `tools/build_leads.py` at the end). To remove a state's leads, delete its JSON file and rebuild.

## Archive listings (Phase C)

Approved archive listings (verification levels C and D) sit between the genuine records and the research leads:

- data: `assets/data/archive-listings.json`, exported from the editorial staging database after owner approval. Never edit it by hand.
- pages: `archive/<id>.html`, listed in Explore with their own evidence filter.
- level C may show its address, labelled provisional; level D never shows an address. No listing has a map pin, and only sources an editor has opened and checked are linked.
- when a listing replaces a research lead, the lead is removed in the same commit.

`python3 tools/build_genuine.py` rebuilds records, then leads (`build_leads.py`), then archive listings (`build_archive.py`). To roll back a release, `git revert` its commit.
