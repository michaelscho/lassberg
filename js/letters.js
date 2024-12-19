document.addEventListener("DOMContentLoaded", function () {
    const rowsToLoad = 100; // Number of rows to load at a time
    const table = document.getElementById("letter-table");
    const allRows = Array.from(table.querySelectorAll("tbody tr:not(.collapsible-row)")); // Main rows
    const collapsibleRows = Array.from(table.querySelectorAll(".collapsible-row")); // Collapsible rows
    const inputs = document.querySelectorAll("thead input"); // Filter inputs
    const filterCheckbox = document.getElementById("filterCheckbox"); // Checkbox for filtering
    const filteredCounter = document.getElementById("filteredCounter"); // Counter element
    let filteredRows = [...allRows]; // Start with all rows
    let lastLoadedIndex = 0; // Tracks the last loaded row for lazy loading
    let debounceTimeout; // Timeout for debounced actions

    // Function to update the visible row counter with debounce
    function updateCounter() {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            const visibleRows = filteredRows.length;
            filteredCounter.textContent = visibleRows; // Update the visible row count to show total filtered rows
        }, 200); // Debounce delay to avoid frequent updates
    }

    // Function to filter rows based on input and checkbox
    function filterTable() {
        const showOnlyTranscribed = filterCheckbox.checked;

        // Filter rows based on inputs and checkbox
        filteredRows = allRows.filter(row => {
            let rowVisible = true;

            // Apply checkbox filter
            const status = row.getAttribute("data-status");
            if (showOnlyTranscribed && status !== "in_oxygen_done") {
                return false;
            }

            // Apply input filters
            inputs.forEach(input => {
                const columnIndex = input.getAttribute("data-column");
                const filterValue = input.value.trim().toLowerCase();
                const cellValue = row.cells[columnIndex]?.textContent.trim().toLowerCase() || "";

                if (columnIndex === "5") {
                    // Special case for "Mentioned" column
                    const collapsibleRow = row.nextElementSibling; // Associated collapsible row
                    const personsDiv = collapsibleRow
                        ? collapsibleRow.querySelector(".mentioned-persons")?.textContent.trim().toLowerCase() || ""
                        : "";
                    const placesDiv = collapsibleRow
                        ? collapsibleRow.querySelector(".mentioned-places")?.textContent.trim().toLowerCase() || ""
                        : "";
                    const literatureDiv = collapsibleRow
                        ? collapsibleRow.querySelector(".mentioned-literature")?.textContent.trim().toLowerCase() || ""
                        : "";

                    const combinedValue = `${personsDiv} ${placesDiv} ${literatureDiv}`;
                    if (filterValue && !combinedValue.includes(filterValue)) {
                        rowVisible = false;
                    }
                } else {
                    // General case for other columns
                    if (filterValue && !cellValue.includes(filterValue)) {
                        rowVisible = false;
                    }
                }
            });

            return rowVisible;
        });

        // Reset lazy loading and hide all rows
        lastLoadedIndex = 0;
        allRows.forEach(row => (row.style.display = "none"));
        collapsibleRows.forEach(row => (row.style.display = "none"));

        // Show the filtered rows and their associated collapsible rows
        loadMoreRows(); // Load the first batch of filtered rows
        updateCounter(); // Update the counter

        // Reattach scroll listener if necessary
        window.removeEventListener("scroll", handleScroll);
        if (filteredRows.length > rowsToLoad) {
            window.addEventListener("scroll", handleScroll);
        }
    }

    // Function to load more rows for lazy loading
    function loadMoreRows() {
        const end = Math.min(lastLoadedIndex + rowsToLoad, filteredRows.length);

        for (let i = lastLoadedIndex; i < end; i++) {
            const row = filteredRows[i];
            row.style.display = ""; // Show the filtered row
            const collapsibleRow = row.nextElementSibling; // Associated collapsible row
            if (collapsibleRow && collapsibleRows.includes(collapsibleRow)) {
                collapsibleRow.style.display = ""; // Show the collapsible row if its parent row is visible
            }
        }

        lastLoadedIndex = end;

        // If all rows are loaded or no rows match, detach the scroll listener
        if (lastLoadedIndex >= filteredRows.length || filteredRows.length === 0) {
            window.removeEventListener("scroll", handleScroll);
        }
    }

    // Function to handle scroll events for lazy loading
    function handleScroll() {
        const scrollPosition = window.innerHeight + window.scrollY;
        const threshold = document.body.offsetHeight - 100;

        if (scrollPosition >= threshold) {
            loadMoreRows();
        }
    }

    // Function to toggle collapsible row visibility
    function toggleCollapse(event) {
        const button = event.target;
        const targetId = button.getAttribute("data-target");
        const collapsibleRow = document.querySelector(targetId);

        if (collapsibleRow.style.display === "table-row") {
            collapsibleRow.style.display = "none"; // Hide the collapsible row
            button.textContent = "Expand";
        } else {
            collapsibleRow.style.display = "table-row"; // Show the collapsible row
            button.textContent = "Collapse";

            // Optional: Lazy load content for collapsible rows
            if (!collapsibleRow.dataset.loaded) {
                const lazyContent = collapsibleRow.querySelector(".lazy-content");
                if (lazyContent) {
                    lazyContent.textContent = "Loaded additional content...";
                }
                collapsibleRow.dataset.loaded = true;
            }
        }
    }

    // Function to add alternating row classes
    function applyAlternatingRowClasses() {
        let visibleIndex = 0; // Tracks visible row index for alternating colors

        filteredRows.forEach(row => {
            if (row.style.display !== "none") {
                // Remove previous classes
                row.classList.remove("odd-row", "even-row");

                // Apply alternating classes
                if (visibleIndex % 2 === 0) {
                    row.classList.add("odd-row");
                } else {
                    row.classList.add("even-row");
                }

                visibleIndex++;
            }
        });
    }

    // Attach filter input event listeners
    inputs.forEach(input => {
        input.addEventListener("input", () => {
            filterTable();
            applyAlternatingRowClasses(); // Reapply alternating classes after filtering
        });
    });

    // Attach checkbox event listener
    filterCheckbox.addEventListener("change", () => {
        filterTable();
        applyAlternatingRowClasses(); // Reapply alternating classes after toggling
    });

    // Attach expand button event listeners
    document.querySelectorAll("button[data-target]").forEach(button => {
        button.addEventListener("click", toggleCollapse);
    });

    // Initial setup
    allRows.forEach(row => (row.style.display = "none")); // Hide all rows initially
    collapsibleRows.forEach(row => (row.style.display = "none")); // Hide all collapsible rows
    filterTable(); // Ensure the filter is applied to all rows initially
    loadMoreRows(); // Load the first batch of rows
    window.addEventListener("scroll", handleScroll); // Attach scroll event listener
    updateCounter(); // Initialize the counter
    applyAlternatingRowClasses(); // Apply alternating row classes initially
});
