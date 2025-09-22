// --- Global Variables ---
let gridLayer = null;
let labelLayer = null;
let selectionLayer = null; // NEW: Layer for highlight polygons
let isGridVisible = true;
let highlightedTiles = {}; // NEW: Object to keep track of highlight layers

// --- Initialize the Map ---
const map = L.map('map').setView([41.9028, 12.4964], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

// --- Grid and Label Drawing Logic ---
// ... (The entire updateGrid function remains exactly the same as before) ...
function updateGrid() {
    if (gridLayer) gridLayer.clearLayers();
    if (labelLayer) labelLayer.clearLayers();
    if (map.getZoom() < 4) return;
    const bounds = map.getBounds();
    const north = Math.ceil(bounds.getNorth()), south = Math.floor(bounds.getSouth());
    const east = Math.ceil(bounds.getEast()), west = Math.floor(bounds.getWest());
    const gridLines = [], gridLabels = [];
    for (let lon = west; lon <= east; lon++) {
        gridLines.push(L.polyline([[north + 1, lon], [south - 1, lon]], { color: '#555', weight: 1, opacity: 0.7, interactive: false }));
        const labelText = lon > 0 ? `${lon}°E` : lon < 0 ? `${Math.abs(lon)}°W` : `${lon}°`;
        gridLabels.push(L.marker([bounds.getNorth() - 0.1, lon + 0.05], { icon: L.divIcon({ className: 'grid-label', html: labelText }), interactive: false }));
    }
    for (let lat = south; lat <= north; lat++) {
        gridLines.push(L.polyline([[lat, west - 1], [lat, east + 1]], { color: '#555', weight: 1, opacity: 0.7, interactive: false }));
        const labelText = lat > 0 ? `${lat}°N` : lat < 0 ? `${Math.abs(lat)}°S` : `${lat}°`;
        gridLabels.push(L.marker([lat + 0.05, bounds.getWest() + 0.1], { icon: L.divIcon({ className: 'grid-label', html: labelText }), interactive: false }));
    }
    if (!gridLayer) gridLayer = L.layerGroup().addTo(map);
    if (!labelLayer) labelLayer = L.layerGroup().addTo(map);
    gridLines.forEach(line => gridLayer.addLayer(line));
    gridLabels.forEach(label => labelLayer.addLayer(label));
    toggleGridVisibility(isGridVisible);
}

function toggleGridVisibility(isVisible) {
    // ... (This function also remains exactly the same) ...
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

// --- NEW: Highlight Drawing Logic (called from Python) ---
/**
 * Draws a highlight rectangle for a given tile.
 * @param {number} lat - The integer latitude of the tile's SW corner.
 * @param {number} lon - The integer longitude of the tile's SW corner.
 */
function addHighlight(lat, lon) {
    if (!selectionLayer) {
        selectionLayer = L.layerGroup().addTo(map);
    }
    const bounds = [[lat, lon], [lat + 1, lon + 1]];
    const rect = L.rectangle(bounds, {
        className: 'selection-polygon', // Our custom CSS class
        interactive: false // The highlight itself shouldn't be clickable
    });
    
    const tileId = `${lat}_${lon}`;
    highlightedTiles[tileId] = rect; // Store the layer
    selectionLayer.addLayer(rect);
}

/**
 * Removes a highlight rectangle for a given tile.
 * @param {number} lat - The integer latitude of the tile's SW corner.
 * @param {number} lon - The integer longitude of the tile's SW corner.
 */
function removeHighlight(lat, lon) {
    const tileId = `${lat}_${lon}`;
    const rect = highlightedTiles[tileId];
    if (rect && selectionLayer) {
        selectionLayer.removeLayer(rect);
        delete highlightedTiles[tileId]; // Clean up the stored layer
    }
}

// --- Event Listeners ---
map.on('moveend', updateGrid);
updateGrid(); // Initial draw

// --- QWebChannel Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        window.backend = channel.objects.backend;

        if (window.backend) {
            // Mouse move for status bar
            map.on('mousemove', e => {
                window.backend.on_mouse_move(e.latlng.lat, e.latlng.lng, map.getZoom());
            });
            map.on('zoomend', () => {
                const center = map.getCenter();
                window.backend.on_mouse_move(center.lat, center.lng, map.getZoom());
            });

            // --- NEW: Map click for tile selection ---
            map.on('click', e => {
                const lat = Math.floor(e.latlng.lat);
                const lon = Math.floor(e.latlng.lng);
                // Call the new slot on our Python bridge object
                window.backend.on_tile_clicked(lat, lon);
            });

        } else {
            console.error("Backend object not found in QWebChannel.");
        }
    });
});