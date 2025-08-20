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
    if (detailsCache.has(key)) return detailsCache.get(key);

    // Use pre-rendered HTML from XSLT
    const tpl = document.getElementById(`details-${key}`);
    if (tpl) {
        const html = tpl.innerHTML;   // content of <template>
        detailsCache.set(key, html);
        return html;
    }

    // Fallback (optional): show a message if template is missing
    const html = '<div class="text-muted p-3">No details available.</div>';
    detailsCache.set(key, html);
    return html;
}

});