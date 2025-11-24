// BRMesh Bridge Frontend Application
let config = {};
let lights = [];
let controllers = [];
let map = null;
let lightMarkers = {};
let controllerMarkers = {};
let selectedLights = new Set();
let currentLightForColor = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    setupTabs();
    setupModals();
    await loadConfig();
    await loadLights();
    await loadControllers();
    await loadEffects();
    await loadScenes();
    initMap();
    
    // Setup event listeners
    document.getElementById('scan-btn').addEventListener('click', scanForLights);
    document.getElementById('refresh-btn').addEventListener('click', refreshAll);
    document.getElementById('save-layout-btn').addEventListener('click', saveLayout);
    document.getElementById('create-scene-btn').addEventListener('click', createScene);
    document.getElementById('add-controller-btn').addEventListener('click', addController);
    
    // Auto-refresh every 5 seconds
    setInterval(refreshAll, 5000);
});

// Tab Navigation
function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // Update active states
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tab}-tab`).classList.add('active');
            
            // Resize map when map tab is activated
            if (tab === 'map' && map) {
                setTimeout(() => map.invalidateSize(), 100);
            }
            
            // Load settings when settings tab is activated
            if (tab === 'settings') {
                loadSettings();
            }
        });
    });
}

// Modal Management
function setupModals() {
    const modal = document.getElementById('color-picker-modal');
    const closeBtn = modal.querySelector('.close');
    
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    const brightnessInput = document.getElementById('brightness-input');
    const brightnessValue = document.getElementById('brightness-value');
    brightnessInput.addEventListener('input', () => {
        brightnessValue.textContent = brightnessInput.value;
    });
    
    document.getElementById('apply-color-btn').addEventListener('click', applyColor);
}

// API Functions
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        config = await response.json();
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

async function loadLights() {
    try {
        const response = await fetch('/api/lights');
        lights = await response.json();
        renderLights();
        renderLightSelectors();
        updateMapMarkers();
    } catch (error) {
        console.error('Failed to load lights:', error);
    }
}

async function loadControllers() {
    try {
        const response = await fetch('/api/controllers');
        controllers = await response.json();
        renderControllers();
        updateMapMarkers();
    } catch (error) {
        console.error('Failed to load controllers:', error);
    }
}

async function loadEffects() {
    try {
        const response = await fetch('/api/effects');
        const effects = await response.json();
        renderEffects(effects);
    } catch (error) {
        console.error('Failed to load effects:', error);
    }
}

async function loadScenes() {
    try {
        const response = await fetch('/api/scenes');
        const scenes = await response.json();
        renderScenes(scenes);
    } catch (error) {
        console.error('Failed to load scenes:', error);
    }
}

// Light Management
function renderLights() {
    const grid = document.getElementById('lights-grid');
    grid.innerHTML = '';
    
    lights.forEach(light => {
        const card = document.createElement('div');
        card.className = `light-card ${light.state.state ? 'active' : ''}`;
        
        const rgb = light.state.rgb || [255, 255, 255];
        const brightness = light.state.brightness || 255;
        const colorHex = rgbToHex(rgb[0], rgb[1], rgb[2]);
        
        card.innerHTML = `
            <div class="light-header">
                <span class="light-name">${light.name}</span>
                <span class="light-status ${light.state.state ? 'on' : ''}"></span>
            </div>
            <div class="light-controls">
                <button class="btn btn-primary" onclick="toggleLight(${light.id})">
                    ${light.state.state ? '⚡ Off' : '💡 On'}
                </button>
                <button class="btn btn-secondary" onclick="pickColor(${light.id})">
                    🎨 Color
                </button>
            </div>
            <div class="color-preview" style="background-color: ${colorHex};" 
                 onclick="pickColor(${light.id})"></div>
        `;
        
        grid.appendChild(card);
    });
}

function renderLightSelectors() {
    const container = document.getElementById('light-selector');
    container.innerHTML = '';
    
    lights.forEach(light => {
        const label = document.createElement('label');
        label.innerHTML = `
            <input type="checkbox" value="${light.id}" 
                   ${selectedLights.has(light.id) ? 'checked' : ''}>
            ${light.name}
        `;
        
        label.querySelector('input').addEventListener('change', (e) => {
            if (e.target.checked) {
                selectedLights.add(parseInt(e.target.value));
            } else {
                selectedLights.delete(parseInt(e.target.value));
            }
        });
        
        container.appendChild(label);
    });
}

async function toggleLight(lightId) {
    const light = lights.find(l => l.id === lightId);
    if (!light) return;
    
    try {
        await fetch(`/api/lights/${lightId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                state: !light.state.state,
                brightness: light.state.brightness || 255,
                rgb: light.state.rgb || [255, 255, 255]
            })
        });
        
        await loadLights();
    } catch (error) {
        console.error('Failed to toggle light:', error);
    }
}

function pickColor(lightId) {
    currentLightForColor = lightId;
    const light = lights.find(l => l.id === lightId);
    
    if (light && light.state.rgb) {
        const colorHex = rgbToHex(...light.state.rgb);
        document.getElementById('color-input').value = colorHex;
    }
    
    if (light && light.state.brightness) {
        document.getElementById('brightness-input').value = light.state.brightness;
        document.getElementById('brightness-value').textContent = light.state.brightness;
    }
    
    document.getElementById('color-picker-modal').style.display = 'block';
}

async function applyColor() {
    if (currentLightForColor === null) return;
    
    const colorHex = document.getElementById('color-input').value;
    const brightness = parseInt(document.getElementById('brightness-input').value);
    const rgb = hexToRgb(colorHex);
    
    try {
        await fetch(`/api/lights/${currentLightForColor}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                state: true,
                brightness: brightness,
                rgb: [rgb.r, rgb.g, rgb.b]
            })
        });
        
        document.getElementById('color-picker-modal').style.display = 'none';
        await loadLights();
    } catch (error) {
        console.error('Failed to apply color:', error);
    }
}

// Effects Management
function renderEffects(effects) {
    const grid = document.getElementById('effects-grid');
    grid.innerHTML = '';
    
    const effectDescriptions = {
        rainbow: 'Smooth rainbow cycle',
        color_loop: 'Loop through colors',
        twinkle: 'Random twinkling',
        fire: 'Flickering fire effect',
        christmas: 'Red and green alternating',
        halloween: 'Orange and purple spooky',
        strobe: 'Fast strobe effect',
        breathe: 'Gentle breathing'
    };
    
    effects.forEach(effect => {
        const card = document.createElement('div');
        card.className = 'effect-card';
        card.innerHTML = `
            <div class="effect-name">${effect.name.toUpperCase()}</div>
            <div class="effect-description">${effectDescriptions[effect.name]}</div>
        `;
        
        card.addEventListener('click', () => startEffect(effect.name));
        grid.appendChild(card);
    });
}

async function startEffect(effectName) {
    if (selectedLights.size === 0) {
        alert('Please select at least one light');
        return;
    }
    
    const params = {};
    
    // Get effect-specific parameters
    if (effectName === 'strobe' || effectName === 'breathe') {
        const colorHex = prompt('Enter color (hex):', '#ffffff');
        if (colorHex) {
            const rgb = hexToRgb(colorHex);
            params.color = [rgb.r, rgb.g, rgb.b];
        }
    }
    
    try {
        await fetch(`/api/effects/${effectName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                light_ids: Array.from(selectedLights),
                params: params
            })
        });
        
        alert(`Effect ${effectName} started!`);
    } catch (error) {
        console.error('Failed to start effect:', error);
    }
}

async function stopAllEffects() {
    try {
        await fetch('/api/effects/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
    } catch (error) {
        console.error('Failed to stop effects:', error);
    }
}

// Scenes Management
function renderScenes(scenes) {
    const grid = document.getElementById('scenes-grid');
    grid.innerHTML = '';
    
    scenes.forEach(scene => {
        const card = document.createElement('div');
        card.className = 'scene-card';
        
        let preview = '';
        if (scene.effect) {
            preview = `<div class="scene-preview">Effect: ${scene.effect}</div>`;
        } else if (scene.lights) {
            const colors = scene.lights.slice(0, 5).map(l => {
                const rgb = l.rgb || [255, 255, 255];
                return `<div class="scene-color" style="background: rgb(${rgb.join(',')})"></div>`;
            }).join('');
            preview = `<div class="scene-preview">${colors}</div>`;
        }
        
        card.innerHTML = `
            <div class="scene-name">${scene.name}</div>
            ${preview}
        `;
        
        card.addEventListener('click', () => applyScene(scene.name));
        grid.appendChild(card);
    });
}

async function applyScene(sceneName) {
    try {
        await fetch(`/api/scenes/${sceneName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        await loadLights();
    } catch (error) {
        console.error('Failed to apply scene:', error);
    }
}

function createScene() {
    alert('Scene creation UI coming soon!');
}

// Controllers Management
function renderControllers() {
    const grid = document.getElementById('controllers-grid');
    grid.innerHTML = '';
    
    controllers.forEach(controller => {
        const card = document.createElement('div');
        card.className = 'controller-card';
        
        card.innerHTML = `
            <div class="controller-status">
                <span class="status-indicator online"></span>
                <strong>${controller.name}</strong>
            </div>
            <div class="controller-info">
                <div>IP: ${controller.ip}</div>
                <div>MAC: ${controller.mac || 'N/A'}</div>
                <div>Location: (${controller.location?.x || 0}, ${controller.location?.y || 0})</div>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

function addController() {
    alert('Add controller UI coming soon!');
}

// Map Functions
function initMap() {
    const lat = config.map_latitude || 0;
    const lon = config.map_longitude || 0;
    const zoom = config.map_zoom || 18;
    
    map = L.map('map').setView([lat, lon], zoom);
    
    // Use ESRI ArcGIS satellite imagery (free, no API key required)
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '© ESRI, Earthstar Geographics'
    });
    
    // ESRI street map layer
    const streetLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '© ESRI'
    });
    
    // Add satellite by default
    satelliteLayer.addTo(map);
    
    // Layer control to switch between views
    const baseMaps = {
        "Satellite": satelliteLayer,
        "Street Map": streetLayer
    };
    
    L.control.layers(baseMaps).addTo(map);
}

function updateMapMarkers() {
    // Clear existing markers
    Object.values(lightMarkers).forEach(marker => map.removeLayer(marker));
    Object.values(controllerMarkers).forEach(marker => map.removeLayer(marker));
    lightMarkers = {};
    controllerMarkers = {};
    
    // Add light markers
    lights.forEach(light => {
        if (light.location?.x !== null && light.location?.y !== null) {
            const marker = L.marker([light.location.y, light.location.x], {
                draggable: true,
                icon: L.divIcon({
                    className: 'light-marker',
                    html: '💡',
                    iconSize: [30, 30]
                })
            }).addTo(map);
            
            marker.bindPopup(`<b>${light.name}</b><br>ID: ${light.id}`);
            
            marker.on('dragend', async (e) => {
                const pos = e.target.getLatLng();
                await updateLightLocation(light.id, pos.lng, pos.lat);
            });
            
            lightMarkers[light.id] = marker;
        }
    });
    
    // Add controller markers
    if (document.getElementById('show-controllers')?.checked) {
        controllers.forEach(controller => {
            if (controller.location?.x !== null && controller.location?.y !== null) {
                const marker = L.marker([controller.location.y, controller.location.x], {
                    icon: L.divIcon({
                        className: 'controller-marker',
                        html: '📡',
                        iconSize: [40, 40]
                    })
                }).addTo(map);
                
                marker.bindPopup(`<b>${controller.name}</b><br>IP: ${controller.ip}`);
                
                controllerMarkers[controller.name] = marker;
            }
        });
    }
}

async function updateLightLocation(lightId, x, y) {
    try {
        await fetch(`/api/lights/${lightId}/location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x, y })
        });
    } catch (error) {
        console.error('Failed to update light location:', error);
    }
}

async function saveLayout() {
    alert('Layout saved successfully!');
}

// Utility Functions
function rgbToHex(r, g, b) {
    return '#' + [r, g, b].map(x => {
        const hex = Math.round(x).toString(16);
        return hex.length === 1 ? '0' + hex : hex;
    }).join('');
}

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : { r: 255, g: 255, b: 255 };
}

async function scanForLights() {
    try {
        const response = await fetch('/api/scan', { method: 'POST' });
        const result = await response.json();
        alert(`Found ${result.lights?.length || 0} new lights`);
        await loadLights();
    } catch (error) {
        console.error('Failed to scan for lights:', error);
    }
}

async function refreshAll() {
    await loadLights();
    await loadControllers();
}

// Settings Management
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        // Core settings
        document.getElementById('mesh-key').value = settings.mesh_key || '';
        
        // MQTT settings
        document.getElementById('use-addon-mqtt').checked = settings.use_addon_mqtt !== false;
        toggleCustomMQTT();
        if (!settings.use_addon_mqtt) {
            document.getElementById('mqtt-host').value = settings.mqtt_host || '';
            document.getElementById('mqtt-port').value = settings.mqtt_port || 1883;
            document.getElementById('mqtt-user').value = settings.mqtt_user || '';
            document.getElementById('mqtt-password').value = settings.mqtt_password || '';
        }
        
        // Map settings
        document.getElementById('map-enabled').checked = settings.map_enabled !== false;
        document.getElementById('map-latitude').value = settings.latitude || 0;
        document.getElementById('map-longitude').value = settings.longitude || 0;
        document.getElementById('map-zoom').value = settings.zoom || 18;
        updateZoomDisplay();
        
        // Feature toggles
        document.getElementById('discovery-enabled').checked = settings.discovery_enabled !== false;
        document.getElementById('generate-esphome').checked = settings.generate_esphome !== false;
        document.getElementById('enable-ble').checked = settings.enable_ble !== false;
        document.getElementById('enable-nspanel').checked = settings.enable_nspanel || false;
        toggleNSPanelSettings();
        if (settings.enable_nspanel) {
            document.getElementById('nspanel-entity').value = settings.nspanel_entity_id || '';
        }
        
        // Import/export
        document.getElementById('app-config-path').value = settings.app_config_path || '/share/brmesh_export.json';
        
    } catch (error) {
        console.error('Failed to load settings:', error);
        showNotification('Failed to load settings', 'error');
    }
}

async function saveSettings() {
    try {
        const settings = {
            mesh_key: document.getElementById('mesh-key').value,
            use_addon_mqtt: document.getElementById('use-addon-mqtt').checked,
            mqtt_host: document.getElementById('mqtt-host').value,
            mqtt_port: parseInt(document.getElementById('mqtt-port').value),
            mqtt_user: document.getElementById('mqtt-user').value,
            mqtt_password: document.getElementById('mqtt-password').value,
            map_enabled: document.getElementById('map-enabled').checked,
            latitude: parseFloat(document.getElementById('map-latitude').value),
            longitude: parseFloat(document.getElementById('map-longitude').value),
            zoom: parseInt(document.getElementById('map-zoom').value),
            discovery_enabled: document.getElementById('discovery-enabled').checked,
            generate_esphome: document.getElementById('generate-esphome').checked,
            enable_ble: document.getElementById('enable-ble').checked,
            enable_nspanel: document.getElementById('enable-nspanel').checked,
            nspanel_entity_id: document.getElementById('nspanel-entity').value,
            app_config_path: document.getElementById('app-config-path').value
        };
        
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            showNotification('Settings saved successfully! Restarting add-on...', 'success');
            // Restart add-on to apply changes
            setTimeout(() => location.reload(), 3000);
        } else {
            throw new Error('Failed to save settings');
        }
    } catch (error) {
        console.error('Failed to save settings:', error);
        showNotification('Failed to save settings', 'error');
    }
}

function toggleCustomMQTT() {
    const useAddonMQTT = document.getElementById('use-addon-mqtt').checked;
    document.getElementById('custom-mqtt-settings').style.display = useAddonMQTT ? 'none' : 'block';
}

function toggleNSPanelSettings() {
    const enableNSPanel = document.getElementById('enable-nspanel').checked;
    document.getElementById('nspanel-settings').style.display = enableNSPanel ? 'block' : 'none';
}

function updateZoomDisplay() {
    const zoom = document.getElementById('map-zoom').value;
    document.getElementById('zoom-value').textContent = zoom;
}

async function resetSettings() {
    if (!confirm('Reset all settings to defaults? This will restart the add-on.')) return;
    
    try {
        const response = await fetch('/api/settings/reset', { method: 'POST' });
        if (response.ok) {
            showNotification('Settings reset! Restarting...', 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            throw new Error('Failed to reset settings');
        }
    } catch (error) {
        console.error('Failed to reset settings:', error);
        showNotification('Failed to reset settings', 'error');
    }
}

async function importFromApp() {
    try {
        const response = await fetch('/api/settings/import-app', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            showNotification(`Imported ${result.lights_imported || 0} lights from BRMesh app`, 'success');
            loadSettings();
            loadLights();
        } else {
            throw new Error(result.error || 'Import failed');
        }
    } catch (error) {
        console.error('Failed to import from app:', error);
        showNotification('Failed to import from app: ' + error.message, 'error');
    }
}

async function exportConfig() {
    try {
        const response = await fetch('/api/settings/export');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'brmesh_config.json';
        a.click();
        window.URL.revokeObjectURL(url);
        showNotification('Configuration exported', 'success');
    } catch (error) {
        console.error('Failed to export config:', error);
        showNotification('Failed to export configuration', 'error');
    }
}

// Event listeners for settings
document.addEventListener('DOMContentLoaded', () => {
    const useMqttCheckbox = document.getElementById('use-addon-mqtt');
    const nspanelCheckbox = document.getElementById('enable-nspanel');
    const zoomSlider = document.getElementById('map-zoom');
    const saveBtn = document.getElementById('save-settings-btn');
    const resetBtn = document.getElementById('reset-settings-btn');
    
    if (useMqttCheckbox) useMqttCheckbox.addEventListener('change', toggleCustomMQTT);
    if (nspanelCheckbox) nspanelCheckbox.addEventListener('change', toggleNSPanelSettings);
    if (zoomSlider) zoomSlider.addEventListener('input', updateZoomDisplay);
    if (saveBtn) saveBtn.addEventListener('click', saveSettings);
    if (resetBtn) resetBtn.addEventListener('click', resetSettings);
});
