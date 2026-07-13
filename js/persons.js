document.addEventListener('DOMContentLoaded', function () {

    const table = $('#person-table').DataTable({
        paging: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
        info: true,
        order: [[1, 'asc']], // Default sort by Name
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
            $('#filteredCounter').text(`${count} persons shown`);
        }
    });

    $('#filter-name').on('keyup', function () { table.column(1).search(this.value).draw(); });
    $('#filter-type').on('keyup', function () { table.column(2).search(this.value).draw(); });

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

    initExpandableRows(table, '#person-table');
    applyDeepLinkSearch(table);
});
