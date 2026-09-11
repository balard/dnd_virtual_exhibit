"""
redownload_cover.py — Force re-download of cover images for one or more product IDs.

Use this after correcting a product's cover_url in the CSV. It reads the remote
URL directly from the CSV (bypassing products.json), deletes any existing cover
files for each ID, downloads fresh front and back covers, then regenerates
products.json automatically.

Usage:
    python redownload_cover.py <id> [id2 id3 ...]

Examples:
    python redownload_cover.py 554
    python redownload_cover.py 554 420 516
"""

import csv as csv_module
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

# Cover URLs live in covers.csv, NOT in tsr_products.csv -- that file has no
# cover_url column at all. Reading the master table here meant load_remote_urls()
# always came back empty and every id reported "not found in CSV".
COVERS_CSV = '../tsr_products/covers.csv'
OUTPUT_DIR = Path('covers/full')
DELAY_SECONDS = 0.5


def get_extension(url):
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    return ext.lower() if ext else '.jpg'


def download_image(url, dest_path):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = response.read()
    with open(dest_path, 'wb') as f:
        f.write(data)


def load_remote_urls():
    """Return {id: (cover_url, backcover_url)} from covers.csv.

    Both URLs are read straight from the file. The back cover is NOT derived
    from the front one: covers.csv carries an explicit backcover_url column,
    and derivation guesses wrong whenever the two differ.
    """
    mapping = {}
    try:
        with open(COVERS_CSV, newline='', encoding='utf-8') as f:
            reader = csv_module.DictReader(f)
            for row in reader:
                rid = row.get('id', '').strip()
                url = row.get('cover_url', '').strip()
                back = row.get('backcover_url', '').strip()
                if rid and url:
                    mapping[int(rid)] = (url, back)
    except OSError as e:
        print(f'Error: could not load CSV: {e}')
        sys.exit(1)
    return mapping


def delete_existing(pid, front=True, back=True):
    """Delete cover files (any extension) for the given product id.

    `front` / `back` select which side to clear. A redownload that is only
    replacing the front must not take an existing back cover with it -- the
    back may have been fetched from a URL that is no longer in covers.csv.
    """
    patterns = []
    if front:
        patterns.append(f'{pid}.*')
    if back:
        patterns.append(f'{pid}-back.*')
    deleted = []
    for pattern in patterns:
        for f in OUTPUT_DIR.glob(pattern):
            f.unlink()
            deleted.append(f.name)
    for name in deleted:
        print(f'  Deleted {OUTPUT_DIR}/{name}')
    if not deleted:
        print(f'  No existing files for id={pid}')


def main():
    if len(sys.argv) < 2 or not all(a.isdigit() for a in sys.argv[1:]):
        print('Usage: python redownload_cover.py <id> [id2 id3 ...]')
        print('Example: python redownload_cover.py 554')
        sys.exit(1)

    ids = [int(a) for a in sys.argv[1:]]
    remote_urls = load_remote_urls()

    ok = 0
    failed = 0

    for pid in ids:
        print(f'\n--- id={pid} ---')
        entry = remote_urls.get(pid)
        if not entry:
            print(f'  ERROR: id={pid} has no cover_url in {COVERS_CSV}')
            print(f'         (if that blank is deliberate, the local file in '
                  f'{OUTPUT_DIR}/ is the cover -- nothing to redownload)')
            failed += 1
            continue
        url, b_url = entry
        if not url.startswith('http'):
            print(f'  ERROR: cover_url for id={pid} is not a remote URL: {url}')
            failed += 1
            continue

        # Download to scratch files FIRST and only swap them in once the front
        # cover is safely on disk. Deleting up front meant a network blip or a
        # dead link left the product with no cover at all -- and since the
        # migration, covers/full/ is the only copy of the image in the repo.
        dest = OUTPUT_DIR / f'{pid}{get_extension(url)}'
        tmp_front = OUTPUT_DIR / f'.{pid}.download{get_extension(url)}'
        tmp_back = None

        try:
            print(f'  Downloading front -> {dest}', end='', flush=True)
            download_image(url, tmp_front)
            print(' OK')
            time.sleep(DELAY_SECONDS)
        except (urllib.error.URLError, OSError) as e:
            print(f' FAILED: {e}')
            print(f'  Existing files for id={pid} left untouched.')
            tmp_front.unlink(missing_ok=True)
            failed += 1
            continue

        back_dest = None
        if b_url and b_url.startswith('http'):
            back_dest = OUTPUT_DIR / f'{pid}-back{get_extension(b_url)}'
            tmp_back = OUTPUT_DIR / f'.{pid}-back.download{get_extension(b_url)}'
            try:
                print(f'  Downloading back  -> {back_dest}', end='', flush=True)
                download_image(b_url, tmp_back)
                print(' OK')
                time.sleep(DELAY_SECONDS)
            except urllib.error.HTTPError as e:
                tmp_back.unlink(missing_ok=True)
                tmp_back = None
                print(' 404 (no back cover)' if e.code == 404 else f' FAILED: {e}')
                if e.code != 404:
                    failed += 1
            except (urllib.error.URLError, OSError) as e:
                tmp_back.unlink(missing_ok=True)
                tmp_back = None
                print(f' FAILED: {e}')
                failed += 1
        else:
            print(f'  No backcover_url for id={pid}; leaving back cover alone')

        # Front is in hand: now it is safe to clear the old files and swap.
        delete_existing(pid, front=True, back=tmp_back is not None)
        tmp_front.replace(dest)
        ok += 1
        if tmp_back is not None:
            tmp_back.replace(back_dest)
            ok += 1

    sys.stdout.flush()
    print(f'\nDownloads: {ok} OK, {failed} failed')

    # Covers arrive from the archives as JPEG, but covers/full/ is AVIF. The
    # conversion has to happen before the thumbnails and the JSON are built
    # from the tree, otherwise the fresh cover sits there as a stray .jpg and
    # cover_url points at a file that is about to be replaced.
    for label, args in (
        ('Converting new cover(s) to AVIF', ['tools/avif_convert.py', '--adopt']),
        ('Regenerating thumbnails',         ['generate_thumbs.py']),
        ('Regenerating products.json',      ['convert_csv.py']),
    ):
        print(f'\n{label}...')
        result = subprocess.run([sys.executable, *args], capture_output=False)
        if result.returncode != 0:
            print(f'WARNING: {args[0]} exited with an error; stopping here.')
            break


if __name__ == '__main__':
    main()
