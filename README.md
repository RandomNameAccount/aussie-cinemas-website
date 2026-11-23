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
- The logo files in `assets/img/brand/` are **placeholders** until the approved Art Deco logo is supplied. Replace `fca-logo.svg` (header) and `fca-logo-on-navy.svg` (footer tile) with the real files; no page code needs to change.
- Dark mode is the reader's choice (footer switch); the site is white by default.
