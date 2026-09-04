import csv
import json
import sys
from pathlib import Path

MAIN_CSV         = '../tsr_products/tsr_products.csv'
COVERS_CSV       = '../tsr_products/covers.csv'
BLURBS_CSV       = '../tsr_products/blurbs.csv'
DTRPG_CSV        = '../tsr_products/dtrpg.csv'
OUTPUT_FILE      = 'products.json'
MAX_YEAR         = 2013  # Only export products up to and including this year
LOCAL_COVERS_DIR = Path('covers/full')


def str_or_none(val):
    v = val.strip()
    return v if v else None


def int_or_none(val):
    v = val.strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def open_csv(path):
    try:
        return open(path, newline='', encoding='utf-8')
    except FileNotFoundError:
        print(f'ERROR: {path} not found')
        sys.exit(1)


def load_covers():
    mapping = {}
    with open_csv(COVERS_CSV) as f:
        for row in csv.DictReader(f):
            rid = row.get('id', '').strip()
            if not rid or rid == 'id':
                continue
            mapping[int(rid)] = {
                'cover_url':     row.get('cover_url', '').strip(),
                'backcover_url': str_or_none(row.get('backcover_url', '')),
            }
    return mapping


def load_blurbs():
    mapping = {}
    with open_csv(BLURBS_CSV) as f:
        for row in csv.DictReader(f):
            rid = row.get('id', '').strip()
            if not rid or rid == 'id':
                continue
            # Source CSV may carry CRLF (or lone CR) inside quoted blurb fields;
            # normalize to \n so regenerating doesn't churn every blurb in the diff.
            blurb = row.get('blurb', '').replace('\r\n', '\n').replace('\r', '\n')
            mapping[int(rid)] = str_or_none(blurb)
    return mapping


def load_dtrpg():
    mapping = {}
    with open_csv(DTRPG_CSV) as f:
        for row in csv.DictReader(f):
            rid = row.get('id', '').strip()
            if not rid or rid == 'id':
                continue
            mapping[int(rid)] = {
                'dtrpg_url':   str_or_none(row.get('dtrpg_url', '')),
                'dtrpg_title': str_or_none(row.get('dtrpg_title', '')),
            }
    return mapping


covers = load_covers()
blurbs = load_blurbs()
dtrpg  = load_dtrpg()

products = []
warnings = []
with open_csv(MAIN_CSV) as f:
    for row in csv.DictReader(f):
        row_id = row.get('id', '').strip()
        if not row_id or row_id == 'id':
            continue
        pid = int(row_id)

        cover_data = covers.get(pid, {})
        cover_url  = cover_data.get('cover_url', '')

        year_raw = row.get('year', '').strip()
        year = int_or_none(year_raw)
        if year is None or year > MAX_YEAR:
            continue

        local_path = None
        for f_path in LOCAL_COVERS_DIR.glob(f'{pid}.*'):
            local_path = f'covers/full/{f_path.name}'
            break

        if not cover_url and not local_path:
            continue  # skip products with no cover

        local_back_path = None
        for f_path in LOCAL_COVERS_DIR.glob(f'{pid}-back.*'):
            local_back_path = f'covers/full/{f_path.name}'
            break

        artist = row.get('cover_artist', '').strip()
        if not artist:
            artist = None
        elif artist.upper() == 'N/A':
            artist = 'N/A'
        elif artist.upper().startswith('LIKELY:'):
            artist = artist[len('LIKELY:'):].strip()

        month = int_or_none(row.get('month', ''))
        if month is not None and (month < 1 or month > 12):
            warnings.append(f'id={pid}: invalid month={month}')
            month = None

        title = row.get('title', '').strip()
        if not title:
            warnings.append(f'id={pid}: missing title, skipping')
            continue

        dtrpg_data = dtrpg.get(pid)

        products.append({
            'id':            pid,
            'order':         int_or_none(row.get('order', '')),
            'year':          year,
            'month':         month,
            'day':           int_or_none(row.get('day', '')),
            'product_code':  str_or_none(row.get('product code', '')),
            'title':         title,
            'module_code':   str_or_none(row.get('module code', '')),
            'type':          str_or_none(row.get('type', '')),
            'system':        str_or_none(row.get('system', '')),
            'setting':       str_or_none(row.get('setting', '')),
            'publisher':     str_or_none(row.get('publisher', '')),
            'confidence':    str_or_none(row.get('confidence', '')),
            'edition':       str_or_none(row.get('edition', '')),
            'authors':       row.get('authors', '').strip() or None,
            'pages':         int_or_none(row.get('pages', '')),
            'isbn':          str_or_none(row.get('isbn', '')),
            'cover_url':     local_path if local_path else cover_url,
            'cover_artist':  artist,
            'semester':      int_or_none(row.get('semester', '')),
            'backcover_url': local_back_path if local_back_path else cover_data.get('backcover_url'),
            'blurb':         blurbs.get(pid),
            'dtrpg_url':     dtrpg_data['dtrpg_url']   if dtrpg_data else None,
            'dtrpg_title':   dtrpg_data['dtrpg_title'] if dtrpg_data else None,
        })

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

print(f'Exported {len(products)} products to {OUTPUT_FILE}')

if warnings:
    print(f'\nVALIDATION WARNINGS ({len(warnings)}):')
    for w in warnings:
        print(f'  {w}')

hotlink_front = [(p['id'], p['title'], p['cover_url'])     for p in products if p['cover_url'].startswith('http')]
hotlink_back  = [(p['id'], p['title'], p['backcover_url']) for p in products if p.get('backcover_url') and p['backcover_url'].startswith('http')]

if hotlink_front:
    print(f'\nWARNING: {len(hotlink_front)} product(s) using remote front cover URL (no local file):')
    for pid, ptitle, url in hotlink_front:
        print(f'  id={pid:>4}  {ptitle[:50]:<50}  {url}')

if hotlink_back:
    print(f'\nWARNING: {len(hotlink_back)} product(s) using remote back cover URL (no local file):')
    for pid, ptitle, url in hotlink_back:
        print(f'  id={pid:>4}  {ptitle[:50]:<50}  {url}')
