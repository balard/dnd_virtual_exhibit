# AVIF Migration Plan

Convert `covers/full/` from JPEG to AVIF at unchanged resolution, get the
published Pages site back under the 1 GB cap, and leave enough headroom for the
5e expansion.

**All figures below were re-measured against the working tree on 2026-09-11**
(3,019 cover files, 1,839 products, 115 commits). An earlier draft of this plan
was written at 2,990 files / 51 commits and its numbers no longer hold — in
particular it described the site as *approaching* the cap. It is over it.

---

## The situation

| | earlier draft | measured now |
|---|---|---|
| `covers/full/` | 932.7 MB | **943.3 MB** (3,019 files) |
| `covers/thumb/` | 78.5 MB | **79.2 MB** (3,019 files) |
| non-image site content | 4.6 MB | **4.6 MB** (`products.json` is 2.7 MB) |
| **published site total** | 1,015.7 MB (99.2% of cap) | **1,077,096,163 B = 1.0031 GiB / 1.077 GB** |
| `.git` | 967 MB | **1,001 MB** (571 MiB packed + 421 MiB loose) |
| commits | 51 | 115 (4 unpushed) |

GitHub's rule is "published GitHub Pages sites may be no larger than 1 GB." The
site is past that on the decimal reading and just past it on the binary one.
This is no longer preventative work.

Note the `.git` figure: 421 MiB of it is loose objects.

> **This was misread, and Phase 6 records the correction.** Loose objects are
> not slack — they are content that has not been packed yet. `git gc` packs
> them; it cannot discard anything still reachable from history. The actual
> reclaim was **29 MB**, not "a large part of 421 MiB".

---

## The decision

- **`covers/full/` → AVIF, 4:4:4, full resolution, quality picked in Phase 2**
  (start from q50).
- **`covers/thumb/` stays JPEG q75, untouched.** See below.
- **The history rewrite is decoupled** from the format migration and is optional.

Projected site size by quality — pick one in Phase 2 by looking at images, not
at this table:

| quality | `covers/full/` | site total | % of 1 GiB | headroom | ≈ products of room* |
|---|---|---|---|---|---|
| q45 | 404 MB | **488 MB** | 47.6% | 536 MB | ~1,900 |
| **q50** | 480 MB | **564 MB** | 55.0% | 460 MB | ~1,500 |
| q55 | 574 MB | **658 MB** | 64.3% | 366 MB | ~1,150 |
| q60 | 650 MB | **734 MB** | 71.6% | 290 MB | ~750 |

\* At the collection's current average of ~1.64 image files per product plus its
thumbnail. A 5e expansion is plausibly 200–400 products, so every row survives
it — but q50 survives it with room to spare, and there is no second conversion
to fall back on later.

---

## Why AVIF, and not "just optimise the JPEGs"

Re-measured on a byte-weighted 150-file random sample of `covers/full/`
(44.3 MB of the 943.3 MB), 4:4:4, speed 6:

| variant | size vs original |
|---|---|
| JPEG q82, same resolution | **~102%** — *larger* |
| WebP q80 | 73.3% |
| AVIF q60 | 68.9% |
| WebP q75 | 59.5% |
| AVIF q55 | 60.9% |
| **AVIF q50** | **50.9%** |
| AVIF q45 | 42.8% |

The first row is the finding: **the existing JPEGs have no slack.** Re-encoding
them at the same resolution makes them bigger. There are no fat outliers to trim
either — 77.5% of all bytes sit in one narrow band at 1600–1799 px on the long
edge, confirmed by measuring every file. Format change is the only lever that
does not cost resolution.

> **Correction against the earlier draft.** It reported AVIF q60 at 56.9%, then
> 62.6% on a second sample, and advised treating the truth as "57–63%". Two
> independent samples here (a 40-file one confined to the dominant size band,
> and the 150-file whole-directory one above) both land at **68–69%**. The
> earlier target of a 645 MB site at q60 is not reachable; q60 gives ~734 MB.
> This is why the recommended starting quality is q50, not q60.

---

## Why resolution is kept

The numbers argue for this more strongly than the earlier draft did. Compare
equal-ish output sizes:

| variant | size vs original |
|---|---|
| **AVIF q50, full ~1600 px** | **50.3%** |
| AVIF q60, downscaled to 1400 px | 55.7% |
| AVIF q55, downscaled to 1400 px | 46.8% |
| JPEG q82, downscaled to 1400 px | 81.9% |

Full-resolution q50 is *both smaller than and higher-resolution than* q60-at-
1400px. Downscaling is simply a bad trade here; it only starts to pay below q55,
where the quality risk is the binding constraint anyway.

The layout backs this up. `.viewer` (index.html:127) is `max-width: 1600px` with
`grid-template-columns: minmax(240px, 1.5fr) 3fr 1fr`, so the cover column gets
3/5.5 of ~1,550 px ≈ **845 CSS px**. A portrait cover at `max-height: 90vh` on a
1080p display renders ~970 CSS px tall, which is ~1,940 device px at DPR 2. The
current ~1600 px sources are already slightly *under*-specced for a retina
display. Do not downscale them.

---

## Why `covers/thumb/` stays JPEG

Measured two ways, on the 300 px thumbnails:

| approach | result |
|---|---|
| Transcode existing thumbs → AVIF q50 | 64.9% (saves ~28 MB) |
| Transcode existing thumbs → AVIF q60 | 83.3% |
| **Regenerate from the full covers → AVIF q50** | **76.8%** of current |
| Regenerate from the full covers → AVIF q60 | **106%** — *larger than the JPEGs* |

At 300 px AVIF's advantage mostly evaporates and above q55 it inverts. The best
honest case saves ~28 MB (2.7% of the site) at the cost of a second generation
of loss on already-lossy thumbnails and slower decode in the `search.html` grid,
which renders hundreds of them at once. Not worth it. Leave them alone.

The consequence is a **code change**, not a data change: `cover_url` will end in
`.avif` while thumbs remain `.jpg`, so the four places that derive a thumbnail
URL by string-swapping `/full/` → `/thumb/` must also swap the extension. That
is Phase 1, and it lands before anything is converted.

---

## Preconditions (re-verified across all 6,038 files)

Re-run on the current tree, not inherited from the earlier draft:

- **EXIF orientation:** 2,325 files carry orientation `1`, 3,713 have no tag.
  **Zero rotated images** — no `exif_transpose` needed (the scripts call it
  anyway, as a no-op safety net).
- **Colour profiles:** 2,261 files carry `sRGB IEC61966-2.1`, 3,777 carry none.
  **No Adobe RGB, no ProPhoto** — dropping the ICC profile is colour-safe. If
  this changes for newly downloaded covers, re-check before converting.
- **Modes:** 6,036 RGB plus exactly two palette-mode files —
  `covers/full/1042.jpg` and `covers/full/1139.jpg`. The scripts' `.convert("RGB")`
  handles them.
- **Unreadable files:** none.
- **`products.json`:** 1,839 products, **0** remote `cover_url`s, **0** remote
  `backcover_url`s, **0** null covers, and every local path is `.jpg`. Nothing
  hotlinks, so the conversion covers the whole served set.
- **Pillow:** needs ≥ 11.3 for built-in AVIF (`PIL.features.check("avif")`).
  Verified working on the installed Pillow 12.1.1.
- **Encoding cost:** ~0.21 s/file single-threaded at speed 6, so ~11 min for
  3,019 files serially, a few minutes across cores.

---

## Tooling

Three scripts, all new in `tools/`. None of them writes anywhere but `build/`
until you explicitly promote:

- **`tools/verify_backup.py`** — the Phase 0 gate: hashes every member of a tar
  backup against the live tree.
- **`tools/avif_preview.py`** — the Phase 2 visual gate.
- **`tools/avif_convert.py`** — bulk conversion, verification, promotion,
  revert, and the steady-state `--adopt` path for future data batches.

`tools/avif_convert.py` never overwrites `covers/full/` in place during the
migration. It fills a staging tree and promotes by two directory renames:

```
covers/full        ->  covers.jpeg.bak/full     (the JPEG originals)
build/covers/full  ->  covers/full              (the AVIF tree)
```

Both renames are instant and exactly reversible, which is what makes the
"test locally, revert if it looks bad" loop cheap.

---

## Phase 0 — Back up the originals off-repo

`covers.jpeg.bak/` (Phase 4) is the fast undo, but it lives on the same disk and
gets deleted at the end of Phase 5. Make a real backup first.

**Status: COMPLETE.** `D:/RPG/tsr-covers-jpeg-20260911.tar`, 991,477,760 B,
3,019 members, re-verified byte-for-byte after being moved to the second
physical drive. Separate spindle from the working tree on `C:`, which is the
property that matters.

```bash
tar -cf "/c/Users/Master/tsr-covers-jpeg-$(date +%Y%m%d).tar" \
    -C "/c/Users/Master/Desktop/teste calude/dnd_virtual_exhibit" covers/full
```

**Uncompressed on purpose.** Measured on a 40-file sample, gzip saves 5.7% on
this content — the JPEGs are already entropy-coded, so there is almost nothing
left to squeeze. That buys ~54 MB in exchange for minutes of CPU and, more
importantly, fragility: a single corrupted byte in a gzip stream costs you
everything after it, whereas a damaged plain tar costs you one file. For an
archive that may be the only copy, robustness wins. Plain tar took 15 seconds.

Verify it properly — a member count is not verification. Stream every member
out of the archive and hash it against its source (no extra disk needed):

```bash
python tools/verify_backup.py "C:/Users/Master/tsr-covers-jpeg-20260911.tar"
```

Expect `members 3019 / missing 0 / extra 0 / hash mismatch 0`. Anything else
and the migration does not start.

Then get it off this machine. Options, in rough order of preference:

- **An external drive or your own cloud storage.** Simplest, and keeps a ~1 GB
  archive of scraped cover art out of a public repo.
- **A GitHub Release asset on this repo** — up to 2 GB per file, does not count
  against the repo tree or the Pages site. Note this repo is public, so the
  asset would be publicly downloadable; the same images are already served from
  the Pages site, but a single bulk archive is a different thing from 3,019
  separate requests, so make that call deliberately:

  ```bash
  gh release create covers-jpeg-archive "C:/Users/Master/tsr-covers-jpeg-20260911.tar" \
    --title "JPEG cover masters (pre-AVIF)" \
    --notes "Original JPEG covers/full as of the AVIF migration."
  ```

Re-downloading from tsrarchive.com / BoardGameGeek years from now is not
guaranteed to work. Do not skip this.

---

## Phase 1 — Update the pipeline and the thumbnail URL derivation

**Status: COMPLETE** — commits `b43ad1d` (plan + tooling) and `0c5af9d`
(the code changes). Verified as a true no-op: `convert_csv.py` emitted
byte-identical output before and after, and all five pages were checked in a
browser against the still-JPEG tree with zero broken images and an empty
console. Not pushed.

**These come first, before anything is converted.** Every one of the four
changes below is an exact no-op against the current all-JPEG tree — verified:
`covers/full/` and `covers/thumb/` are 3,019 `.jpg` files each, with no
`.jpeg` and no uppercase variants, so nothing here changes a single URL or
output filename while the tree is still JPEG.

That is the whole point of doing them now. Apply them, run the site, and
confirm it behaves *identically* to today. You get a green baseline, and by the
time Phase 4 promotes the AVIF tree the only variable left is the image format
itself. Doing it the other way round means testing a knowingly-broken site and
then testing again.

Two further reasons the ordering matters:

- **`.gitignore` must list `covers.jpeg.bak/` before Phase 4 creates it.**
  Phase 5 runs `git add -A`. The ignore rule should already exist by then, not
  be added alongside the thing it protects.
- These changes are a small, self-contained, safely committable unit. Landing
  them as their own commit before the ~3,000-file image commit means the two
  can be reverted independently later.

Four changes. None of them is large, but the first one is load-bearing: once
the covers are AVIF, every thumbnail 404s without it.

**1. Thumbnail URL derivation — `utils.js`.** Four call sites do
`cover_url.replace('/full/', '/thumb/')` and now need the extension swapped too.
Add one shared helper rather than editing the same expression four times:

```js
/* cover_url is covers/full/<id>.avif but thumbnails stay JPEG (AVIF gives
   almost nothing at 300px and decodes slower in a large grid). Remote
   fallback URLs have no local thumbnail, so they pass through unchanged. */
function thumbUrl(coverUrl) {
    if (!coverUrl) return null;
    if (!coverUrl.startsWith('covers/full/')) return coverUrl;
    return coverUrl.replace('/full/', '/thumb/').replace(/\.[^.\/]+$/, '.jpg');
}
```

Then replace the expression at search.html:484, game.html:637, game.html:667,
and odd1out.html:606 with `thumbUrl(p.cover_url)` / `thumbUrl(product.cover_url)`.

**2. `generate_thumbs.py`** — currently reads only JPEG and names the output
after the source file, which would write a JPEG called `123.avif`:

- `extract_id()` regex (generate_thumbs.py:29): `^(\d+)(?:-back)?\.jpe?g$`
  → `^(\d+)(?:-back)?\.(?:jpe?g|avif)$`
- source glob (generate_thumbs.py:48): add `"*.avif"`
- output path (generate_thumbs.py:65): `OUTPUT_DIR / src_path.name`
  → `OUTPUT_DIR / (src_path.stem + ".jpg")`

The existing skip-if-exists idempotency then keeps working unchanged, and all
3,019 current thumbs stay valid.

**3. `convert_csv.py`** — make the glob deterministic. Today
`glob(f'{pid}.*')` takes whatever comes first, which is fine while exactly one
file per id exists but is ambiguous during an `--adopt` window where both
`123.jpg` and `123.avif` are briefly present. Sort with an explicit preference:

```python
for f_path in sorted(LOCAL_COVERS_DIR.glob(f'{pid}.*'),
                     key=lambda p: (p.suffix.lower() != '.avif', p.name)):
```

Same for the `{pid}-back.*` lookup at convert_csv.py:115.

**4. `.gitignore`** — add `covers.jpeg.bak/` so the fast-undo tree can never be
committed by accident. (`build/` is already ignored.)

**Verify the no-op claim before moving on.** With the tree still all-JPEG:

```bash
python convert_csv.py          # products.json must come back byte-identical
git diff --stat products.json  # expect no output at all
python -m http.server 8000
```

Then load `search.html`, `game.html` and `odd1out.html` and confirm the
thumbnail grids render exactly as before. If `products.json` changed or a
thumbnail 404s now, the helper or the glob sort is wrong — fix it here, while
the originals are still in place and the diff is three files wide.

Commit this on its own:

```bash
git commit -am "[refactor] derive thumb URLs via utils.js thumbUrl(); accept AVIF in the pipeline"
```

### The ongoing workflow after this

`download_covers.py` and `redownload_cover.py` keep fetching JPEG from the
remote archives — that is correct, and they need no changes. New covers get
folded in with one extra step:

```bash
python download_covers.py <year>
python tools/avif_convert.py --adopt --quality 50   # NEW: JPEG -> AVIF, verified, then dropped
python generate_thumbs.py <start_id> <end_id>
python convert_csv.py
```

`--adopt` encodes each stray `.jpg` in `covers/full/` to `.avif` alongside it,
confirms the result decodes at identical dimensions, and **only then** deletes
the JPEG. Note the ordering: `--adopt` runs *before* `generate_thumbs.py`, so
thumbnails are generated from the AVIF. That is one extra generation of loss on
a 300 px thumbnail and is not worth reordering around.

Update CLAUDE.md's "Workflow when adding a new year of images" and its
`covers/full/` description to match.

---

## Phase 2 — Quality gate (before converting anything)

**Status: COMPLETE — q50 chosen.** The gate was run on the ten covers that
compress *worst* at q50 (found by encoding a 220-file sample and ranking by
output ratio), not the highest-bytes-per-pixel files: seven of the ten turned
out to be text-heavy back covers, which is where AVIF's smoothing shows first.
Verdict on inspection at 100%: little visible loss, q50 or q55 both acceptable.
q50 taken for the extra 94 MB of headroom, since there is no second conversion.

This is an art-appreciation site. AVIF smooths film grain and scan texture in
ways PSNR does not punish, and painted 1970s–80s covers are exactly the content
where that shows. **Look at the images before you convert 3,019 of them.**

```bash
python tools/avif_preview.py --qualities 45 50 55 60
```

Writes `build/avif_preview/index.html`. Open it and **view at 100% zoom** — the
top strip of each product is a 1:1 centre crop with `image-rendering: pixelated`
so the browser does not smooth over the artifacts, and the bottom strip is the
whole cover for an overall-impression check.

The auto-picked sample is the 12 highest bytes-per-pixel files. That finds the
*largest* files, which is not quite the same as the *hardest to encode* — a
bloated near-lossless scan has high bytes-per-pixel and compresses beautifully.
So also pass a hand-picked set of genuinely awkward covers:

```bash
python tools/avif_preview.py <stems...> --qualities 45 50 55 60 --crop 700
```

Good candidates: dark dungeon scenes with shadow gradients, airbrushed skies
(banding), heavy canvas or paper texture, and any cover with fine ink linework.
Back covers (`--` stems like `830-back`) are often text-heavy, which is a
different and useful failure mode.

**What you are deciding:** the lowest quality at which you cannot tell the
difference at 100% zoom. Write it down; everything after this uses it.
If nothing below q55 passes, take q55 and the 658 MB row — it is still a
365 MB improvement and still buys the 5e expansion.

---

## Phase 3 — Bulk conversion into the staging tree

**Status: COMPLETE.** 3,019 encoded at q50 / 4:4:4 / speed 6 across 12 cores in
5m39s, 0 failures. `--verify`: 3,019 sources, 3,019 staged, 0 missing, 0
undecodable, 0 dimension mismatches, 0 orphans. 943.3 MB -> 479.0 MB (50.8%),
against a 50.9% projection.

Nothing under `covers/` is touched in this phase. Sanity-check the projection
first:

```bash
python tools/avif_convert.py --dry-run --quality 50
```

Then fill `build/covers/full/`:

```bash
python tools/avif_convert.py --quality 50
```

It is parallel across cores, idempotent (already-staged files are skipped, so an
interrupted run just resumes), and it fails loudly per file rather than silently
dropping anything. Then:

```bash
python tools/avif_convert.py --verify
```

`--verify` checks that every JPEG source has a staged AVIF, that each one
**decodes**, and that its dimensions match the source exactly. It also reports
orphan staged files and the real (not sampled) size ratio. **It exits non-zero
and refuses to bless the tree if anything is missing, undecodable, or
mis-sized.** Do not continue past a failure.

---

## Phase 4 — Promote, regenerate, and test locally (no commit)

**Status: COMPLETE.** Promoted, `convert_csv.py` re-run, all six pages driven in
a browser: index (front + flip to back, both `.avif`), spread (2/2), search
(1,208 thumbs, 0 broken, still `.jpg`), both games (5/5 each), stats (5 charts).
Empty error console throughout; `.avif` served as `image/avif`.

**Published site: 590,337,845 B = 563.0 MiB**, down from 1,077,096,163 B.
54.8% of the former size, 461 MiB of headroom under the cap.

```bash
python tools/avif_convert.py --promote   # two renames; JPEGs -> covers.jpeg.bak/
python convert_csv.py                    # cover_url now points at .avif
python -m http.server 8000
```

`convert_csv.py` needs no change for this: its local-file lookup is already
`LOCAL_COVERS_DIR.glob(f'{pid}.*')` (convert_csv.py:103), extension-agnostic.
Expect its diff on `products.json` to be exactly 3,019 path rewrites,
`.jpg` → `.avif`, and nothing else. Check that.

**Do not commit yet.** Click through:

- **index.html** — front cover, flip to back, arrow-key navigation, the preload
  path at index.html:1089 (it constructs `new Image()` for the next product).
- **spread.html** — both covers side by side; this is the widest rendering in
  the app and the one most likely to expose softness.
- **search.html** — the thumbnail grid. Thumbs are still the same JPEGs they
  were in Phase 1, so this grid should look untouched. Anything broken here is
  a `thumbUrl()` bug, not an AVIF one.
- **game.html / odd1out.html** — same thumb path.
- **stats.html** — no images, but confirm it still reads `products.json` cleanly.

Check DevTools for 404s and compare a few covers against the tarball from
Phase 0 at full zoom.

### If it looks wrong

```bash
python tools/avif_convert.py --revert   # JPEGs back in place, AVIF back to build/
python convert_csv.py                   # cover_url back to .jpg
```

You are exactly where you started, with the Phase 1 commit still valid and the
conversion uncommitted. Re-run Phase 3 at a higher quality and repeat. Rehearse
this once before you need it.

---

## Phase 5 — Commit and ship

**Status: COMPLETE.** Pushed; the Pages deploy succeeded with no 404s. Verified
independently against the live site: `covers/full/1.avif` and
`covers/full/1968.avif` return `image/avif`, `covers/thumb/1968.jpg` returns
`image/jpeg` (the format split holds in production), `products.json` 200.

Original status line follows for the record:
`0416232` changed 6,039 files; the pre-push check was clean (3,019 deletions,
3,019 additions, `products.json`, nothing else, `covers.jpeg.bak/` ignored).

Still to do, in order:
1. `git push` (11 commits: 4 predate the migration)
2. Confirm the Pages deploy succeeds and no size warning appears
3. Load the live index / spread / search; check for 404s and `image/avif`
4. Only then `rm -rf covers.jpeg.bak` — the D: tar stays as the permanent backup

### Work done after the conversion, outside the phases

Folding the deferred 31-product import through the steady-state path turned
up three faults in the cover pipeline that the plan never anticipated:

- `download_covers.py` tested for `{id}-back.jpg` specifically, so after the
  migration it saw all 1,172 downloaded back covers as missing and would have
  re-fetched them as JPEG (~350 MB of duplicates). Now extension-agnostic.
- `redownload_cover.py` read `cover_url` from `tsr_products.csv`, which has no
  such column — it resolved zero ids and had been entirely non-functional.
- The same script deleted the existing cover *before* downloading the
  replacement, so a dead link left the product with nothing. Now downloads to
  scratch files and swaps in only on success — and refuses outright to
  overwrite a local cover without `--force`, because `covers/full/` is
  authoritative and covers.csv is only a fallback.

CLAUDE.md's add-a-year workflow also had `convert_csv.py` running *before* the
conversion, which would record `.jpg` paths for covers about to become `.avif`.

```bash
git add -A
git commit -m "[perf] convert covers/full to AVIF q50; thumbs stay JPEG"
git push
```

This is a large commit — ~3,019 deletions and ~3,019 additions plus the
`products.json` rewrite. Expect the push to take a while. The code changes are
already in their own Phase 1 commit, so this one is purely data: if the AVIF
ever needs undoing, it is a single commit to revert.

Before pushing, confirm nothing stray got swept in:

```bash
git status --short | grep -v '^D  covers/full/\|^A  covers/full/'
```

Expect only `products.json`. In particular `covers.jpeg.bak/` must not appear —
that is what the Phase 1 `.gitignore` change is for.

Then verify the live site, not just localhost:

- Confirm the Pages deploy succeeded and no size warning appears in
  **Settings → Pages** or the deploy log.
- Load the live `index.html`, `spread.html`, and `search.html`; check the
  Network tab for 404s and confirm the served covers are `image/avif`.
- Re-measure: the published site should match the Phase 2 quality row.

Once the live site is confirmed good, delete the local undo tree:

```bash
rm -rf covers.jpeg.bak
```

The Phase 0 tarball remains the permanent backup.

### Browser support note

AVIF is supported by Chrome 85+, Firefox 93+, Safari 16.4+ (March 2023) and
Edge 121+ — roughly 95–96% of traffic. There is no `<picture>` fallback in this
plan, because maintaining a parallel JPEG tree would defeat the entire purpose.
For a personal art-browsing site this is an acceptable trade; it is worth being
deliberate about it rather than discovering it later.

---

## Phase 6 — Git housekeeping (separate decision, do not bundle)

After Phase 5 the *published site* problem is solved. The *repository size*
problem is a different one, and the earlier draft bundled them together. Keep
them apart.

**Status: DONE.** `git gc --prune=now`, 35s, `git fsck` clean afterwards.

```
             before                 after
  .git       1,498 MB               1,469 MB      (-29 MB)
  loose      911.47 MiB             0
  pack       570.88 MiB             1.43 GiB
```

**The prediction in this plan was wrong and the result is worth understanding.**
The loose objects were not reclaimable slack; they were the newly written AVIF
blobs waiting to be packed. `gc` packed them, which is why the pack grew by
roughly what the loose store shrank by. Nothing reachable from history can be
dropped, so the only real saving was genuine garbage: 29 MB.

`.git` now sits at ~1.43 GiB and will stay there. It holds both formats: the
AVIF at HEAD and the JPEG blobs throughout history. That is well inside
GitHub's 5 GB soft limit and costs nothing but local disk.

**Consider this separately, later, or not at all:**

`git filter-repo` to purge the JPEG blobs from all 115 commits would take `.git`
from ~600 MB to perhaps ~250 MB. But it rewrites every commit, requires a
force-push over the whole history, and is irreversible once the old objects are
gone from GitHub. Weigh that against what it actually buys:

- GitHub's repository soft limit is **5 GB**, not 1 GB. Only the *published
  site* is capped at 1 GB, and Phase 5 already fixed that.
- Local `.git` size costs disk, nothing else.
- Clone time for a solo repo you have already cloned is not a real cost.

Recommendation: **`git gc` is done; do NOT run `filter-repo` — not now, not
later.** The reason has grown stronger since this plan was written. `covers/full/` is the authoritative source of cover art and diverges from the upstream URLs over time as better scans replace poor ones, which means **git history is the only record of every superseded cover**. The URLs in covers.csv cannot reconstruct them: they point at the files that were rejected. Purging the JPEG blobs would not be reclaiming space, it would be destroying curation work. Revisit it only if the
repo approaches 5 GB, at which point the right answer is more likely to be
moving images out of git entirely (see below) than rewriting history again.

---

## What this does not solve

**AVIF is a one-time lever.** There is no second conversion. At q50 the site
lands near 564 MB with ~460 MB of headroom, which comfortably absorbs a 5e
expansion of 200–400 products (~60–150 MB) and leaves room after it. But the
ceiling is still 1 GB and the collection still only grows.

If the site ever approaches the cap again, the next move is not another codec —
it is getting the images off GitHub Pages:

- **Cloudflare Pages** — no 1 GB site cap; its limits are 20,000 files and
  25 MiB per file, and this site is at 6,038 files with a 1.88 MB largest file.
  It would fit today with a wide margin.
- **Cloudflare R2 / a separate assets repo** — decouples image growth from the
  app repo entirely.

Both add an external dependency and a deploy step to a project whose whole
character is "no build, no framework", which is why neither is the move *now*.
Worth writing down so the decision is deliberate when it comes.

---

## Rollback summary

| stage reached | how to undo |
|---|---|
| Phase 1 code changes made | `git revert` that commit — it is self-contained and `covers/` was never touched |
| Phase 3 done (staged only) | `rm -rf build/covers` — `covers/` was never touched |
| Phase 4 promoted, not committed | `python tools/avif_convert.py --revert` then `python convert_csv.py`; the Phase 1 commit stays valid and needs no undo |
| Phase 5 committed, not pushed | `git reset --hard HEAD~1` then revert as above |
| Phase 5 pushed | restore `covers/full` from the Phase 0 tarball, `python convert_csv.py`, commit and push forward (do not force-push). The Phase 1 commit can stay — it works against a JPEG tree too |
| `covers.jpeg.bak/` deleted | Phase 0 tarball / the GitHub Release asset is the only copy — this is why Phase 0 is mandatory |
