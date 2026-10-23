document.addEventListener('DOMContentLoaded', function () {

    const table = $('#manuscript-table').DataTable({
        paging: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
        info: true,
        order: [[1, 'asc']],
        columnDefs: [{ orderable: false, className: 'dt-control', targets: 0 }],
        drawCallback: function () {
            const count = this.api().page.info().recordsDisplay;
            $('#filteredCounter').text(`${count} manuscripts shown`);
        }
    });

    // name + shelfmark columns
    $('#filter-name').on('keyup', function () { table.search(this.value).draw(); });

    $('#filterCheckbox').on('change', function () {
        if (this.checked) {
            $.fn.dataTable.ext.search.push((settings, data, dataIndex) => {
                return Number($(table.row(dataIndex).node()).attr('data-mentions')) > 0;
            });
        } else {
            $.fn.dataTable.ext.search.pop();
        }
        table.draw();
    });

    initExpandableRows(table, '#manuscript-table');
    applyDeepLinkSearch(table);
});
