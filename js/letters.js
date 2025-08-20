document.addEventListener('DOMContentLoaded', function () {

    const table = $('#letter-table').DataTable({
        paging: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
        info: true,
        responsive: true,
        order: [[2, 'asc']], // Default sort by Date (now column index 2)
        columnDefs: [
            {
                orderable: false,
                className: 'dt-control',
                targets: 0,
                defaultContent: ''
            }
        ],
        drawCallback: function () {
            const api = this.api();
            const count = api.page.info().recordsDisplay;
            $('#filteredCounter').text(`${count} letters shown`);
        }
    });

    // --- EVENT LISTENERS FOR FILTERS ---
    $('#filter-id').on('keyup', function () { table.column(1).search(this.value).draw(); });
    $('#filter-date').on('keyup', function () { table.column(2).search(this.value).draw(); });
    $('#filter-sender').on('keyup', function () { table.column(3).search(this.value).draw(); });
    $('#filter-recipient').on('keyup', function () { table.column(4).search(this.value).draw(); });
    $('#filter-place').on('keyup', function () { table.column(5).search(this.value).draw(); });

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
        const icon = $(this).find('i');

        if (row.child.isShown()) {
            row.child.hide();
            tr.removeClass('dt-hasChild');
            icon.removeClass('bi-dash-lg').addClass('bi-plus-lg');
        } else {
            tr.addClass('dt-hasChild');
            icon.removeClass('bi-plus-lg').addClass('bi-dash-lg');
            
            // Show a loading message while we fetch the details
            row.child('<div><span class="spinner-border spinner-border-sm" role="status"></span> Loading details...</div>').show();

            const letterKey = tr.data('key');
            try {
                // Fetch and display the rich details
                const detailsHtml = await getFormattedDetails(letterKey, tr.data());
                row.child(detailsHtml).show();
            } catch (error) {
                row.child('<div class="text-danger">Could not load letter details.</div>').show();
                console.error("Error fetching letter details:", error);
            }
        }
    });

    // --- HELPER FUNCTIONS ---

    // Cache to store fetched letter details to avoid repeated network requests
    const detailsCache = new Map();

    async function getFormattedDetails(key, rowData) {
        if (detailsCache.has(key)) {
            return detailsCache.get(key);
        }

        const url = `../data/letters/${key}.xml`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`File not found: ${url}`);
        }
        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "text/xml");

        const summaryNode = xmlDoc.querySelector('div[type="summary"]');
        const summary = summaryNode ? summaryNode.textContent.trim() : 'No summary available.';

        // Create the "Open Letter" button only if the status is "online"
        const openLetterButton = rowData.status === 'online' 
            ? `<a href="../html/letters/${key}.html" class="btn btn-primary btn-sm mt-2" target="_blank">Open Letter</a>` 
            : '';

        const html = `
            <div class="collapsible-content p-3">
                <div class="row">
                    <div class="col-md-6">
                        <strong>Provenance:</strong> <span class="text-muted">${rowData.provenance || 'N/A'}</span><br/>
                        <strong>Harris ID:</strong> <span class="text-muted">${rowData.harris || 'N/A'}</span>
                    </div>
                </div>
                <hr>
                <h6>Summary</h6>
                <p class="text-muted small">${summary}</p>
                ${openLetterButton}
            </div>`;
        
        detailsCache.set(key, html); // Cache the result
        return html;
    }
});