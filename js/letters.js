document.addEventListener('DOMContentLoaded', function () {

    const table = $('#letter-table').DataTable({
        paging: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
        info: true,
        responsive: true,
        order: [[2, 'asc']], // Default sort by Date (column index 2)
        columnDefs: [
            {
                orderable: false,
                className: 'dt-control',
                targets: 0
            }
        ],
        drawCallback: function () {
            const api = this.api();
            const count = api.page.info().recordsDisplay;
            $('#filteredCounter').text(`${count} letters shown`);
        }
    });

    // --- EVENT LISTENERS FOR FILTERS ---
    // Note the updated column indices to match the new table structure
    $('#filter-id').on('keyup', function () { table.column(1).search(this.value).draw(); });
    $('#filter-date').on('keyup', function () { table.column(2).search(this.value).draw(); });
    $('#filter-sender').on('keyup', function () { table.column(3).search(this.value).draw(); });
    $('#filter-recipient').on('keyup', function () { table.column(4).search(this.value).draw(); });
    $('#filter-place').on('keyup', function () { table.column(5).search(this.value).draw(); });
    $('#filter-provenance').on('keyup', function () { table.column(6).search(this.value).draw(); }); // This filter is now active

    $('#filterCheckbox').on('change', function () {
        if (this.checked) {
            $.fn.dataTable.ext.search.push((settings, data, dataIndex) => {
                return $(table.row(dataIndex).node()).attr('data-status') === 'online';
            });
        } else {
            $.fn.dataTable.ext.search.pop();
        }
        table.draw();
    });

    // --- EVENT LISTENER FOR EXPAND/COLLAPSE ---
    $('#letter-table tbody').on('click', 'td.dt-control', async function (event) {
        event.stopPropagation();
        const tr = $(this).closest('tr');
        const row = table.row(tr);
        const icon = tr.find('td.dt-control i');

        if (row.child.isShown()) {
            row.child.hide();
            tr.removeClass('dt-hasChild');
            icon.removeClass('bi-dash-lg').addClass('bi-plus-lg');
        } else {
            tr.addClass('dt-hasChild');
            icon.removeClass('bi-plus-lg').addClass('bi-dash-lg');
            
            row.child('<div><span class="spinner-border spinner-border-sm"></span> Loading details...</div>').show();

            const letterKey = tr.data('key');
            try {
                const detailsHtml = await getFormattedDetails(letterKey, tr.data());
                row.child(detailsHtml).show();
            } catch (error) {
                row.child('<div class="text-danger p-3">Could not load letter details.</div>').show();
                console.error("Error fetching letter details:", error);
            }
        }
    });

    // --- HELPER FUNCTIONS ---
    const detailsCache = new Map();

    async function getFormattedDetails(key, rowData) {
        if (detailsCache.has(key)) {
            return detailsCache.get(key);
        }
        
        const url = `https://raw.githubusercontent.com/michaelscho/lassberg/main/data/letters/${key}.xml`;
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`File not found or couldn't be fetched from ${url}`);
        }
        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "text/xml");

        const summaryNode = xmlDoc.querySelector('div[type="summary"]');
        const summary = summaryNode ? summaryNode.textContent.trim() : 'No summary available.';

        const openLetterButton = rowData.status === 'online' 
            ? `<a href="../html/letters/${key}.html" class="btn btn-primary btn-sm mt-3" target="_blank">Open Full Letter Page</a>` 
            : '';

        const html = `
            <div class="collapsible-content p-3">
                <div class="row">
                    <div class="col-12">
                        <strong>Harris ID:</strong> <span class="text-muted">${rowData.harris || 'N/A'}</span>
                    </div>
                </div>
                <hr class="my-2">
                <h6>Summary</h6>
                <p class="text-muted small mb-0">${summary}</p>
                ${openLetterButton}
            </div>`;
        
        detailsCache.set(key, html);
        return html;
    }
});