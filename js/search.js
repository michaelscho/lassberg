// Shared across the three register pages (letters.html, persons.html, places.html):
// the MiniSearch-powered global search box, and the row-expand/collapse pattern used by all
// three DataTables (a dt-control button revealing a pre-rendered <template id="details-{key}">).
// Included before the page-specific script (letters.js / persons.js / places.js).

const KIND_LABELS = {
    letter: 'Letter', person: 'Person', place: 'Place',
    literature: 'Literature', manuscript: 'Manuscript'
};

function initGlobalSearch() {
    let miniSearch = null;
    const searchInput = document.getElementById('global-search');
    const searchResults = document.getElementById('letter-search-results');
    if (!searchInput || !searchResults) return;

    fetch('../json/search_index.json')
        .then(res => res.json())
        .then(records => {
            miniSearch = new MiniSearch({
                fields: ['title', 'text'],
                storeFields: ['kind', 'id', 'title', 'date', 'url', 'external'],
                searchOptions: { prefix: true, fuzzy: 0.15, boost: { title: 2 } }
            });
            miniSearch.addAll(records);
        })
        .catch(err => console.error('Could not load search index:', err));

    function renderSearchResults(results) {
        if (!results.length) {
            searchResults.innerHTML = '<div class="list-group-item text-muted">No matches.</div>';
            searchResults.classList.remove('d-none');
            return;
        }
        const items = results.slice(0, 25).map(r => {
            const label = KIND_LABELS[r.kind] || r.kind;
            const dateStr = r.date ? ` &middot; ${r.date}` : '';
            const extraLink = r.external ? ` <a href="${r.external}" target="_blank" rel="noopener noreferrer" class="ms-1">↗</a>` : '';
            return `<a href="${r.url}" class="list-group-item list-group-item-action">
                <span class="search-kind">${label}</span>${dateStr}<br>${r.title}${extraLink}
            </a>`;
        }).join('');
        searchResults.innerHTML = items;
        searchResults.classList.remove('d-none');
    }

    let searchDebounce;
    searchInput.addEventListener('input', function () {
        clearTimeout(searchDebounce);
        const query = this.value.trim();
        if (!query || !miniSearch) {
            searchResults.classList.add('d-none');
            return;
        }
        searchDebounce = setTimeout(() => {
            renderSearchResults(miniSearch.search(query));
        }, 150);
    });
}

// Reusable dt-control expand/collapse: clicking the row-expand-btn shows/hides a child row
// filled from the matching <template id="details-{key}">, cached after first load.
function initExpandableRows(table, tableSelector) {
    const detailsCache = new Map();

    async function getFormattedDetails(key) {
        if (detailsCache.has(key)) return detailsCache.get(key);
        const tpl = document.getElementById(`details-${key}`);
        const html = tpl ? tpl.innerHTML : '<div class="text-muted p-3">No details available.</div>';
        detailsCache.set(key, html);
        return html;
    }

    $(`${tableSelector} tbody`).on('click', 'td.dt-control', async function (event) {
        event.stopPropagation();
        const tr = $(this).closest('tr');
        const row = table.row(tr);
        const btn = tr.find('td.dt-control .row-expand-btn');

        if (row.child.isShown()) {
            row.child.hide();
            tr.removeClass('dt-hasChild');
            btn.attr('aria-expanded', 'false');
        } else {
            tr.addClass('dt-hasChild');
            btn.attr('aria-expanded', 'true');
            row.child('<div><span class="spinner-border spinner-border-sm"></span> Loading details...</div>').show();

            const key = tr.data('key');
            try {
                const detailsHtml = await getFormattedDetails(key);
                row.child(detailsHtml).show();
            } catch (error) {
                row.child('<div class="text-danger p-3">Could not load details.</div>').show();
                console.error('Error loading details:', error);
            }
        }
    });
}

// Reads ?q=... from the current URL and, if present, pre-fills the given DataTable's global
// search and pre-filters it — used so a search-result link from another register page lands
// pre-filtered here.
function applyDeepLinkSearch(table) {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    if (q) {
        table.search(q).draw();
    }
}

document.addEventListener('DOMContentLoaded', initGlobalSearch);
