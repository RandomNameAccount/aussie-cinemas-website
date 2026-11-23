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

### Refinement round 1 (branch `refine-1`): awaiting Tony's review

Not live. The approved White Art Deco design on `main` stays as it is until Tony confirms this round.

- Homepage is more image-led: a larger hero picture with the panel overlapping it, a full-width story picture, and featured records as large picture-first cards (one lead record, three supporting).
- The map stays directly under the hero, with state and territory browsing straight beneath it. The map is taller, its area buttons are larger, and its zoom buttons are 44 px. On phones the area buttons scroll sideways and the key is more compact. On touch screens one finger scrolls the page and pinch zooms the map; a "Move the map" button turns one-finger panning on.
- Phones: tighter section spacing, a shorter header and menu, states in a 4-across grid, and What's On cards that swipe sideways.
- Same logo file (`assets/img/brand/fca-logo.png`) in the header and phone menu; the footer uses the same artwork on a white tile.
- Evidence labels, source citations, and the fictional/real labelling are unchanged. Member accounts, forums, giveaways and payments stay switched off.
