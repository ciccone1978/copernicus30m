// --- Global Variables ---

const SELECTION_STYLE = {
    color: '#005a9e',       // stroke-color (blue)
    fillColor: '#0078d4',  // fill-color (blue)
    fillOpacity: 0.3,
    weight: 1              // stroke-width
};

const ACTIVE_SELECTION_STYLE = {
    color: '#a20b17',       // stroke-color (red)
    fillColor: '#e81123',  // fill-color (red)
    fillOpacity: 0.5,
    weight: 2              // stroke-width
};

let gridLayer = null;
let labelLayer = null;
let selectionLayer = null;
let isGridVisible = true;
let highlightedTiles = {};
let currentlyActiveTileId = null;

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
    const rect = L.rectangle(bounds, { interactive: false });
    rect.setStyle(SELECTION_STYLE);
    
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

function clearAllHighlights() {
    if (selectionLayer) {
        selectionLayer.clearLayers();
        highlightedTiles = {}; // Reset the tracking object
    }
}

/**
 * Clears all existing highlights and draws new ones for the given tiles.
 * This is more efficient than calling addHighlight for each tile from Python.
 * @param {Array<Array<number>>} tiles - An array of [lat, lon] pairs.
 */
function syncHighlights(tiles) {
    // 1. Clear everything first
    if (selectionLayer) {
        selectionLayer.clearLayers();
    }
    highlightedTiles = {};

    // 2. If there are tiles to draw, add them
    if (tiles && tiles.length > 0) {
        if (!selectionLayer) {
            selectionLayer = L.layerGroup().addTo(map);
        }
        
        const newHighlightLayers = [];
        tiles.forEach(tile => {
            const lat = tile[0];
            const lon = tile[1];
            
            const bounds = [[lat, lon], [lat + 1, lon + 1]];
            const rect = L.rectangle(bounds, { interactive: false });
            rect.setStyle(SELECTION_STYLE);
            
            const tileId = `${lat}_${lon}`;
            highlightedTiles[tileId] = rect; // Store for individual removal later
            newHighlightLayers.push(rect);
        });
        
        // Add all new layers in a single, efficient operation
        newHighlightLayers.forEach(layer => selectionLayer.addLayer(layer));
    }
}


/**
 * Changes the style of a specific tile highlight to 'active' (e.g., red).
 * Resets the style of the previously active tile.
 * @param {number} lat - The integer latitude of the tile to activate.
 * @param {number} lon - The integer longitude of the tile to activate.
 */
function setActiveHighlight(lat, lon) {
    
    console.log(`--- setActiveHighlight called with lat: ${lat}, lon: ${lon} ---`);

    // First, reset the previously active tile, if there was one
    if (currentlyActiveTileId) {
        const oldRect = highlightedTiles[currentlyActiveTileId];
        console.log("Found old active tile:", currentlyActiveTileId, "Rect:", oldRect);
        if (oldRect) {
            oldRect.setStyle(SELECTION_STYLE);
        }
    }

    // Now, set the new active tile
    const newTileId = `${lat}_${lon}`;
    const newRect = highlightedTiles[newTileId];

    console.log("Trying to find new tile:", newTileId);
    console.log("All highlighted tiles known to JS:", Object.keys(highlightedTiles));
    console.log("Finding rect:", newRect);

    if (newRect) {
        console.log("SUCCESS: Found rect. Applying active style.");
        newRect.setStyle(ACTIVE_SELECTION_STYLE);
        newRect.bringToFront();
        currentlyActiveTileId = newTileId;
    } else {
        console.error("FAILURE: Could not find a highlight rectangle for this tile ID.");
    }
}

/**
 * Resets the style of the currently active tile back to the default selection color.
 */
function clearActiveHighlight() {
    if (currentlyActiveTileId) {
        const oldRect = highlightedTiles[currentlyActiveTileId];
        if (oldRect) {
            oldRect.setStyle(SELECTION_STYLE);
        }
        currentlyActiveTileId = null;
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