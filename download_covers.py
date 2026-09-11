"""
download_covers.py — Download cover images for products of a given year.

Usage:
    python download_covers.py <year>

Example:
    python download_covers.py 1980

Images are saved to covers/full/{id}.{ext} (front) and covers/full/{id}-back.{ext}
(back), where the extension is preserved from the original cover_url.
Already-downloaded files are skipped. Back cover URLs are read directly from
covers.csv (backcover_url column).
Requires products.json to be up-to-date (run convert_csv.py first).
"""

import csv as csv_module
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

PRODUCTS_FILE = 'products.json'
COVERS_CSV = '../tsr_products/covers.csv'
OUTPUT_DIR = Path('covers/full')
DELAY_SECONDS = 0.5  # polite delay between requests


def get_extension(url):
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    return ext.lower() if ext else '.jpg'


def local_cover_exists(pid, back=False):
    """True if a local cover file exists for this id, whatever its extension.

    The extension is not fixed. covers/full/ holds AVIF after the migration
    while downloads still arrive as JPEG from the archives, so testing for one
    specific suffix would report "missing" for every already-converted cover
    and re-download the lot.
    """
    stem = f'{pid}-back' if back else str(pid)
    return any(OUTPUT_DIR.glob(f'{stem}.*'))



def download_image(url, dest_path):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = response.read()
    with open(dest_path, 'wb') as f:
        f.write(data)


def load_back_urls():
    """Return {id: backcover_url} from covers.csv."""
    mapping = {}
    try:
        with open(COVERS_CSV, newline='', encoding='utf-8') as f:
            for row in csv_module.DictReader(f):
                rid = row.get('id', '').strip()
                if not rid or rid == 'id':
                    continue
                url = row.get('backcover_url', '').strip()
                if url:
                    mapping[int(rid)] = url
    except OSError as e:
        print(f'Warning: could not load covers.csv for back-cover URLs: {e}')
    return mapping


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print('Usage: python download_covers.py <year>')
        print('Example: python download_covers.py 1980')
        sys.exit(1)

    year = int(sys.argv[1])

    with open(PRODUCTS_FILE, encoding='utf-8') as f:
        products = json.load(f)

    back_urls = load_back_urls()

    targets = [p for p in products if p.get('year') == year and p.get('cover_url') and p.get('id') is not None]

    if not targets:
        print(f'No products with images found for year {year}.')
        sys.exit(0)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Downloading {len(targets)} cover(s) for year {year} -> {OUTPUT_DIR}/')

    ok = 0
    skipped = 0
    failed = 0

    for i, product in enumerate(targets, 1):
        pid = product['id']
        url = product['cover_url']
        dest = OUTPUT_DIR / f'{pid}{get_extension(url)}'

        prefix = f'[{i}/{len(targets)}]'

        # --- front cover ---
        if local_cover_exists(pid) or not url.startswith('http'):
            print(f'{prefix} Skip id={pid} front (already exists)')
            skipped += 1
        else:
            try:
                print(f'{prefix} Downloading id={pid} front -> {dest}', end='', flush=True)
                download_image(url, dest)
                print(' OK')
                ok += 1
                time.sleep(DELAY_SECONDS)
            except (urllib.error.URLError, OSError) as e:
                print(f' FAILED: {e}')
                failed += 1

        # --- back cover ---
        b_url = back_urls.get(pid)
        if b_url and b_url.startswith('http'):
            back_dest = OUTPUT_DIR / f'{pid}-back{get_extension(b_url)}'
            if local_cover_exists(pid, back=True):
                print(f'{prefix} Skip id={pid} back (already exists)')
                skipped += 1
            else:
                try:
                    print(f'{prefix} Downloading id={pid} back -> {back_dest}', end='', flush=True)
                    download_image(b_url, back_dest)
                    print(' OK')
                    ok += 1
                    time.sleep(DELAY_SECONDS)
                except (urllib.error.URLError, OSError) as e:
                    print(f' FAILED (back): {e}')
                    failed += 1
        else:
            print(f'{prefix} Skip id={pid} back (no back-cover URL)')
            skipped += 1

    print(f'\nDone: {ok} downloaded, {skipped} skipped, {failed} failed.')


if __name__ == '__main__':
    main()
