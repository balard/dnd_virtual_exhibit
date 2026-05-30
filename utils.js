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

const MONTH_NAMES = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December'];

const TEXT_FIELDS = ['title','dtrpg_title','module_code','product_code',
                     'authors','cover_artist','blurb'];

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
 * Filter a products array using the persisted filter object (arrays, not Sets).
 * @param {Array}  all     - Full products array
 * @param {Object} filters - Saved filter state from localStorage (or null for no filter)
 * @returns {Array} Filtered products
 */
function applyFiltersToProducts(all, filters) {
    if (!filters) return all;
    const { type, system, setting, publisher, text,
            exclude_type, exclude_system, exclude_setting, exclude_publisher } = filters;
    const q = (text || '').toLowerCase();
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
            const matches = TEXT_FIELDS.some(f => p[f] && p[f].toLowerCase().includes(q));
            if (!matches) return false;
        }
        return true;
    });
}
