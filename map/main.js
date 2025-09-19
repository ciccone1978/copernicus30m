// Initialize the map and set its view to a chosen geographical coordinates and a zoom level
// L is the main Leaflet object, available because we included leaflet.js
const map = L.map('map').setView([41.9028, 12.4964], 6); // Centered on Rome, Italy

// Add a tile layer to the map. This is the background imagery.
// We're using OpenStreetMap, a free and open map source.
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);