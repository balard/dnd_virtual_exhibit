#!/usr/bin/env python3
"""
tools/avif_convert.py - bulk JPEG -> AVIF conversion for covers/full/.

Converts into a STAGING tree (build/covers/full/) and never overwrites
covers/full/ in place. Promotion is two directory renames, so it is instant
and exactly reversible:

    covers/full        ->  covers.jpeg.bak/full     (the JPEG originals)
    build/covers/full  ->  covers/full              (the AVIF tree)

covers/thumb/ is deliberately NOT touched. At 300px AVIF is barely smaller
than the existing JPEG q75 thumbs (and larger above q55), while costing a
second generation of loss and slower decode in the search grid.

Usage:
    python tools/avif_convert.py --dry-run              # measure a sample, write nothing
    python tools/avif_convert.py --quality 50           # fill the staging tree
    python tools/avif_convert.py --verify               # completeness + decodability
    python tools/avif_convert.py --promote              # swap staging into place
    python tools/avif_convert.py --revert               # swap the JPEGs back

After the one-time migration, new covers arrive from download_covers.py as
JPEG. Fold them in with:

    python tools/avif_convert.py --adopt                # encode + verify + drop the JPEG

--adopt converts each stray .jpg in covers/full/ to .avif in place, checks
that the result decodes at the same dimensions, and only then deletes the
JPEG. It is the steady-state path; the staging/promote flow above is for the
one-time bulk migration.
"""

import argparse
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

try:
    from PIL import Image, ImageOps, features
except ImportError:
    sys.exit("Pillow is required:  pip install 'Pillow>=11.3'")

LIVE = Path("covers/full")
STAGING = Path("build/covers/full")
BACKUP = Path("covers.jpeg.bak/full")

SOURCE_GLOBS = ("*.jpg", "*.jpeg", "*.JPG", "*.JPEG")
JPEG_EXTS = (".jpg", ".jpeg", ".JPG", ".JPEG")


def sources(root=LIVE):
    return sorted({f for g in SOURCE_GLOBS for f in root.glob(g)})


def mb(n):
    return f"{n / 1048576:,.1f} MB"


def encode_one(job):
    """Worker: (src, dst, quality, speed, subsampling) -> (dst, bytes | error string)."""
    src, dst, quality, speed, subsampling = job
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.save(dst, "AVIF", quality=quality, speed=speed,
                    subsampling=subsampling)
        return (str(dst), dst.stat().st_size)
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        return (str(dst), f"{type(exc).__name__}: {exc}")


def cmd_dry_run(args):
    files = sources()
    if not files:
        sys.exit(f"No JPEG sources under {LIVE}/")
    total = sum(f.stat().st_size for f in files)
    random.seed(11)
    samp = random.sample(files, min(args.sample, len(files)))
    samp_orig = sum(f.stat().st_size for f in samp)

    print(f"{len(files)} source files, {mb(total)}")
    print(f"Sampling {len(samp)} of them at q{args.quality}, "
          f"{args.subsampling}, speed {args.speed} ...")

    out = Path(os.environ.get("TEMP", "/tmp")) / "avif_dryrun.avif"
    got = 0
    for f in samp:
        with Image.open(f) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.save(out, "AVIF", quality=args.quality, speed=args.speed,
                    subsampling=args.subsampling)
        got += out.stat().st_size
    out.unlink(missing_ok=True)

    ratio = got / samp_orig
    print(f"\n  ratio        {100 * ratio:.1f}% of JPEG")
    print(f"  covers/full  {mb(total)}  ->  ~{mb(total * ratio)}")
    print(f"  saved        ~{mb(total - total * ratio)}")
    print("\n(Sample estimate. Run without --dry-run for the real figure.)")


def cmd_convert(args):
    files = sources()
    if not files:
        sys.exit(f"No JPEG sources under {LIVE}/")
    STAGING.mkdir(parents=True, exist_ok=True)

    jobs = []
    skipped = 0
    for src in files:
        dst = STAGING / f"{src.stem}.avif"
        if dst.exists() and not args.force:
            skipped += 1
            continue
        jobs.append((src, dst, args.quality, args.speed, args.subsampling))

    print(f"{len(files)} sources, {skipped} already staged, {len(jobs)} to encode")
    if not jobs:
        print("Nothing to do. Run --verify next.")
        return

    errors = []
    done = 0
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for dst, result in pool.map(encode_one, jobs, chunksize=8):
            done += 1
            if isinstance(result, str):
                errors.append((dst, result))
                print(f"  FAIL [{done}/{len(jobs)}] {dst}: {result}")
            elif done % 100 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}] {dst}")

    print(f"\nEncoded {done - len(errors)}, failed {len(errors)}")
    if errors:
        print("Failures:")
        for dst, msg in errors:
            print(f"  {dst}: {msg}")
        sys.exit(1)
    print("Now run:  python tools/avif_convert.py --verify")


def cmd_verify(args):
    files = sources()
    if not files:
        sys.exit(f"No JPEG sources under {LIVE}/ - already promoted?")
    if not STAGING.exists():
        sys.exit(f"No staging tree at {STAGING}/ - run the conversion first.")

    missing, broken, mismatched = [], [], []
    orig_total = staged_total = 0

    for i, src in enumerate(files, 1):
        dst = STAGING / f"{src.stem}.avif"
        orig_total += src.stat().st_size
        if not dst.exists():
            missing.append(src.name)
            continue
        staged_total += dst.stat().st_size
        try:
            with Image.open(src) as a:
                sw, sh = ImageOps.exif_transpose(a).size
            with Image.open(dst) as b:
                b.load()
                dw, dh = b.size
            if (sw, sh) != (dw, dh):
                mismatched.append(f"{src.name} {sw}x{sh} -> {dw}x{dh}")
        except Exception as exc:  # noqa: BLE001
            broken.append(f"{dst.name}: {type(exc).__name__}: {exc}")
        if i % 500 == 0:
            print(f"  checked {i}/{len(files)} ...")

    staged_files = list(STAGING.glob("*.avif"))
    extra = [f.name for f in staged_files
             if not any((LIVE / (f.stem + e)).exists() for e in JPEG_EXTS)]

    print(f"\nsources        {len(files)}")
    print(f"staged         {len(staged_files)}")
    print(f"missing        {len(missing)}")
    print(f"undecodable    {len(broken)}")
    print(f"dim mismatch   {len(mismatched)}")
    print(f"orphan staged  {len(extra)}")
    for label, items in (("MISSING", missing), ("UNDECODABLE", broken),
                         ("DIM MISMATCH", mismatched), ("ORPHAN", extra)):
        for x in items[:20]:
            print(f"  {label}: {x}")
        if len(items) > 20:
            print(f"  {label}: ... and {len(items) - 20} more")

    if staged_total:
        print(f"\ncovers/full    {mb(orig_total)}  ->  {mb(staged_total)}"
              f"  ({100 * staged_total / orig_total:.1f}%)")

    if missing or broken or mismatched:
        sys.exit("VERIFY FAILED - do not promote.")
    print("\nVERIFY OK. Safe to promote.")


def cmd_adopt(args):
    """Steady state: convert stray JPEGs in covers/full/ to AVIF, then drop them."""
    files = sources()
    if not files:
        print(f"No stray JPEGs under {LIVE}/ - nothing to adopt.")
        return

    print(f"{len(files)} JPEG(s) to adopt at q{args.quality}, "
          f"{args.subsampling}, speed {args.speed}")

    converted, failed, kept = 0, [], []
    for i, src in enumerate(files, 1):
        dst = LIVE / f"{src.stem}.avif"
        if dst.exists() and not args.force:
            kept.append(f"{dst.name} already exists - left {src.name} alone")
            continue

        _, result = encode_one((src, dst, args.quality, args.speed, args.subsampling))
        if isinstance(result, str):
            failed.append(f"{src.name}: {result}")
            print(f"  FAIL [{i}/{len(files)}] {src.name}: {result}")
            continue

        try:
            with Image.open(src) as a:
                sw, sh = ImageOps.exif_transpose(a).size
            with Image.open(dst) as b:
                b.load()
                dw, dh = b.size
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{dst.name}: unreadable after encode: {exc}")
            dst.unlink(missing_ok=True)
            continue

        if (sw, sh) != (dw, dh):
            failed.append(f"{src.name}: {sw}x{sh} -> {dw}x{dh}")
            dst.unlink(missing_ok=True)
            continue

        src.unlink()
        converted += 1
        print(f"  [{i}/{len(files)}] {src.name} -> {dst.name}")

    print(f"\nAdopted {converted}, skipped {len(kept)}, failed {len(failed)}")
    for msg in kept + failed:
        print(f"  {msg}")
    if failed:
        sys.exit(1)
    print("\nNext:\n  python generate_thumbs.py\n  python convert_csv.py")


def cmd_promote(args):
    if not STAGING.exists():
        sys.exit(f"No staging tree at {STAGING}/")
    if BACKUP.exists():
        sys.exit(f"{BACKUP}/ already exists - a promotion is already in effect. "
                 "Run --revert first, or delete it once you are happy.")
    if not LIVE.exists():
        sys.exit(f"{LIVE}/ does not exist.")

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    LIVE.rename(BACKUP)
    STAGING.rename(LIVE)
    print(f"Promoted.\n  JPEG originals -> {BACKUP}/\n  AVIF tree      -> {LIVE}/")
    print("\nNext:\n  python convert_csv.py       # rewrite cover_url to .avif\n"
          "  python -m http.server 8000  # then click through the site")
    print("\nTo undo:  python tools/avif_convert.py --revert")


def cmd_revert(args):
    if not BACKUP.exists():
        sys.exit(f"Nothing to revert - {BACKUP}/ does not exist.")
    if STAGING.exists():
        sys.exit(f"{STAGING}/ already exists - move it aside first.")

    STAGING.parent.mkdir(parents=True, exist_ok=True)
    LIVE.rename(STAGING)
    BACKUP.rename(LIVE)
    try:
        BACKUP.parent.rmdir()
    except OSError:
        pass
    print(f"Reverted.\n  AVIF tree      -> {STAGING}/\n  JPEG originals -> {LIVE}/")
    print("\nNext:  python convert_csv.py   # rewrite cover_url back to .jpg")


def main():
    ap = argparse.ArgumentParser(
        description="Bulk JPEG -> AVIF conversion for covers/full/.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="measure a sample, write nothing")
    mode.add_argument("--verify", action="store_true", help="check the staging tree")
    mode.add_argument("--promote", action="store_true", help="swap staging into covers/full")
    mode.add_argument("--revert", action="store_true", help="swap the JPEGs back")
    mode.add_argument("--adopt", action="store_true",
                      help="steady state: convert stray JPEGs in covers/full/ in place")
    ap.add_argument("--quality", type=int, default=50)
    ap.add_argument("--speed", type=int, default=6, help="0 slowest/smallest .. 10 fastest")
    ap.add_argument("--subsampling", default="4:4:4", choices=["4:2:0", "4:4:4"])
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--sample", type=int, default=150, help="--dry-run sample size")
    ap.add_argument("--force", action="store_true", help="re-encode already-staged files")
    args = ap.parse_args()

    if not features.check("avif"):
        sys.exit("No AVIF support in this Pillow. Try: pip install -U 'Pillow>=11.3'")

    if args.dry_run:
        cmd_dry_run(args)
    elif args.verify:
        cmd_verify(args)
    elif args.promote:
        cmd_promote(args)
    elif args.revert:
        cmd_revert(args)
    elif args.adopt:
        cmd_adopt(args)
    else:
        cmd_convert(args)


if __name__ == "__main__":
    main()
