// --- Global Variables ---
let gridLayer = null; // This will hold our grid lines layer
let labelLayer = null; // This will hold our text labels
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
    
    // Clear existing layers before redrawing
    if (gridLayer) gridLayer.clearLayers();
    if (labelLayer) labelLayer.clearLayers();
    
    // Don't draw if zoomed too far out
    if (map.getZoom() < 4) {
        return;
    }

    // Get the geographical bounds of the visible map area
    const bounds = map.getBounds();
    const north = Math.ceil(bounds.getNorth());
    const south = Math.floor(bounds.getSouth());
    const east = Math.ceil(bounds.getEast());
    const west = Math.floor(bounds.getWest());

    const gridLines = [];
    const gridLabels = [];

    // --- Create Vertical Lines (Longitude) and their labels ---
    for (let lon = west; lon <= east; lon++) {
        const line = L.polyline([[north + 1, lon], [south - 1, lon]], {
            color: '#555', weight: 1, opacity: 0.7, interactive: false
        });
        gridLines.push(line);

        // Add a label for the longitude line at the top of the screen
        const labelText = lon > 0 ? `${lon}°E` : lon < 0 ? `${Math.abs(lon)}°W` : `${lon}°`;
        const labelPos = [bounds.getNorth() - 0.1, lon + 0.05]; // Position slightly inside the view
        const label = L.marker(labelPos, {
            icon: L.divIcon({
                className: 'grid-label',
                html: labelText
            }),
            interactive: false
        });
        gridLabels.push(label);
    }

    // --- Create Horizontal Lines (Latitude) and their labels ---
    for (let lat = south; lat <= north; lat++) {
        const line = L.polyline([[lat, west - 1], [lat, east + 1]], {
            color: '#555', weight: 1, opacity: 0.7, interactive: false
        });
        gridLines.push(line);

        // Add a label for the latitude line on the left of the screen
        const labelText = lat > 0 ? `${lat}°N` : lat < 0 ? `${Math.abs(lat)}°S` : `${lat}°`;
        const labelPos = [lat + 0.05, bounds.getWest() + 0.1]; // Position slightly inside the view
        const label = L.marker(labelPos, {
            icon: L.divIcon({
                className: 'grid-label',
                html: labelText
            }),
            interactive: false
        });
        gridLabels.push(label);
    }

    // --- Manage Layers ---
    // Initialize layers if they don't exist
    if (!gridLayer) {
        gridLayer = L.layerGroup().addTo(map);
    }
    if (!labelLayer) {
        labelLayer = L.layerGroup().addTo(map);
    }
    
    // Add new lines and labels to their respective layers
    gridLines.forEach(line => gridLayer.addLayer(line));
    gridLabels.forEach(label => labelLayer.addLayer(label));

    // Ensure the visibility matches the toggle state
    toggleGridVisibility(isGridVisible);
}

/**
 * Toggles the visibility of the grid and label layers.
 * @param {boolean} isVisible - True to show, false to hide.
 */
function toggleGridVisibility(isVisible) {
    isGridVisible = isVisible;
    if (!gridLayer || !labelLayer) return;

    if (isGridVisible) {
        map.addLayer(gridLayer);
        map.addLayer(labelLayer);
    } else {
        map.removeLayer(gridLayer);
        map.removeLayer(labelLayer);
    }
}

// --- Event Listeners ---
// Redraw the grid whenever the user finishes moving or zooming the map.
map.on('moveend', updateGrid);

// --- Initial Grid Draw ---
// Perform an initial draw when the script loads.
updateGrid();


// --- QWebChannel Initialization ---
// This code block sets up the connection from JavaScript to Python.
document.addEventListener("DOMContentLoaded", () => {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        // 'backend' is the name we registered in our Python code.
        // window.backend is now a JavaScript object that mirrors our MapBridge Python object.
        window.backend = channel.objects.backend;

        // Now that the bridge is set up, we can add the mouse listener.
        if (window.backend) {
            map.on('mousemove', function(e) {
                // Call the 'on_mouse_move' slot on our Python MapBridge object
                // and pass the latitude and longitude as arguments.
                window.backend.on_mouse_move(e.latlng.lat, e.latlng.lng);
            });
        } else {
            console.error("Backend object not found in QWebChannel.");
        }
    });
});