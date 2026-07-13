document.addEventListener('DOMContentLoaded', function () {

    const table = $('#place-table').DataTable({
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
            $('#filteredCounter').text(`${count} places shown`);
        }
    });

    $('#filter-name').on('keyup', function () { table.column(1).search(this.value).draw(); });

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

    initExpandableRows(table, '#place-table');
    applyDeepLinkSearch(table);

    // Build the overview map from every row's data-lat/data-lon/data-radius (present only for
    // places with coordinates; see places.xsl). `map` is created by the inline script at the
    // end of the page body, which runs before this DOMContentLoaded handler.
    const placeMarkers = {};
    table.rows().every(function () {
        const node = $(this.node());
        const lat = node.attr('data-lat');
        const lon = node.attr('data-lon');
        if (!lat || !lon) return;
        const name = node.attr('data-name');
        const mentions = node.attr('data-mentions');
        const radius = Number(node.attr('data-radius'));
        const marker = L.circleMarker([Number(lat), Number(lon)], {
            radius: radius, color: '#143761', weight: 1.5, fillColor: '#1d4e89', fillOpacity: 0.6
        }).addTo(window.map).bindPopup(`${name} (${mentions} letters)`);
        placeMarkers[node.attr('data-key')] = marker;
    });

    // Clicking a place name in the table flies the map to its marker and opens its popup.
    $('#place-table tbody').on('click', '.place-map-link', function (event) {
        event.preventDefault();
        const id = $(this).data('place-id');
        const marker = placeMarkers[id];
        if (!marker) return;
        window.map.flyTo(marker.getLatLng(), 10);
        marker.openPopup();
        document.getElementById('places-map').scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
});
