/**
 * Krishi Mitra (AgriNova) - Interactive Farm Field GIS Map (Leaflet)
 * Renders farm polygons, centroid coordinates, satellite/street views & area metrics
 */

class FarmFieldMap {
  constructor(containerId = 'farm-map') {
    this.containerId = containerId;
    this.map = null;
    this.polygonLayer = null;
    this.markerLayer = null;
    this.drawingLayer = null;
    this.currentPlot = null;
  }

  init(center = [17.50045, 78.50047], zoom = 16) {
    const container = document.getElementById(this.containerId);
    if (!container) return;

    if (this.map) {
      this.map.remove();
    }

    // Base Tile Layers
    const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    });

    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    });

    // Initialize Leaflet Map
    this.map = L.map(this.containerId, {
      center: center,
      zoom: zoom,
      layers: [satelliteLayer] // Default to high-res satellite
    });

    // Layer Switcher Control
    const baseMaps = {
      '🛰️ Satellite View': satelliteLayer,
      '🗺️ Street Map': streetLayer
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(this.map);

    // Drawing layer group
    this.drawingLayer = L.featureGroup().addTo(this.map);
  }

  /**
   * Render farm field polygon from GeoJSON coordinates
   */
  renderPlotPolygon(plot) {
    if (!this.map || !plot) return;
    this.currentPlot = plot;

    // Clear previous layers
    if (this.polygonLayer) this.map.removeLayer(this.polygonLayer);
    if (this.markerLayer) this.map.removeLayer(this.markerLayer);

    const boundary = plot.boundary;
    if (!boundary || !boundary.coordinates || !boundary.coordinates[0]) return;

    // Convert GeoJSON [lon, lat] to Leaflet [lat, lon]
    const latLngs = boundary.coordinates[0].map(coord => [coord[1], coord[0]]);

    // Styled Polygon
    this.polygonLayer = L.polygon(latLngs, {
      color: '#10b981', // Emerald
      weight: 3,
      opacity: 0.9,
      fillColor: '#34d399',
      fillOpacity: 0.35,
      dashArray: '4, 6'
    }).addTo(this.map);

    // Centroid marker with custom agricultural pin
    const centroidLat = plot.centroid_lat || latLngs[0][0];
    const centroidLon = plot.centroid_lon || latLngs[0][1];

    const pinIcon = L.divIcon({
      className: 'custom-farm-pin',
      html: `
        <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-emerald-600 text-white shadow-lg border-2 border-white transform -translate-x-1/2 -translate-y-1/2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"></path>
          </svg>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    this.markerLayer = L.marker([centroidLat, centroidLon], { icon: pinIcon }).addTo(this.map);

    // Interactive Popup
    const popupContent = `
      <div class="p-1 min-w-[200px]">
        <div class="flex items-center gap-2 mb-2 font-semibold text-slate-800 text-sm">
          <span class="text-emerald-600">🌱</span> ${plot.name || 'Farm Plot'}
        </div>
        <div class="grid grid-cols-2 gap-2 text-xs text-slate-600">
          <div><span class="text-slate-400">Area:</span> <b class="text-slate-700">${plot.area_hectares || 1.15} ha</b></div>
          <div><span class="text-slate-400">Soil:</span> <b class="text-slate-700">${plot.soil_texture || 'Vertisol'}</b></div>
          <div><span class="text-slate-400">Survey #:</span> ${plot.survey_number || '45/2'}</div>
          <div><span class="text-slate-400">Slope:</span> ${plot.slope_percent || 1.5}%</div>
        </div>
        <div class="mt-2.5 pt-2 border-t border-slate-200 text-[11px] text-emerald-700 font-medium">
          Coordinates: ${centroidLat.toFixed(4)}°N, ${centroidLon.toFixed(4)}°E
        </div>
      </div>
    `;

    this.polygonLayer.bindPopup(popupContent);
    this.markerLayer.bindPopup(popupContent);

    // Zoom map to fit polygon bounds
    this.map.fitBounds(this.polygonLayer.getBounds(), { padding: [40, 40] });
  }

  resize() {
    if (this.map) {
      setTimeout(() => {
        this.map.invalidateSize();
      }, 200);
    }
  }
}

window.FarmFieldMap = FarmFieldMap;
