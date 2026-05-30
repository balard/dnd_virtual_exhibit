# DnD Virtual Exhibit — Claude Instructions

## Project Overview
A single-page web application for browsing TSR (Tactical Studies Rules) product cover art,
spanning publications from 1974 onward (D&D, AD&D, and related products).

## Architecture
- **index.html** — Main SPA: HTML, CSS, and JavaScript in one file (no build step); links `common.css` and `utils.js`
- **search.html** — Search/filter page: pill toggles for type/system/setting/publisher, live text search across title/code/authors/artist/blurb, thumbnail grid; clicking a result opens `index.html#id=<N>`; links `common.css` and `utils.js`
- **spread.html** — Spread viewer: shows back cover (left) + front cover (right) side by side for a single product; toolbar with Back, Random, and collapsible Details; navigates all products; syncs position with `index.html` via localStorage and `#id=` hash; designed for wide/desktop displays; links `common.css` and `utils.js`
- **stats.html** — "By the Numbers" statistics page: 5 Chart.js v4 (CDN) visualizations — releases per year (line/area), game systems over time (stacked bar), product type breakdown (doughnut), top campaign settings (horizontal bar), top cover artists (horizontal bar); summary stat cards with scroll-to-chart; standalone page (not yet linked from other pages); links `common.css`
- **game.html** — "Chrono Covers" mini-game: arrange 5 random cover cards in chronological order; 3 difficulty levels (easy: cross-decade, medium: same decade, hard: 3-year window with month-aware ordering); drag-and-drop + click-to-swap; streak counter persisted in localStorage; draws rounds from the active search-filter universe (shared via `tsr_active_filters`) — shows a banner with a session-local "Play with all" toggle, and a warn+block panel (per difficulty) when the filtered pool is too small; links `common.css` and `utils.js`
- **odd1out.html** — "Odd One Out" mini-game: identify which of 5 cover cards doesn't share a common attribute (year, setting, system, type, artist, author); single mode (no difficulty picker); streak counter; draws rounds from the active search-filter universe (shared via `tsr_active_filters`) — same banner + warn+block behavior as game.html; links `common.css` and `utils.js`
- **debug.html** — Developer tool: shows all 24 fields per product in a 7-product context window (±3 around current); same dark theme; keyboard nav (←/→/Home/End)
- **common.css** — Shared CSS: design tokens (CSS variables `--bg`, `--bg2`, `--card`, `--border`, `--accent`, `--text`, `--muted`), error overlay styles, and the game filter banner/warning styles (`.filter-banner`, `.filter-warning`); linked by all HTML pages
- **utils.js** — Shared JS: `FILTERS_KEY`, `FILTERS_SEEDED_KEY`, `MONTH_NAMES`, `TEXT_FIELDS`, `loadActiveFilters()`, `applyFiltersToProducts()`; also runs a one-time seed on load that defaults the filter to exclude magazines (see search.html internals); loaded by index.html, search.html, spread.html, game.html, odd1out.html
- **products.json** — Product data consumed by the viewer at runtime via `fetch()`
- **convert_csv.py** — Python 3 script that regenerates `products.json` from the CSV source
- **download_covers.py** — Downloads cover images by year into `covers/full/`
- **covers/full/** — Local image files: front covers named `{id}.{ext}`, back covers named `{id}-back.{ext}`; served via GitHub Pages
- **covers/thumb/** — 300px-wide JPEG thumbnails generated from `covers/full/`; used by `search.html` and `game.html`
- **generate_thumbs.py** — Python 3 script that generates `covers/thumb/` from `covers/full/` (requires Pillow)
- **../tsr_products/tsr_products.csv** — Master product table (19 cols: id through semester, includes publisher; no cover_url)
- **../tsr_products/covers.csv** — Cover URLs (3 cols: id, cover_url, backcover_url)
- **../tsr_products/blurbs.csv** — Product blurb text (2 cols: id, blurb; QUOTE_ALL)
- **../tsr_products/dtrpg.csv** — DriveThruRPG links (3 cols: id, dtrpg_url, dtrpg_title)

## Tech Stack
- Vanilla HTML5 / CSS3 / JavaScript (no frameworks, no bundler)
- Google Fonts: Cinzel (serif headings)
- Python 3 (data pipeline only)

## search.html internals
- Loads `products.json` via `fetch()` on init (same requirement: must run via local server)
- **Structured filters** — pill toggle buttons, multi-select, OR-logic within a category, AND-logic across categories:
  - **Type** (8 values): `adventure`, `accessory`, `boxed set`, `hardcover`, `Flip-book`, `boardgame`, `miniatures`, `magazine`
  - **System** (9 values): `AD&D 2e`, `AD&D 1e`, `Basic D&D`, `OD&D`, `Dragon Quest`, `D&D 3e`, `D&D 3.5`, `Chainmail`, `D&D 4e`
  - **Setting** (23 values + null): Forgotten Realms, Greyhawk, Mystara, Ravenloft, Dragonlance, Planescape, Dark Sun, Birthright, Spelljammer, Al-Qadim, Lankhmar, Thunder Rift, Kara-Tur, Mystara (2E), Blackmoor, Conan, Celtic, Eberron, Ghostwalk, Oriental Adventures, Diablo, Chainmail, Various — plus `(no setting)` for products where `setting` is null
  - **Publisher** (2 values): `TSR`, `WotC`
- **Text search** — live, debounced 200ms, case-insensitive, searches: `title`, `dtrpg_title`, `module_code`, `product_code`, `authors`, `cover_artist`, `blurb`
- Pill counts show total products per value (not filtered count) — they are built once on load
- Results render as a thumbnail grid (`aspect-ratio: 3/4`, lazy-loaded); clicking a card → `index.html#id=<N>`
- Filter state is saved to `localStorage` key `tsr_active_filters` (JSON) on every change and restored on load; a "Clear Filters" button removes it
- **Default (seed-once):** on a browser's first ever visit, `utils.js` seeds `tsr_active_filters` with `exclude_type: ['magazine']` so magazines are hidden by default app-wide (gallery, spread, both games). A `tsr_filters_seeded` marker ensures this happens at most once, so after the first visit the user has full control and "Clear Filters" truly clears (it will not re-add the default)
- `index.html` and `spread.html` read `tsr_active_filters` on load and navigate only within the filtered product set; position is tracked by product id (`tsr_current_id`) rather than array index

## Key Conventions
- Page-specific logic stays in its own HTML file; shared filter logic lives in `utils.js`; shared styles in `common.css`
- `products.json` is generated — never hand-edit it; run `convert_csv.py` instead
- `products.json` entries include 24 fields; CSV columns with spaces are normalized to underscores (`product_code`, `module_code`); `cover_url` points to a local path (`covers/full/{id}.jpg`) if the image has been downloaded, otherwise the remote URL from covers.csv
- Dark theme colors are defined as CSS variables in `common.css` — edit them there, not in individual HTML files
- Responsive breakpoint at 900px (3-column → 1-column layout)

## Data Pipeline
To regenerate `products.json` after editing the CSV:
```bash
python convert_csv.py
```
Inputs: `../tsr_products/tsr_products.csv`, `../tsr_products/covers.csv`,
        `../tsr_products/blurbs.csv`, `../tsr_products/dtrpg.csv`
Output: `products.json`

`MAX_YEAR` in `convert_csv.py` is fixed at **2013** — do not change it.

### Image Download Pipeline
To download covers for a specific year (run *before* regenerating JSON):
```bash
python download_covers.py <year>
```
Output:
- `covers/full/{id}.{ext}` — front cover, named by the product's CSV `id` field
- `covers/full/{id}-back.{ext}` — back cover (URL read from `covers.csv` `backcover_url` column)

- Already-downloaded files are skipped automatically (idempotent).
- The script reads `../tsr_products/covers.csv` directly to get `backcover_url` for each product.
- 404s on back covers are expected — not all products have back cover images on tsrarchive.com.

**Workflow when adding a new year of images:**
1. `python download_covers.py <year>`
2. `python convert_csv.py` ← regenerate JSON; local paths are picked up automatically
3. `python generate_thumbs.py <start_id> <end_id>` ← generate thumbnails for the new products

## generate_thumbs.py internals
- Reads `covers/full/` (`.jpg`/`.jpeg`, case-insensitive) and writes 300px-wide JPEGs to `covers/thumb/`
- Maintains aspect ratio; JPEG quality 75; uses Pillow (`pip install Pillow`)
- Idempotent — existing files are skipped
- Optional ID range: `python generate_thumbs.py <start_id> <end_id>`
- `search.html` and `game.html` derive thumb URLs via `cover_url.replace('/full/', '/thumb/')`

## download_covers.py internals
- Reads `products.json` to filter products by year
- Reads `../tsr_products/covers.csv` to get `backcover_url` for each product directly (no URL derivation needed)
- Both front and back downloads are idempotent — existing files are skipped

## convert_csv.py internals
- Joins 4 CSV files on `id`: tsr_products.csv (main), covers.csv, blurbs.csv, dtrpg.csv
- Exports 24 fields per product: id, order, year, month, day, product_code, title, module_code, type, system, setting, publisher, confidence, edition, authors, pages, isbn, cover_url, cover_artist, semester, backcover_url, blurb, dtrpg_url, dtrpg_title
- CSV columns with spaces (`product code`, `module code`) are normalized to underscores
- `cover_artist` normalization: strips `LIKELY:` prefix; converts empty/blank to `null`; keeps `N/A` as the string `"N/A"` (meaning artist credit is explicitly not applicable, distinct from unknown/missing)
- `season` field removed (no longer in source data)
- Always reads local CSV files directly (no remote URL fallback)
- Local cover files (`covers/full/{id}.*`) are the primary image source; `cover_url` from covers.csv is a fallback — products with local files are included even without a CSV cover_url
- Validates month (1–12) and title; invalid months are set to `null` with a warning; missing titles are skipped
- Exits with a clear error if any source CSV file is missing

## Image Download Progress
Years fully downloaded to `covers/full/` (run `download_covers.py` then regenerate JSON):
- Front covers: 1974 ✓, 1975 ✓, 1976 ✓, 1977 ✓, 1978 ✓, 1979 ✓, 1980 ✓, 1981 ✓, 1982 ✓, 1983 ✓, 1984 ✓, 1985 ✓, 1986 ✓, 1987 ✓, 1988 ✓, 1989 ✓, 1990 ✓, 1991 ✓, 1992 ✓, 1993 ✓, 1994 ✓, 1995 ✓, 1996 ✓, 1997 ✓, 1998 ✓, 1999 ✓, 2008 ✓ (ids 1033–1035), 2012 ✓ (ids 1037–1039), 2013 ✓
- Back covers: 1974–1999 ✓, 2008 ✓ (ids 1033–1035), 2012 ✓ (ids 1037–1039), 2013 ✓ (id=420 [1992] back added manually)
- id=868 (The Book of Regency, 2002) has no back cover — intentionally absent, confirmed dead link
- ids 1023 & 1028 (2007): local covers only (no cover_url in covers.csv); included via local file detection
- Front/back covers now fully downloaded for all years with products (2000–2013 covered via Dragon/Dungeon/4e batches)
- Years with no products (skip): 2009–2011

### Dragon Magazine covers (ids 1042–1471)
430 magazine issues added (The Dragon #1 through Dragon #430, 1976–2013). Cover images
sourced from `cf.geekdo-images.com` URLs (BoardGameGeek); no back covers exist in covers.csv.
- 20 front covers already present locally (ids 1069, 1091, 1095, 1096, 1107, 1146, 1148, 1150–1153, 1155, 1159, 1160, 1170, 1192, 1195, 1197, 1200, 1204); auto-picked up by convert_csv.py
- Remaining ~410 magazine covers need downloading via `download_covers.py <year>` for each year 1976–2013
- Years 1976–1999: magazines overlap with fully-downloaded product years; existing product files are skipped automatically, only magazine covers are fetched
- Years 2000–2007: Dragon magazines overlap with Dungeon magazines for these years
- Years 2008–2013: magazines alongside the D&D 4e product covers
- Magazine `setting` is always `"Various"` — they are not setting-specific publications

### Dungeon Magazine covers (ids 1472–1692)
221 magazine issues added (Dungeon #1 through Dungeon #221, 1986–2013). Cover images
sourced from `cf.geekdo-images.com` URLs (BoardGameGeek); no back covers exist in covers.csv.
- Systems span AD&D 1e (early issues), AD&D 2e, D&D 3e, D&D 3.5, D&D 4e (digital era)
- Magazine `setting` is always `"Various"`
- All front covers downloadable via `download_covers.py <year>` for each year 1986–2013

### D&D 4e product covers (ids 1693–1903)
134 non-magazine D&D 4e products (2007–2013): hardcovers, adventures, accessories, boxed sets,
boardgames. Cover images sourced from `https://www.tsrarchive.com/4e/` URLs; no back covers.
- Publisher: WotC exclusively
- All front covers downloadable via `download_covers.py <year>` for years 2007–2013

## Running Locally
Open `index.html` via a local server (required — `fetch()` won't work over `file://`):
```bash
python -m http.server 8000
# then open http://localhost:8000
```

## GitHub
https://github.com/balard/dnd_virtual_exhibit
