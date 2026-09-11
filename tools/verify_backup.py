#!/usr/bin/env python3
"""
tools/verify_backup.py - verify a covers/full tar backup against the live tree.

A member count proves nothing: it does not catch a truncated file, a silently
mangled byte, or a member that was written from the wrong source. This streams
every member out of the archive and hashes it against the file it claims to be
a copy of, without extracting anything to disk.

Usage:
    python tools/verify_backup.py <archive.tar> [--source covers/full]

Exits non-zero if anything is missing, extra, or does not match.
"""

import argparse
import hashlib
import os
import sys
import tarfile


def digest(fh):
    d = hashlib.sha256()
    for chunk in iter(lambda: fh.read(1 << 20), b""):
        d.update(chunk)
    return d.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("--source", default="covers/full")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.archive):
        sys.exit(f"No such archive: {args.archive}")
    if not os.path.isdir(args.source):
        sys.exit(f"No such source directory: {args.source}")

    src = set(os.listdir(args.source))
    seen = set()
    mismatch, unreadable = [], []

    with tarfile.open(args.archive) as t:
        n = 0
        for member in t:
            if not member.isfile():
                continue
            name = os.path.basename(member.name)
            seen.add(name)

            src_path = os.path.join(args.source, name)
            if not os.path.isfile(src_path):
                continue  # reported below as "extra"

            try:
                archived = digest(t.extractfile(member))
                with open(src_path, "rb") as fh:
                    live = digest(fh)
            except Exception as exc:  # noqa: BLE001
                unreadable.append(f"{name}: {type(exc).__name__}: {exc}")
                continue

            if archived != live:
                mismatch.append(name)

            n += 1
            if not args.quiet and n % 1000 == 0:
                print(f"  verified {n} ...")

    missing = sorted(src - seen)
    extra = sorted(seen - src)

    print(f"\narchive        {args.archive}")
    print(f"source         {args.source}")
    print(f"members        {len(seen)}")
    print(f"source files   {len(src)}")
    print(f"missing        {len(missing)}  {missing[:5]}")
    print(f"extra          {len(extra)}  {extra[:5]}")
    print(f"unreadable     {len(unreadable)}  {unreadable[:5]}")
    print(f"hash mismatch  {len(mismatch)}  {mismatch[:5]}")

    if missing or extra or unreadable or mismatch:
        sys.exit("\nBACKUP FAILED VERIFICATION - do not proceed.")
    print("\nBACKUP VERIFIED - every file present and byte-identical.")


if __name__ == "__main__":
    main()
