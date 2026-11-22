# The Australian Projection Archive

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
