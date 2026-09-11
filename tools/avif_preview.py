#!/usr/bin/env python3
"""
tools/avif_preview.py — visual A/B gate for the AVIF migration.

Encodes a hand-picked or auto-picked sample at several qualities and writes
1:1 centre crops plus whole-image views into a self-contained HTML page.
Nothing under covers/ is touched — output goes to build/avif_preview/.

Usage:
    python tools/avif_preview.py                       # 12 hardest-to-encode files
    python tools/avif_preview.py 830-back 754-back 857 # specific stems
    python tools/avif_preview.py --qualities 45 50 55 60
    python tools/avif_preview.py --crop 700

Output: build/avif_preview/index.html  (open it, view at 100% zoom)
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps, features
except ImportError:
    sys.exit("Pillow is required:  pip install 'Pillow>=11.3'")

if not features.check("avif"):
    sys.exit("No AVIF support in this Pillow. Try: pip install -U Pillow")

SOURCE_DIR = Path("covers/full")
OUT_DIR = Path("build/avif_preview")


def auto_pick(n):
    """Highest bytes-per-pixel = most grain/detail = hardest for the encoder."""
    scored = []
    for f in SOURCE_DIR.glob("*.jpg"):
        with Image.open(f) as im:
            w, h = im.size
        if w * h < 500_000:
            continue
        scored.append((f.stat().st_size / (w * h), f))
    scored.sort(reverse=True)
    return [f for _, f in scored[:n]]


def kb(n):
    return f"{n / 1024:,.0f} KB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stems", nargs="*", help="file stems, e.g. 830-back 857")
    ap.add_argument("--qualities", nargs="+", type=int, default=[45, 50, 55, 60])
    ap.add_argument("--speed", type=int, default=6)
    ap.add_argument("--subsampling", default="4:4:4", choices=["4:2:0", "4:4:4"])
    ap.add_argument("--crop", type=int, default=600, help="1:1 centre crop size")
    ap.add_argument("--count", type=int, default=12)
    args = ap.parse_args()

    files = ([SOURCE_DIR / f"{s}.jpg" for s in args.stems] if args.stems
             else auto_pick(args.count))
    missing = [f for f in files if not f.exists()]
    if missing:
        sys.exit("not found: " + ", ".join(str(m) for m in missing))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    totals = {q: 0 for q in args.qualities}
    total_orig = 0

    for src in files:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            w, h = im.size
            c = min(args.crop, w, h)
            box = ((w - c) // 2, (h - c) // 2, (w + c) // 2, (h + c) // 2)

            orig_bytes = src.stat().st_size
            total_orig += orig_bytes

            cells = []
            ref_crop = OUT_DIR / f"{src.stem}__orig.png"
            im.crop(box).save(ref_crop)
            full_ref = OUT_DIR / f"{src.stem}__orig_full.jpg"
            im.copy().save(full_ref, "JPEG", quality=92)
            cells.append(("JPEG (original)", ref_crop.name, full_ref.name,
                          orig_bytes, None))

            for q in args.qualities:
                cand = OUT_DIR / f"{src.stem}__q{q}.avif"
                im.save(cand, "AVIF", quality=q, speed=args.speed,
                        subsampling=args.subsampling)
                totals[q] += cand.stat().st_size
                with Image.open(cand) as dec:
                    dec.load()
                    dec = dec.convert("RGB")
                    crop_png = OUT_DIR / f"{src.stem}__q{q}.png"
                    dec.crop(box).save(crop_png)
                    full_png = OUT_DIR / f"{src.stem}__q{q}_full.jpg"
                    dec.save(full_png, "JPEG", quality=92)
                pct = 100 * cand.stat().st_size / orig_bytes
                cells.append((f"AVIF q{q}", crop_png.name, full_png.name,
                              cand.stat().st_size, pct))
            rows.append((src.name, f"{w}x{h}", cells))

    html = [
        "<!doctype html><meta charset=utf-8><title>AVIF preview</title>",
        "<style>body{background:#14141c;color:#ddd;font:14px system-ui;"
        "margin:0;padding:24px}h1{font-size:18px;color:#c9a227}"
        "h2{font-size:15px;margin:32px 0 8px;color:#c9a227}"
        ".row{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px}"
        "figure{margin:0;flex:0 0 auto}"
        "img{display:block;border:1px solid #333;image-rendering:pixelated}"
        "figcaption{font-size:12px;color:#aaa;padding:4px 0;text-align:center}"
        ".big{max-height:420px;image-rendering:auto}"
        "table{border-collapse:collapse;margin:16px 0}"
        "td,th{border:1px solid #333;padding:4px 10px;text-align:right}"
        "th:first-child,td:first-child{text-align:left}"
        "p.hint{color:#888;max-width:70ch;line-height:1.5}</style>",
        "<h1>AVIF quality gate</h1>",
        f"<p class=hint>Subsampling {args.subsampling}, speed {args.speed}. "
        "Top strip of each product is a 1:1 centre crop (pixelated rendering, "
        "no browser smoothing) &mdash; view this page at 100% zoom. Bottom "
        "strip is the whole cover. Look for smeared film grain, banded skies, "
        "and mushy brushwork, not for PSNR.</p>",
    ]

    html.append("<h2>Totals across this sample</h2><table>"
                "<tr><th>variant</th><th>bytes</th><th>vs JPEG</th></tr>")
    html.append(f"<tr><td>JPEG (original)</td><td>{kb(total_orig)}</td><td>&mdash;</td></tr>")
    for q in args.qualities:
        html.append(f"<tr><td>AVIF q{q}</td><td>{kb(totals[q])}</td>"
                    f"<td>{100 * totals[q] / total_orig:.1f}%</td></tr>")
    html.append("</table>")

    for name, dims, cells in rows:
        html.append(f"<h2>{name} &mdash; {dims}</h2>")
        html.append("<div class=row>")
        for label, crop_img, _full_img, size, pct in cells:
            tail = f" &middot; {pct:.0f}%" if pct is not None else ""
            html.append(f"<figure><img src='{crop_img}'>"
                        f"<figcaption>{label}<br>{kb(size)}{tail}</figcaption></figure>")
        html.append("</div>")
        html.append("<div class=row>")
        for label, _crop_img, full_img, _size, _pct in cells:
            html.append(f"<figure><img class=big src='{full_img}'>"
                        f"<figcaption>{label}</figcaption></figure>")
        html.append("</div>")

    (OUT_DIR / "index.html").write_text("\n".join(html), encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'index.html'}  ({len(rows)} products, "
          f"{len(args.qualities)} qualities)")
    print("Totals across sample:")
    for q in args.qualities:
        print(f"  q{q}: {100 * totals[q] / total_orig:5.1f}% of JPEG")


if __name__ == "__main__":
    main()
