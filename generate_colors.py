#!/usr/bin/env python3
"""
generate_colors.py — Distill a representative color from each front cover.

Reads the 300px thumbnails in covers/thumb/ (front covers only, ignoring
'*-back.jpg') and writes covers/cover_colors.json, a map keyed by product id:

    { "1": {"avg": "#rrggbb", "dom": "#rrggbb"}, ... }

  avg — the cover's overall average color (1x1 box downsample).
  dom — the cover's dominant color: the most frequent swatch after quantizing,
        skipping near-black / near-white / near-grey entries so the result is
        characterful rather than a muddy background tone. Falls back to avg.

stats.html consumes this file and aggregates per setting / per artist.

Usage:
    python generate_colors.py              # process all front covers
    python generate_colors.py 100 200      # only ids 100-200 (inclusive)
    python generate_colors.py --force      # recompute even if already present
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow is required. Install it with:  pip install Pillow")
    sys.exit(1)

SOURCE_DIR = Path("covers/thumb")
OUTPUT_FILE = Path("covers/cover_colors.json")

# Dominant-color extraction tuning.
QUANTIZE_COLORS = 8   # palette size to reduce each cover to
NEAR_BLACK = 28       # discard swatches whose max channel is below this
NEAR_WHITE = 228      # discard swatches whose min channel is above this
MIN_CHROMA = 18       # discard near-grey swatches (max-min channel spread)


def extract_id(filename: str) -> int | None:
    """Return the numeric id for a *front* cover ('123.jpg'), else None.

    Back covers ('123-back.jpg') are intentionally skipped.
    """
    m = re.match(r"^(\d+)\.jpe?g$", filename.lower())
    return int(m.group(1)) if m else None


def to_hex(rgb) -> str:
    r, g, b = (int(round(c)) for c in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def average_color(img: "Image.Image") -> tuple:
    """Overall average color via a 1x1 box downsample."""
    return img.resize((1, 1), Image.BOX).getpixel((0, 0))


def dominant_color(img: "Image.Image", fallback: tuple) -> tuple:
    """Most frequent quantized swatch, skipping black/white/grey; else fallback."""
    pal_img = img.quantize(colors=QUANTIZE_COLORS)
    palette = pal_img.getpalette()  # flat [r,g,b, r,g,b, ...]
    counts = pal_img.getcolors()    # list of (count, palette_index)
    if not counts:
        return fallback

    # Most frequent first.
    for _, idx in sorted(counts, key=lambda c: c[0], reverse=True):
        r, g, b = palette[idx * 3: idx * 3 + 3]
        hi, lo = max(r, g, b), min(r, g, b)
        if hi < NEAR_BLACK or lo > NEAR_WHITE or (hi - lo) < MIN_CHROMA:
            continue
        return (r, g, b)

    return fallback


def main():
    parser = argparse.ArgumentParser(description="Distill a color from each front cover.")
    parser.add_argument("start_id", nargs="?", type=int, help="Start of id range (inclusive)")
    parser.add_argument("end_id", nargs="?", type=int, help="End of id range (inclusive)")
    parser.add_argument("--force", action="store_true", help="Recompute ids already present")
    args = parser.parse_args()

    if (args.start_id is None) != (args.end_id is None):
        parser.error("Provide both start_id and end_id, or neither.")

    id_range = (args.start_id, args.end_id) if args.start_id is not None else None

    if not SOURCE_DIR.exists():
        print(f"Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    # Load any existing results so runs are idempotent and mergeable.
    colors = {}
    if OUTPUT_FILE.exists():
        try:
            colors = json.loads(OUTPUT_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            print(f"Warning: could not read {OUTPUT_FILE}; starting fresh.")
            colors = {}

    all_files = sorted(f for ext in ("*.jpg", "*.jpeg") for f in SOURCE_DIR.glob(ext))

    files = []
    for f in all_files:
        pid = extract_id(f.name)
        if pid is None:
            continue  # skips back covers and any odd names
        if id_range and not (id_range[0] <= pid <= id_range[1]):
            continue
        files.append((pid, f))

    if id_range:
        print(f"Processing ids {id_range[0]}–{id_range[1]}: {len(files)} front covers found")
    else:
        print(f"Processing all front covers: {len(files)} found")

    computed = 0
    skipped = 0
    total = len(files)

    for i, (pid, src_path) in enumerate(files, 1):
        if not args.force and str(pid) in colors:
            skipped += 1
            continue

        try:
            with Image.open(src_path) as img:
                img = img.convert("RGB")
                avg = average_color(img)
                dom = dominant_color(img, avg)
        except OSError as e:
            print(f"  skip [{i}/{total}] {src_path.name} (unreadable: {e})")
            skipped += 1
            continue

        colors[str(pid)] = {"avg": to_hex(avg), "dom": to_hex(dom)}
        print(f"  [{i}/{total}] {src_path.name} -> avg {to_hex(avg)}  dom {to_hex(dom)}")
        computed += 1

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ordered = {k: colors[k] for k in sorted(colors, key=int)}
    OUTPUT_FILE.write_text(json.dumps(ordered, separators=(",", ":")) + "\n")

    print(f"\nDone: {computed} computed, {skipped} skipped. "
          f"{len(ordered)} total in {OUTPUT_FILE}.")


if __name__ == "__main__":
    main()
