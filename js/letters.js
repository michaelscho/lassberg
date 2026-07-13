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

    // EVENT LISTENERS FOR FILTERS
    $('#filter-id').on('keyup', function () { table.column(1).search(this.value).draw(); });
    $('#filter-date').on('keyup', function () { table.column(2).search(this.value).draw(); });
    $('#filter-sender').on('keyup', function () { table.column(3).search(this.value).draw(); });
    $('#filter-recipient').on('keyup', function () { table.column(4).search(this.value).draw(); });
    $('#filter-place').on('keyup', function () { table.column(5).search(this.value).draw(); });
    $('#filter-provenance').on('keyup', function () { table.column(6).search(this.value).draw(); }); // This filter is now active

    // Status filters (docs/TEI.md "Letter status model"): data-status carries the register's
    // @change value — in_register | preview_{print,transcription} | online_{print,transcription}.
    // "With full text online" = preview_* or online_*; "Reviewed editions only" = online_*.
    const statusFilter = (settings, data, dataIndex) => {
        const status = $(table.row(dataIndex).node()).attr('data-status') || '';
        if ($('#filterReviewed').is(':checked')) return status.startsWith('online');
        if ($('#filterFulltext').is(':checked')) return status.startsWith('online') || status.startsWith('preview');
        return true;
    };
    $.fn.dataTable.ext.search.push(statusFilter);
    $('#filterFulltext, #filterReviewed').on('change', () => table.draw());

    initExpandableRows(table, '#letter-table');
    applyDeepLinkSearch(table);
});
