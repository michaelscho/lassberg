// This script assumes jQuery and DataTables are already loaded on the page.

document.addEventListener('DOMContentLoaded', function () {
    // Initialize the DataTable with basic configuration
    const table = $('#letter-table').DataTable({
        "paging": true,
        "pageLength": 25,
        "lengthChange": true,
        "lengthMenu": [[10, 25, 50, -1], [10, 25, 50, "All"]],
        "info": false,
        "responsive": true,
        "order": [[1, 'asc']], // Default sort by Date column
        "columnDefs": [
            { "orderable": false, "targets": 0 }, // Disable sorting on the details icon column
            { "className": 'dt-control', "targets": 0 }
        ]
    });

    // --- DATA FETCHING AND TABLE POPULATION ---
    
    // Fetch the main letter register data
    fetch('../data/register/final_register.xml')
        .then(response => response.text())
        .then(str => (new DOMParser()).parseFromString(str, "text/xml"))
        .then(data => {
            const letters = Array.from(data.querySelectorAll('correspDesc'));
            populateTable(letters, table);
            updateCounter(table);
        })
        .catch(error => {
            console.error('Error fetching or parsing letter data:', error);
            $('#filteredCounter').text('Error loading data.');
        });
        
    function populateTable(letters, dt) {
        dt.clear(); // Clear the table before adding new rows

        letters.forEach(letter => {
            const rowNode = dt.row.add([
                '', // Placeholder for the expand/collapse icon
                letter.querySelector('correspAction[type="sent"] date')?.getAttribute('when') || 'N/A',
                letter.querySelector('correspAction[type="sent"] persName')?.textContent.trim() || 'N/A',
                letter.querySelector('correspAction[type="received"] persName')?.textContent.trim() || 'N/A',
                letter.querySelector('correspAction[type="sent"] placeName')?.textContent.trim() || 'N/A',
                `${letter.querySelector('note[type="aufbewahrungsort"]')?.textContent.trim() || ''}, ${letter.querySelector('note[type="aufbewahrungsinstitution"]')?.textContent.trim() || ''}`
            ]).node();
            
            // Attach status and the full letter data for the child row
            $(rowNode).attr('data-status', letter.getAttribute('change') || 'in_register');
            $(rowNode).data('letter-data', letter); // Store the XML element itself
        });

        dt.draw();
    }

    // --- EVENT LISTENERS ---

    // Listeners for the custom text filter inputs
    $('#filter-date').on('keyup', function() { table.column(1).search(this.value).draw(); updateCounter(table); });
    $('#filter-sender').on('keyup', function() { table.column(2).search(this.value).draw(); updateCounter(table); });
    $('#filter-recipient').on('keyup', function() { table.column(3).search(this.value).draw(); updateCounter(table); });
    $('#filter-place').on('keyup', function() { table.column(4).search(this.value).draw(); updateCounter(table); });
    $('#filter-provenance').on('keyup', function() { table.column(5).search(this.value).draw(); updateCounter(table); });

    // Listener for the "transcribed" checkbox
    $('#filterCheckbox').on('change', function () {
        if (this.checked) {
            // Apply a custom search function to filter rows by data-status
            $.fn.dataTable.ext.search.push((settings, data, dataIndex) => {
                return $(table.row(dataIndex).node()).attr('data-status') === 'online';
            });
        } else {
            // Remove the custom search function to show all rows
            $.fn.dataTable.ext.search.pop();
        }
        table.draw();
        updateCounter(table);
    });

    // Listener for opening and closing child row details
    $('#letter-table tbody').on('click', 'td.dt-control', function () {
        const tr = $(this).closest('tr');
        const row = table.row(tr);
        const icon = $(this).find('i');

        if (row.child.isShown()) {
            row.child.hide();
            tr.removeClass('dt-hasChild');
            icon.removeClass('bi-dash-lg').addClass('bi-plus-lg');
        } else {
            const letterData = tr.data('letter-data');
            row.child(formatChildRow(letterData)).show();
            tr.addClass('dt-hasChild');
            icon.removeClass('bi-plus-lg').addClass('bi-dash-lg');
        }
    });

    // --- HELPER FUNCTIONS ---

    function updateCounter(dt) {
        const count = dt.rows({ search: 'applied' }).count();
        $('#filteredCounter').text(`${count} letters shown`);
    }

    function formatChildRow(letter) {
        // This function builds the HTML for the expandable details section
        const scanUrl = letter.querySelector('note[type="url_facsimile"]')?.textContent.trim();
        const printNote = letter.querySelector('note[type="published_in"]');
        const printUrl = printNote?.getAttribute('target');
        const printText = printNote?.textContent.trim();

        const scanLink = scanUrl ? `<a href="${scanUrl}" target="_blank">View Scan</a>` : `<span class="text-muted">Not available</span>`;
        const printLink = printUrl ? `<a href="${printUrl}" target="_blank">${printText || 'View Print'}</a>` : `<span class="text-muted">Not available</span>`;

        return `
            <div class="collapsible-content p-2">
                <div class="row">
                    <div class="col-md-6">
                        <strong>Harris ID:</strong> <span class="text-muted">${letter.querySelector('note[type="nummer_harris"]')?.textContent.trim() || 'N/A'}</span><br/>
                        <strong>Signature:</strong> <span class="text-muted">${letter.querySelector('note[type="signatur"]')?.textContent.trim() || 'N/A'}</span><br/>
                        <strong>Journal:</strong> <span class="text-muted">${letter.querySelector('note[type="journalnummer"]')?.textContent.trim() || 'N/A'}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Scan:</strong> ${scanLink}<br/>
                        <strong>Print:</strong> ${printLink}
                    </div>
                </div>
            </div>`;
    }
});