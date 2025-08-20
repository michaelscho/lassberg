document.addEventListener('DOMContentLoaded', function () {

    // Initialize the DataTable with configurations
    const table = $('#letter-table').DataTable({
        paging: true,
        pageLength: 25,
        lengthChange: true,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
        info: true, // Shows "Showing 1 to X of Y entries"
        responsive: true,
        order: [[1, 'asc']], // Default sort by Date column
        columnDefs: [
            {
                orderable: false,
                className: 'dt-control', // Essential class for the expand/collapse functionality
                targets: 0,              // Apply to the first column
                defaultContent: ''       // DataTables will handle the icon
            }
        ],
        // This function runs every time the table is drawn (e.g., on filter, sort, or page change)
        drawCallback: function () {
            const api = this.api();
            const count = api.page.info().recordsDisplay; // Gets the count of currently displayed rows
            $('#filteredCounter').text(`${count} letters shown`);
        }
    });

    // --- EVENT LISTENERS FOR FILTERS ---

    // Connects each text input to the search function of its corresponding column
    $('#filter-date').on('keyup', function () { table.column(1).search(this.value).draw(); });
    $('#filter-sender').on('keyup', function () { table.column(2).search(this.value).draw(); });
    $('#filter-recipient').on('keyup', function () { table.column(3).search(this.value).draw(); });
    $('#filter-place').on('keyup', function () { table.column(4).search(this.value).draw(); });
    $('#filter-provenance').on('keyup', function () { table.column(5).search(this.value).draw(); });

    // Custom filter function for the "transcribed" checkbox
    $('#filterCheckbox').on('change', function () {
        if (this.checked) {
            // If checked, filter to only show rows with data-status="online"
            $.fn.dataTable.ext.search.push((settings, data, dataIndex) => {
                return $(table.row(dataIndex).node()).attr('data-status') === 'online';
            });
        } else {
            // If unchecked, remove the custom filter
            $.fn.dataTable.ext.search.pop();
        }
        table.draw(); // Redraw the table with the new filter applied/removed
    });

    // --- EVENT LISTENER FOR EXPAND/COLLAPSE ---

    // Handles clicks on the first column to show/hide child rows
    $('#letter-table tbody').on('click', 'td.dt-control', function (event) {
        event.stopPropagation();
        const tr = $(this).closest('tr');
        const row = table.row(tr);

        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('dt-hasChild');
        } else {
            // Open this row by formatting its child row content
            const letterData = tr.data(); // DataTables automatically reads data-* attributes
            row.child(formatChildRow(letterData)).show();
            tr.addClass('dt-hasChild');
        }
    });

    // --- HELPER FUNCTION ---

    // Creates the HTML for the expandable details section from the row's data-* attributes
    function formatChildRow(data) {
        const scanLink = data.scanUrl ? `<a href="${data.scanUrl}" target="_blank">View Scan</a>` : `<span class="text-muted">Not available</span>`;
        const printLink = data.printUrl ? `<a href="${data.printUrl}" target="_blank">${data.printText || 'View Print'}</a>` : `<span class="text-muted">Not available</span>`;

        return `
            <div class="collapsible-content p-3">
                <div class="row">
                    <div class="col-md-6">
                        <strong>Harris ID:</strong> <span class="text-muted">${data.harris || 'N/A'}</span><br/>
                        <strong>Signature:</strong> <span class="text-muted">${data.signature || 'N/A'}</span><br/>
                        <strong>Journal:</strong> <span class="text-muted">${data.journal || 'N/A'}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Print:</strong> ${printLink}<br/>
                        <strong>Scan:</strong> ${scanLink}
                    </div>
                </div>
            </div>`;
    }
});