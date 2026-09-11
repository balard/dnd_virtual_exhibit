# DnD Virtual Exhibit — Claude Instructions

## Project Overview
A single-page web application for browsing TSR (Tactical Studies Rules) product cover art,
spanning publications from 1974 onward (D&D, AD&D, and related products).

## Architecture
- **index.html** — Main SPA: HTML, CSS, and JavaScript in one file (no build step); links `common.css` and `utils.js`
- **search.html** — Search/filter page: pill toggles for type/system/setting/publisher, live text search across title/code/authors/artist/blurb, thumbnail grid; clicking a result opens `index.html#id=<N>`; links `common.css` and `utils.js`
- **spread.html** — Spread viewer: shows back cover (left) + front cover (right) side by side for a single product; toolbar with Back, Random, and collapsible Details; navigates all products; syncs position with `index.html` via localStorage and `#id=` hash; designed for wide/desktop displays; links `common.css` and `utils.js`
- **stats.html** — "By the Numbers" statistics page: 5 Chart.js v4 (CDN) visualizations — releases per year stacked by publisher (area), game systems over time (stacked bar, includes D&D 4e), product types (horizontal bar, types under 10 products collapse into `Other`), top campaign settings (horizontal bar, excludes null — which now includes the magazines), top cover artists (horizontal bar); the settings and artists bars are individually colored from their cover art via the baked static `SETTING_COLORS` (20 of the 21 chartable settings) / `ARTIST_COLORS` (66 artists with ≥5 covers — the only ones that realistically reach a top-12 bar) maps (Vibrant method — most-saturated cover art, saturation-weighted and averaged per entity over the full collection), so a bar's hue follows the entity regardless of filter; unlisted entities fall back to a blended Vibrant tone (`#a76c44` for artists, `#98c379` for settings); summary stat cards (Products, Year Range, Publishers, Settings, Cover Artists) with scroll-to-chart; **filter-aware** — defaults to the full collection but has a header toggle (`Full collection` / `Current filter`) that re-renders all charts against `applyFiltersToProducts(...)`; the `Current filter` button is disabled when no filter is active; linked from `index.html` control bar; links `common.css` and `utils.js`
  - The systems chart is the one chart with a **hardcoded** value list (`systemOrder` / `majorSystems`, stats.html:507) — anything not in it collapses into `Other`. `Saga` (13), `Chainmail` (6) and `Dragon Quest` (1) currently make up that bucket of 20. This is by design, but note `Saga` is now its largest member; promote it to a major system if the Fifth Age line deserves its own band.
  - **`SETTING_COLORS` / `ARTIST_COLORS` keys are matched against the data by exact string**, so an upstream *rename* silently orphans a baked color and the entity falls back. This has already happened twice: `cover_artist` "John and Laura Lakey" became "John Lakey & Laura Lakey" upstream, stranding `#bdb05e`; and `setting` "Mystara (2E)" was unified into "Mystara", stranding `#a75a44` (that dead key has since been removed from the map). When a data refresh renames a setting or artist, re-check these maps — a stale key looks identical to a missing one. The cheapest check is to diff the map keys against `set(p["setting"] for p in products.json)` after every refresh.
  - **Known gap — `Historical` has no baked `SETTING_COLORS` entry** (added to the data after the maps were generated), so it draws with the `#98c379` fallback, off-palette against the browns. It ranks 14th in the full collection and so misses the top-12 settings bar there, but any filter that lifts it into the top 12 shows the green. Deferred, not urgent. Note the script that baked `SETTING_COLORS` / `ARTIST_COLORS` is **not in the repo** — regenerating a color means reimplementing the Vibrant method described above.
- **game.html** — "Chrono Covers" mini-game: arrange 5 random cover cards in chronological order; 3 difficulty levels (easy: cross-decade, medium: same decade, hard: 3-year window with month-aware ordering); drag-and-drop + click-to-swap; streak counter persisted in localStorage; draws rounds from the active search-filter universe (shared via `tsr_active_filters`) — shows a banner with a session-local "Play with all" toggle, and a warn+block panel (per difficulty) when the filtered pool is too small; links `common.css` and `utils.js`
- **odd1out.html** — "Odd One Out" mini-game: identify which of 5 cover cards doesn't share a common attribute (year, setting, system, type, artist, author); single mode (no difficulty picker); streak counter; draws rounds from the active search-filter universe (shared via `tsr_active_filters`) — same banner + warn+block behavior as game.html; links `common.css` and `utils.js`
- **debug.html** — Developer tool: shows all 24 fields per product in a 7-product context window (±3 around current); same dark theme; keyboard nav (←/→/Home/End)
- **common.css** — Shared CSS: design tokens (CSS variables `--bg`, `--bg2`, `--card`, `--border`, `--accent`, `--text`, `--muted`), error overlay styles, and the game filter banner/warning styles (`.filter-banner`, `.filter-warning`); linked by all HTML pages
- **utils.js** — Shared JS: `FILTERS_KEY`, `FILTERS_SEEDED_KEY`, `MONTH_NAMES`, `TEXT_FIELDS`, `loadActiveFilters()`, `filtersActive()` (true if any filter criterion is set — drives the gallery filter-indicator and spread filter-badge visibility, independent of whether the filter reduces the count), `applyFiltersToProducts()`, `thumbUrl()` (maps a `covers/full/{id}.avif` cover_url to its `covers/thumb/{id}.jpg` thumbnail — rewrites the extension as well as the directory, returns null for a coverless product, and passes remote fallback URLs through unchanged); also runs a one-time seed on load that defaults the filter to exclude magazines (see search.html internals); loaded by index.html, search.html, spread.html, game.html, odd1out.html, stats.html
- **products.json** — Product data consumed by the viewer at runtime via `fetch()`
- **convert_csv.py** — Python 3 script that regenerates `products.json` from the CSV source
- **download_covers.py** — Downloads cover images by year into `covers/full/` (as JPEG; run `--adopt` after)
- **redownload_cover.py** — Re-download one or more product ids after fixing a `cover_url`. **Skips any id that already has a local cover unless `--force` is given** (the local file wins); downloads to scratch files and swaps them in only once the front cover is safely on disk, then chains `--adopt` -> `generate_thumbs.py` -> `convert_csv.py`
- **tools/** — Migration and maintenance scripts: `avif_convert.py` (staged bulk conversion, `--verify`, `--promote`, `--revert`, and the steady-state `--adopt`), `avif_preview.py` (visual A/B quality gate), `verify_backup.py` (hashes a tar backup against the live tree)
- **covers/full/** — Local image files, **AVIF** (q50, 4:4:4, full resolution): front covers named `{id}.avif`, back covers named `{id}-back.avif`; served via GitHub Pages. Converted from JPEG to get the published site back under the 1 GB Pages cap (1,077 MB -> 572 MB); see `AVIF_MIGRATION_PLAN.md`. Downloads still arrive as JPEG and are folded in with `tools/avif_convert.py --adopt`
- **covers/thumb/** — 300px-wide **JPEG** thumbnails generated from `covers/full/`; used by `search.html`, `game.html` and `odd1out.html`. Deliberately NOT AVIF: at 300px AVIF saves almost nothing (and is *larger* above q55) while costing a second generation of loss and slower decode in a grid of hundreds. The two trees therefore differ in format — always derive thumb URLs with `thumbUrl()` from `utils.js`, never by string-swapping the directory
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
- **Structured filters** — pill toggle buttons, multi-select, OR-logic within a category, AND-logic across categories. Each pill cycles through **three states** on click: neutral → include (`.active`, added to `activeFilters`) → exclude (`.excluded`, added to `excludedFilters`) → neutral. Excludes are AND-ed as negations, so an excluded value is dropped even when another pill in the same category includes it.
  - Pill values are **derived from `products.json` at load** (`buildAllPills()`), not hardcoded — a new type/system/setting/publisher in the data gets a pill automatically, in first-appearance order. The lists below are therefore a snapshot of the current data, not a fixed schema:
  - **Type** (8 values): `boxed set`, `accessory`, `magazine`, `hardcover`, `adventure`, `boardgame`, `Flip-book`, `miniatures`
  - **System** (10 values): `OD&D`, `Basic D&D`, `AD&D 1e`, `AD&D 2e`, `Dragon Quest`, `Saga`, `D&D 3e`, `Chainmail`, `D&D 3.5`, `D&D 4e` — `Saga` is the Dragonlance Fifth Age line (13 products, 1996–1998)
  - **Setting** (21 values + null): Greyhawk, Blackmoor, Mystara, Ravenloft, Celtic, Dragonlance, Conan, Forgotten Realms, Kara-Tur, Lankhmar, Planescape, Spelljammer, Historical, Dark Sun, Thunder Rift, Al-Qadim, Birthright, Diablo, Chainmail, Eberron, Points of Light — plus `(no setting)` for products where `setting` is null (the `__none__` sentinel, always sorted last). `(no setting)` is now the largest bucket by far (1,076 of 1,871), because 663 products landed in it when `Various` was retired (the 661 magazines plus the two `hardcover` Dragon/Dungeon Magazine Annuals, ids 1988-1989); `Mystara (2E)` was likewise folded into `Mystara` upstream
  - **Publisher** (3 pills): `TSR`, `WotC`, `Paizo` (the last being ~118 Dragon/Dungeon magazine issues, 2002–2007). stats.html charts all three as well.
- **Text search** — live, debounced 200ms, case-insensitive, searches: `title`, `dtrpg_title`, `module_code`, `product_code`, `authors`, `cover_artist`, `blurb`. A "Title only" checkbox beside the search box narrows this to `title` alone; its state persists as `text_title_only` in `tsr_active_filters` and is honored by `applyFiltersToProducts()` in `utils.js`, so it also scopes the text search used by `index.html`/`spread.html` navigation, both games, and `stats.html`'s current-filter mode — not just `search.html`'s own grid
- Pill counts show total products per value (not filtered count) — they are built once on load
- Results render as a thumbnail grid (`aspect-ratio: 3/4`, lazy-loaded); clicking a card → `index.html#id=<N>`
- Filter state is saved to `localStorage` key `tsr_active_filters` (JSON) on every change and restored on load; a "Clear Filters" button removes it
- **Default (seed-once):** on a browser's first ever visit, `utils.js` seeds `tsr_active_filters` with `exclude_type: ['magazine']` so magazines are hidden by default app-wide (gallery, spread, both games). A `tsr_filters_seeded` marker ensures this happens at most once, so after the first visit the user has full control and "Clear Filters" truly clears (it will not re-add the default)
- `index.html` and `spread.html` read `tsr_active_filters` on load and navigate only within the filtered product set; position is tracked by product id (`tsr_current_id`) rather than array index

## Key Conventions
- Page-specific logic stays in its own HTML file; shared filter logic lives in `utils.js`; shared styles in `common.css`
- `products.json` is generated — never hand-edit it; run `convert_csv.py` instead
- `products.json` entries include 24 fields; CSV columns with spaces are normalized to underscores (`product_code`, `module_code`); `cover_url` points to a local path (`covers/full/{id}.avif`) if the image has been downloaded, otherwise the remote URL from covers.csv
- `covers/full/` is AVIF and `covers/thumb/` is JPEG — never assume the two share an extension; use `thumbUrl()` from `utils.js`
- **The local file always wins.** `covers/full/` is the authoritative source of cover art. `cover_url` / `backcover_url` in covers.csv are a *starting point and a fallback* — the URL that was used to seed the folder once, not a description of what is in it now. Covers get replaced by hand whenever a better scan is found, and **this divergence is expected to grow over time**. Never re-fetch over a file that already exists locally, never treat a URL as the source of truth, and never "repair" a local file to match its URL
- A blank `cover_url` is therefore meaningful, not missing data: it says the upstream scan was rejected outright and the local file is the only cover. Do not source a replacement URL from tsrarchive to fill it
- **AVIF is the master format from id 1968 onward.** Covers added from that point exist only as `.avif` and that is intended — there is no JPEG original to preserve and none should be manufactured. `tools/avif_convert.py --adopt` deleting the source JPEG is correct behaviour, not a bug to fix. The pre-migration JPEG masters (ids up to ~1961) survive in git history and in the off-machine tar purely as an **escape hatch in case AVIF ever proves to be the wrong path** — they are insurance, not a working master set, and nothing in the pipeline should try to keep the two formats in step
- Dark theme colors are defined as CSS variables in `common.css` — edit them there, not in individual HTML files
- Responsive breakpoint at 900px (3-column → 1-column layout)

## Data Pipeline

> **`convert_csv.py` does NOT convert images.** The name is about CSV -> JSON.
> It reads the CSVs and whatever files happen to be sitting in `covers/full/`,
> and writes `products.json`. Nothing else in it touches an image.
> Only `tools/avif_convert.py --adopt` converts anything.
>
> - **Text-only CSV edit** (title, artist, blurb, dtrpg link): `convert_csv.py`
>   alone is the whole job.
> - **Any change involving images** (new products, re-fetched covers, a
>   hand-dropped file): `convert_csv.py` is the **last of four steps**. See
>   *Image Download Pipeline* below and run all of them, in order.

To regenerate `products.json` after a text-only CSV edit:
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
- `covers/full/{id}.{ext}` — front cover, named by the product's CSV `id` field (JPEG on arrival; converted to `.avif` by `--adopt`)
- `covers/full/{id}-back.{ext}` — back cover (URL read from `covers.csv` `backcover_url` column)

- Already-downloaded files are skipped automatically (idempotent).
- The script reads `../tsr_products/covers.csv` directly to get `backcover_url` for each product.
- 404s on back covers are expected — not all products have back cover images on tsrarchive.com.

**Workflow when adding a new year of images:**
1. `python download_covers.py <year>` ← covers arrive as JPEG
2. `python tools/avif_convert.py --adopt` ← **required**: converts each stray JPEG to AVIF in place, checks the result decodes at identical dimensions, and only then deletes the JPEG
3. `python generate_thumbs.py <start_id> <end_id>` ← thumbnails, generated from the AVIF
4. `python convert_csv.py` ← regenerate JSON **last**; local paths are picked up automatically

**The order matters, and both ways of getting it wrong are worth knowing:**

- **Skipping step 2 entirely** is the dangerous one, because *nothing visibly
  breaks*. The JPEGs stay in `covers/full/`, `products.json` records
  `covers/full/{id}.jpg`, a matching `.jpg` thumbnail is generated, and the site
  serves all of it happily. The only symptom is that those products are silently
  still JPEG — roughly double the bytes — quietly eating the headroom the
  migration bought. Nobody notices until the Pages cap is in sight again.
- **Running step 4 before step 2** fails loudly instead: `products.json` records
  `.jpg` for files that then become `.avif`, and every one of those products
  renders a broken image.

`redownload_cover.py` chains steps 2–4 automatically for exactly this reason;
`download_covers.py` deliberately does not, so after a bulk fetch the remaining
three steps are yours to run.

**Verifying a batch landed correctly** — after any image work, this must print 0:
```bash
ls covers/full/*.jpg 2>/dev/null | wc -l    # stray JPEGs; 0 means --adopt ran
```
and `products.json` should contain no `covers/full/*.jpg` paths:
```bash
grep -c 'covers/full/[^"]*\.jpg' products.json    # expect 0
```

## generate_thumbs.py internals
- Reads `covers/full/` (`.avif`/`.jpg`/`.jpeg`, case-insensitive) and writes 300px-wide JPEGs to `covers/thumb/`
- Output is named by *stem*, so an `.avif` source still yields a `.jpg` thumbnail
- The source glob is deduped with `set()` — Windows matches globs case-insensitively, so `*.jpg`/`*.JPG` would otherwise return every file twice
- Maintains aspect ratio; JPEG quality 75; uses Pillow (`pip install Pillow`)
- Idempotent — existing files are skipped
- Optional ID range: `python generate_thumbs.py <start_id> <end_id>`
- `search.html`, `game.html` and `odd1out.html` derive thumb URLs via `thumbUrl(cover_url)` from `utils.js` — a bare `.replace('/full/', '/thumb/')` is wrong now that the two trees use different formats

## download_covers.py internals
- Reads `products.json` to filter products by year
- Reads `../tsr_products/covers.csv` to get `backcover_url` for each product directly (no URL derivation needed)
- Both front and back downloads are idempotent — existing files are skipped via `local_cover_exists()`, which globs `{id}.*` / `{id}-back.*` and is **extension-agnostic**. This matters: the check used to test for `{id}-back.jpg` specifically, and after the AVIF migration that reported all 1,172 already-downloaded back covers as missing. Never reintroduce a fixed suffix here
- Targets are products whose `cover_url` is truthy, so **a product with no front cover never gets its back cover fetched either** (this is why id=1968 kept a hotlinked `backcover_url` until its front was supplied)

## redownload_cover.py internals
- Reads both `cover_url` and `backcover_url` from **`../tsr_products/covers.csv`** — not from `tsr_products.csv`, which has no `cover_url` column at all. It read the master table until it was fixed, so `load_remote_urls()` always came back empty and every id reported "not found in CSV"
- Downloads to scratch `.{id}.download.*` files and swaps them in only once the front cover is safely on disk. It used to delete first, which meant a dead link or network blip left the product with no cover at all — worse now that `covers/full/` is the only copy of the image in the repo
- Deletion is selective (`delete_existing(pid, front=, back=)`), so replacing only the front does not take an existing back cover with it
- **Refuses by default to overwrite a cover that already exists locally** — it reports the existing files and skips. `--force` is required to replace one, and there is no undo beyond git. This is the local-file-wins rule enforced in the one tool whose whole job is to pull from upstream
- An id absent from covers.csv is reported and skipped without deleting anything, so a deliberately blank `cover_url` is safe from both directions
- Chains `tools/avif_convert.py --adopt` -> `generate_thumbs.py` -> `convert_csv.py` automatically after downloading

## convert_csv.py internals
- Joins 4 CSV files on `id`: tsr_products.csv (main), covers.csv, blurbs.csv, dtrpg.csv
- Exports 24 fields per product: id, order, year, month, day, product_code, title, module_code, type, system, setting, publisher, confidence, edition, authors, pages, isbn, cover_url, cover_artist, semester, backcover_url, blurb, dtrpg_url, dtrpg_title
- CSV columns with spaces (`product code`, `module code`) are normalized to underscores
- `cover_artist` normalization: strips `LIKELY:` prefix; converts empty/blank to `null`; keeps `N/A` as the string `"N/A"` (meaning artist credit is explicitly not applicable, distinct from unknown/missing)
- `blurb` normalization: CRLF and lone CR inside the quoted CSV field are normalized to `\n`. The CSV must be opened with `newline=''` (required by the `csv` module), which preserves whatever line endings the source file carries — without this normalization an upstream rewrite of `blurbs.csv` churns every blurb in the `products.json` diff while changing nothing that renders
- `season` field removed (no longer in source data)
- Always reads local CSV files directly (no remote URL fallback)
- Local cover files (`covers/full/{id}.*`) are the primary image source; `cover_url` from covers.csv is a fallback — products with local files are included even without a CSV cover_url
- Validates month (1–12) and title; invalid months are set to `null` with a warning; missing titles are skipped
- **Missing-cover reporting.** Every product is expected to have a front cover; a missing back cover is normal. Both are reported, at different volumes, and *neither* drops the product any more:
  - **`ACTION NEEDED` (banner, printed last)** — no front cover anywhere (no `covers/full/{id}.*` **and** no `cover_url` in covers.csv). The product **is still exported**, with `cover_url: null`, so the record stays browsable and correctable later. Lists id, year, title, type, and both fixes: drop the image at `covers/full/{id}.jpg`, or add a `cover_url` for that id in covers.csv. This was a silent `continue` until ids 1921–1924 (the 1994 Player Packs) were found missing from every import with no trace
  - **`WARNING`** — no back cover. Always reported, since art can turn up later. Non-magazine products are listed individually (currently 8); the ~651 magazines legitimately never had backs and are collapsed to a trailing count so they don't bury the actionable ones
- **`cover_url` is nullable** as a result, and a null can be intentional as well as accidental. Consumers must guard it: assigning `null` to `img.src` requests `/null` and 404s, and `thumbUrl(null)` returns null rather than throwing. `search.html` renders a dashed "No cover yet" placeholder card, `index.html` and `spread.html` show their existing "not available" state without issuing a request, and both games (`game.html`, `odd1out.html`) drop coverless products from the pool since judging cover art is the whole point
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
- Magazine `setting` is **null** — they are not setting-specific publications. It was the string `"Various"` until that marker was retired upstream (2026-09-11); nothing in the app keys off the old value any more

### Dungeon Magazine covers (ids 1472–1692)
221 magazine issues added (Dungeon #1 through Dungeon #221, 1986–2013). Cover images
sourced from `cf.geekdo-images.com` URLs (BoardGameGeek); no back covers exist in covers.csv.
- Systems span AD&D 1e (early issues), AD&D 2e, D&D 3e, D&D 3.5, D&D 4e (digital era)
- Magazine `setting` is **null** (formerly `"Various"`, retired upstream)
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
