// --- Global Variables ---
let gridLayer = null; // This will hold our grid lines layer
let isGridVisible = true; // The initial state of the grid

// --- Initialize the Map ---
const map = L.map('map').setView([41.9028, 12.4964], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

// --- Grid Drawing Logic ---

/**
 * Updates and redraws the 1x1 degree grid based on the current map view.
 */
function updateGrid() {
    // Don't draw the grid if zoomed too far out
    if (map.getZoom() < 4) {
        if (gridLayer) {
            gridLayer.clearLayers();
        }
        return;
    }

    // Get the geographical bounds of the visible map area
    const bounds = map.getBounds();
    const north = Math.ceil(bounds.getNorth());
    const south = Math.floor(bounds.getSouth());
    const east = Math.ceil(bounds.getEast());
    const west = Math.floor(bounds.getWest());

    const gridLines = [];

    // Create vertical lines (longitude)
    for (let lon = west; lon <= east; lon++) {
        const line = L.polyline([[north + 1, lon], [south - 1, lon]], {
            color: '#555',
            weight: 1,
            opacity: 0.7,
            interactive: false // Lines should not be clickable
        });
        gridLines.push(line);
    }

    // Create horizontal lines (latitude)
    for (let lat = south; lat <= north; lat++) {
        const line = L.polyline([[lat, west - 1], [lat, east + 1]], {
            color: '#555',
            weight: 1,
            opacity: 0.7,
            interactive: false
        });
        gridLines.push(line);
    }

    // Update the grid layer with the new lines
    if (!gridLayer) {
        gridLayer = L.layerGroup(gridLines).addTo(map);
    } else {
        gridLayer.clearLayers();
        gridLines.forEach(line => gridLayer.addLayer(line));
    }
}

/**
 * Toggles the visibility of the entire grid layer.
 * This function will be called from our Python code.
 * @param {boolean} isVisible - True to show the grid, false to hide it.
 */
function toggleGridVisibility(isVisible) {
    if (!gridLayer) return;

    isGridVisible = isVisible;
    if (isGridVisible) {
        map.addLayer(gridLayer);
    } else {
        map.removeLayer(gridLayer);
    }
}

// --- Event Listeners ---
// Redraw the grid whenever the user finishes moving or zooming the map.
map.on('moveend', updateGrid);

// --- Initial Grid Draw ---
// Perform an initial draw when the script loads.
updateGrid();