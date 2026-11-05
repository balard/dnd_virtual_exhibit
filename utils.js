/**
 * utils.js — Shared utilities for DnD Virtual Exhibit
 * Provides filter helpers and shared constants used across index.html,
 * search.html, and spread.html.
 */

const FILTERS_KEY = 'tsr_active_filters';
const FILTERS_SEEDED_KEY = 'tsr_filters_seeded';

// One-time default: exclude magazines on a user's first ever visit.
// Runs when this script loads — before any page reads the filter. After the
// seed, the user has full control and Clear Filters truly clears (the marker
// prevents re-seeding, so clearing won't silently re-add the default).
(function seedDefaultFilters() {
    try {
        if (localStorage.getItem(FILTERS_SEEDED_KEY)) return;     // already seeded once
        localStorage.setItem(FILTERS_SEEDED_KEY, '1');
        if (localStorage.getItem(FILTERS_KEY) != null) return;    // user already has filters
        localStorage.setItem(FILTERS_KEY, JSON.stringify({
            type: [], system: [], setting: [], publisher: [], text: '',
            exclude_type: ['magazine'],
            exclude_system: [], exclude_setting: [], exclude_publisher: [],
        }));
    } catch (e) { /* storage unavailable — ignore */ }
})();

// ── Shareable filter links ───────────────────────────────────────────────────
// A shared link carries the full filter in the query string, e.g.
//   search.html?v=1&type=adventure&xtype=magazine&system=AD%26D+1e&q=dragon&title=1
// Include values use the category name, excludes an `x` prefix; multi-select
// values repeat the key. `v` is mandatory: it marks the URL as a shared filter
// (so `?v=1` alone means "no filter — show everything", distinct from a bare
// URL, which keeps the visitor's own filter) and versions the format.
// These names are a public contract once links are out — do not rename them.
const SHARE_VERSION = '1';
const SHARE_CATEGORIES = ['type', 'system', 'setting', 'publisher'];
const SHARE_PARAMS = ['v', 'q', 'title',
    ...SHARE_CATEGORIES, ...SHARE_CATEGORIES.map(c => 'x' + c)];

/** Build an absolute shareable URL for `page` encoding the filter object. */
function buildShareUrl(filters, page = 'search.html') {
    const url = new URL(page, window.location.href);
    url.search = '';
    url.hash = '';
    const sp = url.searchParams;
    sp.set('v', SHARE_VERSION);
    const f = filters || {};
    for (const c of SHARE_CATEGORIES) {
        for (const val of (f[c] || []))              sp.append(c, val);
        for (const val of (f['exclude_' + c] || [])) sp.append('x' + c, val);
    }
    if (f.text) sp.set('q', f.text);
    if (f.text_title_only) sp.set('title', '1');
    return url.toString();
}

// Import a shared filter from the query string. Runs after the seed above and
// before any page reads the filter, so every page that loads utils.js accepts
// a shared link. It silently replaces the visitor's saved filter, then strips
// its params from the address bar — otherwise every reload would re-import the
// link and discard changes made since. Values are not validated here
// (products.json isn't loaded yet); search.html drops values it has no pill for.
// hotsite.html is skipped: it is isolated from the filter state by design.
(function importSharedFilters() {
    try {
        if (/(^|\/)hotsite\.html$/.test(window.location.pathname)) return;
        const url = new URL(window.location.href);
        const sp = url.searchParams;
        if (sp.get('v') !== SHARE_VERSION) return;   // absent or unknown version
        const filters = { text: (sp.get('q') || '').trim(), text_title_only: sp.get('title') === '1' };
        for (const c of SHARE_CATEGORIES) {
            filters[c] = sp.getAll(c);
            filters['exclude_' + c] = sp.getAll('x' + c);
        }
        localStorage.setItem(FILTERS_KEY, JSON.stringify(filters));
        localStorage.setItem(FILTERS_SEEDED_KEY, '1');
        for (const k of SHARE_PARAMS) sp.delete(k);
        history.replaceState(history.state, '', url.pathname + url.search + url.hash);
    } catch (e) { /* storage or history unavailable — ignore */ }
})();

const MONTH_NAMES = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December'];

const TEXT_FIELDS = ['title','dtrpg_title','module_code','product_code',
                     'authors','cover_artist','blurb'];

/**
 * Derive a product's thumbnail URL from its cover_url.
 *
 * The two trees deliberately use different formats: covers/full/ is AVIF
 * (roughly half the bytes of JPEG at the same resolution) while covers/thumb/
 * stays JPEG, because at 300px AVIF saves almost nothing and decodes slower in
 * a grid rendering hundreds of images at once. So the extension has to be
 * rewritten, not just the directory.
 *
 * Returns null for a product with no cover, and passes through any remote
 * fallback URL unchanged — those have no locally generated thumbnail.
 */
function thumbUrl(coverUrl) {
    if (!coverUrl) return null;
    if (!coverUrl.startsWith('covers/full/')) return coverUrl;
    return coverUrl.replace('/full/', '/thumb/').replace(/\.[^.\/]+$/, '.jpg');
}

/**
 * Read the saved filter state from localStorage.
 * Returns parsed object, or null if nothing is saved / parse fails.
 */
function loadActiveFilters() {
    try {
        const raw = localStorage.getItem(FILTERS_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch(e) { return null; }
}

/**
 * True if the filter object has any active criterion (any of the 9 keys).
 * Drives filter-indicator visibility independently of whether the filter
 * actually reduces the product count (a filter can be active yet non-reducing,
 * e.g. excluding a value no product has).
 */
function filtersActive(filters) {
    if (!filters) return false;
    const len = k => Array.isArray(filters[k]) ? filters[k].length : 0;
    return !!(len('type') || len('system') || len('setting') || len('publisher')
           || len('exclude_type') || len('exclude_system')
           || len('exclude_setting') || len('exclude_publisher')
           || (filters.text && filters.text.length));
}

/**
 * Filter a products array using the persisted filter object (arrays, not Sets).
 * @param {Array}  all     - Full products array
 * @param {Object} filters - Saved filter state from localStorage (or null for no filter)
 * @returns {Array} Filtered products
 */
function applyFiltersToProducts(all, filters) {
    if (!filters) return all;
    const { type, system, setting, publisher, text, text_title_only,
            exclude_type, exclude_system, exclude_setting, exclude_publisher } = filters;
    const q = (text || '').toLowerCase();
    const textFields = text_title_only ? ['title'] : TEXT_FIELDS;
    return all.filter(p => {
        if (type      && type.length      && !type.includes(p.type))                       return false;
        if (system    && system.length    && !system.includes(p.system))                   return false;
        if (setting   && setting.length   && !setting.includes(p.setting ?? '__none__'))   return false;
        if (publisher && publisher.length && !publisher.includes(p.publisher))             return false;
        if (exclude_type      && exclude_type.includes(p.type))                            return false;
        if (exclude_system    && exclude_system.includes(p.system))                        return false;
        if (exclude_setting   && exclude_setting.includes(p.setting ?? '__none__'))        return false;
        if (exclude_publisher && exclude_publisher.includes(p.publisher))                  return false;
        if (q) {
            const matches = textFields.some(f => p[f] && p[f].toLowerCase().includes(q));
            if (!matches) return false;
        }
        return true;
    });
}
