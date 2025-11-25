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
    setupDarkMode();
    await loadConfig();
    
    // Check if mesh key is configured, if not, default to settings tab
    if (!config.mesh_key || config.mesh_key.trim() === '') {
        // Switch to settings tab
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('.tab-btn[data-tab="settings"]').classList.add('active');
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById('settings-tab').classList.add('active');
        loadSettings();
        loadWiFiNetworks();
        showNotification('⚠️ Please configure your mesh key in Settings to get started', 'warning');
    }
    
    await loadLights();
    await loadControllers();
    await loadEffects();
    await loadScenes();
    initMap();
    
    // Setup event listeners
    document.getElementById('import-app-btn').addEventListener('click', importFromAppHeader);
    document.getElementById('scan-btn').addEventListener('click', scanForLights);
    document.getElementById('refresh-btn').addEventListener('click', refreshAll);
    document.getElementById('save-layout-btn').addEventListener('click', saveLayout);
    document.getElementById('create-scene-btn').addEventListener('click', createScene);
    document.getElementById('create-controller-btn').addEventListener('click', createController);
    document.getElementById('add-controller-btn').addEventListener('click', addExistingController);
    document.getElementById('dark-mode-toggle').addEventListener('click', toggleDarkMode);
    
    // Mesh key visibility toggle
    document.getElementById('toggle-mesh-key').addEventListener('click', () => {
        const input = document.getElementById('mesh-key');
        const button = document.getElementById('toggle-mesh-key');
        if (input.type === 'password') {
            input.type = 'text';
            button.textContent = '🙈';
        } else {
            input.type = 'password';
            button.textContent = '👁️';
        }
    });
    
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
                loadWiFiNetworks();
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
        const response = await fetch('api/config');
        config = await response.json();
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

async function loadLights() {
    try {
        const response = await fetch('api/lights');
        lights = await response.json();
        // Ensure all lights have valid location objects
        lights = lights.map(light => ({
            ...light,
            location: light.location || { x: null, y: null }
        }));
        renderLights();
        renderLightSelectors();
        updateMapMarkers();
    } catch (error) {
        console.error('Failed to load lights:', error);
    }
}

async function loadControllers() {
    try {
        const response = await fetch('api/controllers');
        controllers = await response.json();
        // Ensure all controllers have valid location objects
        controllers = controllers.map(controller => ({
            ...controller,
            location: controller.location || { x: null, y: null }
        }));
        renderControllers();
        updateMapMarkers();
    } catch (error) {
        console.error('Failed to load controllers:', error);
    }
}

async function loadEffects() {
    try {
        const response = await fetch('api/effects');
        const effects = await response.json();
        renderEffects(effects);
    } catch (error) {
        console.error('Failed to load effects:', error);
    }
}

async function loadScenes() {
    try {
        const response = await fetch('api/scenes');
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
        await fetch('api/effects/stop', {
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
    // Create modal for scene creation
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <h2>Create New Scene</h2>
            <div class="form-group">
                <label for="scene-name">Scene Name:</label>
                <input type="text" id="scene-name" placeholder="e.g., Christmas, Movie Night, Party Mode" />
            </div>
            <div class="form-group">
                <label>Scene Type:</label>
                <select id="scene-type">
                    <option value="static">Static Colors</option>
                    <option value="effect">Effect Pattern</option>
                </select>
            </div>
            <div id="scene-static-config" class="form-group">
                <h3>Select Lights & Colors</h3>
                <div id="scene-lights-list"></div>
            </div>
            <div id="scene-effect-config" class="form-group" style="display: none;">
                <label for="scene-effect">Effect:</label>
                <select id="scene-effect">
                    <option value="rainbow">Rainbow</option>
                    <option value="chase">Chase</option>
                    <option value="twinkle">Twinkle</option>
                    <option value="pulse">Pulse</option>
                    <option value="fade">Fade</option>
                </select>
            </div>
            <div class="modal-buttons">
                <button class="btn btn-primary" onclick="saveScene()">💾 Save Scene</button>
                <button class="btn btn-secondary" onclick="this.parentElement.parentElement.parentElement.remove()">Cancel</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Populate lights list
    const lightsList = document.getElementById('scene-lights-list');
    lights.forEach(light => {
        const lightDiv = document.createElement('div');
        lightDiv.className = 'scene-light-item';
        const currentColor = light.state.rgb || [255, 255, 255];
        const colorHex = rgbToHex(currentColor[0], currentColor[1], currentColor[2]);
        
        lightDiv.innerHTML = `
            <label>
                <input type="checkbox" class="scene-light-checkbox" data-light-id="${light.id}" checked />
                ${light.name}
            </label>
            <input type="color" class="scene-light-color" data-light-id="${light.id}" value="${colorHex}" />
        `;
        lightsList.appendChild(lightDiv);
    });
    
    // Handle scene type change
    document.getElementById('scene-type').addEventListener('change', (e) => {
        const isEffect = e.target.value === 'effect';
        document.getElementById('scene-static-config').style.display = isEffect ? 'none' : 'block';
        document.getElementById('scene-effect-config').style.display = isEffect ? 'block' : 'none';
    });
}

async function saveScene() {
    const name = document.getElementById('scene-name').value.trim();
    if (!name) {
        showNotification('Please enter a scene name', 'error');
        return;
    }
    
    const sceneType = document.getElementById('scene-type').value;
    const sceneData = { name, type: sceneType };
    
    if (sceneType === 'static') {
        sceneData.lights = [];
        document.querySelectorAll('.scene-light-checkbox:checked').forEach(checkbox => {
            const lightId = parseInt(checkbox.dataset.lightId);
            const colorInput = document.querySelector(`.scene-light-color[data-light-id="${lightId}"]`);
            const color = hexToRgb(colorInput.value);
            sceneData.lights.push({ id: lightId, rgb: color, brightness: 255 });
        });
    } else {
        sceneData.effect = document.getElementById('scene-effect').value;
    }
    
    try {
        const response = await fetch('api/scenes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sceneData)
        });
        
        if (response.ok) {
            showNotification('Scene created successfully!', 'success');
            document.querySelector('.modal').remove();
            await loadScenes();
        } else {
            showNotification('Failed to create scene', 'error');
        }
    } catch (error) {
        console.error('Failed to create scene:', error);
        showNotification('Failed to create scene: ' + error.message, 'error');
    }
}

// Controllers Management
function renderControllers() {
    const grid = document.getElementById('controllers-grid');
    grid.innerHTML = '';
    
    controllers.forEach(controller => {
        const card = document.createElement('div');
        card.className = 'controller-card';
        
        const controllerName = controller.name.toLowerCase().replace(/ /g, '-');
        
        card.innerHTML = `
            <div class="controller-status">
                <strong>${controller.name}</strong>
            </div>
            <div class="controller-info">
                <div>IP: ${controller.ip}</div>
                <div>MAC: ${controller.mac || 'N/A'}</div>
                <div>Location: (${controller.location?.x || 0}, ${controller.location?.y || 0})</div>
            </div>
            <div class="controller-actions">
                <button class="btn btn-primary" onclick="buildFirmware('${controllerName}')">🔨 Build</button>
                <button class="btn btn-success" onclick="flashFirmware('${controllerName}')">⚡ Flash</button>
                <button class="btn btn-secondary" onclick="buildAndFlash('${controllerName}')">🚀 Build & Flash</button>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

async function createController() {
    // Load WiFi networks first
    let wifiNetworks = [];
    try {
        const response = await fetch('api/wifi-networks');
        const data = await response.json();
        // Extract networks array from response
        wifiNetworks = data.networks || [];
    } catch (error) {
        console.error('Failed to load WiFi networks:', error);
        wifiNetworks = [];
    }
    
    // Build network selector options using the id from the network object
    const networkOptions = wifiNetworks.map((net) => 
        `<option value="${net.id}">📶 ${net.ssid}</option>`
    ).join('');
    
    // Create modal for building a new ESP32 from scratch
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <h2>🔨 Create New ESP32 Controller</h2>
            <p>Build and flash a new ESP32 controller. Just provide your WiFi credentials and we'll handle the rest!</p>
            
            <div class="form-group">
                <label for="wifi-network-selector">WiFi Network: <span style="color: red;">*</span></label>
                <select id="wifi-network-selector" onchange="toggleWiFiInputs()">
                    <option value="new">➕ Enter New Network</option>
                    ${networkOptions}
                </select>
            </div>
            
            <div id="wifi-manual-inputs" ${networkOptions ? 'style="display:none;"' : ''}>
                <div class="form-group">
                    <label for="wifi-ssid">WiFi SSID: <span style="color: red;">*</span></label>
                    <input type="text" id="wifi-ssid" placeholder="Your WiFi Network Name" required />
                </div>
                
                <div class="form-group">
                    <label for="wifi-password">WiFi Password: <span style="color: red;">*</span></label>
                    <input type="password" id="wifi-password" placeholder="Your WiFi Password" required />
                    <small>Stored securely in /config/secrets.yaml</small>
                </div>
            </div>
            
            <div class="form-group">
                <label for="controller-name">Controller Name (optional):</label>
                <input type="text" id="controller-name" placeholder="Leave blank to auto-generate (brmesh_bridge, brmesh_bridge_1, etc.)" />
                <small>Auto-generated if not specified</small>
            </div>
            
            <div class="info-box">
                <strong>What happens next:</strong>
                <ol>
                    <li>Controller config and WiFi secrets are generated automatically</li>
                    <li>Firmware compiles (takes 5-10 minutes first time)</li>
                    <li>Connect your ESP32 via USB</li>
                    <li>Click "Flash" to upload firmware</li>
                    <li>Your ESP32 connects to WiFi and appears in Home Assistant!</li>
                </ol>
                <p><small>💡 Name, IP, and location can be configured later in the Controllers tab.</small></p>
            </div>
            
            <div class="modal-buttons">
                <button class="btn btn-success" onclick="saveControllerAndBuild()">🔨 Create & Build Firmware</button>
                <button class="btn btn-secondary" onclick="this.parentElement.parentElement.parentElement.remove()">Cancel</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Show/hide manual inputs initially
    toggleWiFiInputs();
}

function toggleWiFiInputs() {
    const selector = document.getElementById('wifi-network-selector');
    const manualInputs = document.getElementById('wifi-manual-inputs');
    if (selector && manualInputs) {
        manualInputs.style.display = selector.value === 'new' ? 'block' : 'none';
    }
}

function addExistingController() {
    // Create modal for adding an already-configured ESP32
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <h2>➕ Add Existing Controller</h2>
            <p>Add an ESP32 controller that is already configured and running ESPHome firmware.</p>
            
            <div class="form-group">
                <label for="controller-name">Controller Name:</label>
                <input type="text" id="controller-name" placeholder="e.g., Front Yard, Backyard, Garage" />
            </div>
            
            <div class="form-group">
                <label for="controller-ip">Controller IP Address:</label>
                <input type="text" id="controller-ip" placeholder="192.168.1.100" />
                <small>Leave blank for auto-discovery</small>
            </div>
            
            <div class="form-group">
                <label for="controller-mac">MAC Address (Optional):</label>
                <input type="text" id="controller-mac" placeholder="AA:BB:CC:DD:EE:FF" />
            </div>
            
            <div class="form-group">
                <h3>Location (for signal optimization)</h3>
                <label for="controller-lat">Latitude:</label>
                <input type="number" id="controller-lat" step="0.000001" placeholder="41.0199" value="${config.map_latitude || ''}" />
                <label for="controller-lon">Longitude:</label>
                <input type="number" id="controller-lon" step="0.000001" placeholder="-73.8286" value="${config.map_longitude || ''}" />
                <small>Click on the map to set location automatically</small>
            </div>
            
            <div class="modal-buttons">
                <button class="btn btn-primary" onclick="saveController()">💾 Add Controller</button>
                <button class="btn btn-secondary" onclick="this.parentElement.parentElement.parentElement.remove()">Cancel</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

async function saveController() {
    const name = document.getElementById('controller-name').value.trim();
    const ip = document.getElementById('controller-ip').value.trim();
    const mac = document.getElementById('controller-mac').value.trim();
    const lat = parseFloat(document.getElementById('controller-lat').value);
    const lon = parseFloat(document.getElementById('controller-lon').value);
    
    if (!name) {
        showNotification('Please enter a controller name', 'error');
        return;
    }
    
    // Default to HA instance location if not specified
    let location;
    if (lat && lon && !isNaN(lat) && !isNaN(lon)) {
        location = { x: lon, y: lat };
    } else if (config.map_latitude && config.map_longitude) {
        location = { x: config.map_longitude, y: config.map_latitude };
    } else {
        location = { x: 0, y: 0 };
    }
    
    const controllerData = {
        name,
        ip: ip || null,
        mac: mac || null,
        generate_esphome: false,  // Existing controller, no config generation
        location
    };
    
    try {
        const response = await fetch('api/controllers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(controllerData)
        });
        
        if (response.ok) {
            showNotification('Controller added successfully!', 'success');
            document.querySelector('.modal').remove();
            await loadControllers();
        } else {
            const error = await response.json();
            showNotification('Failed to add controller: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to add controller:', error);
        showNotification('Failed to add controller: ' + error.message, 'error');
    }
}

async function saveControllerAndBuild() {
    const networkSelector = document.getElementById('wifi-network-selector');
    const selectedNetwork = networkSelector.value;
    const name = document.getElementById('controller-name').value.trim();
    
    let wifiSsid, wifiPassword, networkId;
    
    if (selectedNetwork === 'new') {
        // Using manual WiFi credentials
        wifiSsid = document.getElementById('wifi-ssid')?.value.trim();
        wifiPassword = document.getElementById('wifi-password')?.value.trim();
        
        // Validate WiFi credentials
        if (!wifiSsid) {
            showNotification('Please enter your WiFi SSID', 'error');
            return;
        }
        
        if (!wifiPassword) {
            showNotification('Please enter your WiFi password', 'error');
            return;
        }
        
        networkId = null;
    } else {
        // Using pre-configured network
        networkId = parseInt(selectedNetwork);
        wifiSsid = null;
        wifiPassword = null;
    }
    
    const controllerData = {
        name: name || null,  // Auto-generate if empty
        wifi_ssid: wifiSsid,
        wifi_password: wifiPassword,
        network_id: networkId,
        generate_esphome: true,  // Generate config for new controller
        location: null  // Will be set later
    };
    
    try {
        showNotification('🔨 Creating controller and generating configuration...', 'info');
        
        const response = await fetch('api/controllers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(controllerData)
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`✅ Controller "${result.name}" created and config generated!`, 'success');
            document.querySelector('.modal').remove();
            await loadControllers();
            
            // Automatically start building firmware
            if (result.esphome_path) {
                showNotification('🔨 Starting firmware build... This will take 5-10 minutes.', 'info');
                await buildFirmware(result.name);
            }
        } else {
            const error = await response.json();
            showNotification('Failed to create controller: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to create controller:', error);
        showNotification('Failed to create controller: ' + error.message, 'error');
    }
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
    // Check if map is initialized
    if (!map) {
        return;
    }
    
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
                    draggable: true,
                    icon: L.divIcon({
                        className: 'controller-marker',
                        html: '📡',
                        iconSize: [40, 40]
                    })
                }).addTo(map);
                
                marker.bindPopup(`<b>${controller.name}</b><br>IP: ${controller.ip}`);
                
                marker.on('dragend', async (e) => {
                    const pos = e.target.getLatLng();
                    await updateControllerLocation(controller.id, pos.lng, pos.lat);
                });
                
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

async function updateControllerLocation(controllerId, x, y) {
    try {
        await fetch(`api/controllers/${controllerId}/location`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x, y })
        });
        showNotification('Controller location updated', 'success');
    } catch (error) {
        console.error('Failed to update controller location:', error);
        showNotification('Failed to update controller location', 'error');
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
    const scanBtn = document.getElementById('scan-btn');
    const originalText = scanBtn.textContent;
    
    try {
        // Show progress
        scanBtn.disabled = true;
        scanBtn.textContent = '🔍 Scanning... (30s)';
        showNotification('Scanning for BRMesh lights... This will take 30 seconds.', 'info');
        
        const response = await fetch('api/scan', { method: 'POST' });
        const result = await response.json();
        
        if (result.error) {
            showNotification(`Scan failed: ${result.error}`, 'error');
        } else {
            showNotification(`Found ${result.count || 0} new lights!`, result.count > 0 ? 'success' : 'info');
            if (result.count > 0) {
                await loadLights();
            }
        }
    } catch (error) {
        console.error('Failed to scan for lights:', error);
        showNotification('Scan failed. Check add-on logs for details.', 'error');
    } finally {
        scanBtn.disabled = false;
        scanBtn.textContent = originalText;
    }
}

async function refreshAll() {
    await loadLights();
    await loadControllers();
}

// Settings Management
async function loadSettings() {
    try {
        const response = await fetch('api/settings');
        const settings = await response.json();
        
        // Core settings
        document.getElementById('mesh-key').value = settings.mesh_key || '';
        
        // MQTT settings
        document.getElementById('use-addon-mqtt').checked = settings.use_addon_mqtt !== false;
        toggleMQTTSection();
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
        
        const response = await fetch('api/settings', {
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

function toggleMQTTSection() {
    const useAddonMQTT = document.getElementById('use-addon-mqtt').checked;
    const section = document.getElementById('custom-mqtt-section');
    if (section) section.style.display = useAddonMQTT ? 'none' : 'block';
}

function toggleNSPanelSettings() {
    const enableNSPanel = document.getElementById('enable-nspanel').checked;
    document.getElementById('nspanel-settings').style.display = enableNSPanel ? 'block' : 'none';
}

function toggleMapSettings() {
    const mapEnabled = document.getElementById('map-enabled').checked;
    document.getElementById('map-settings-fields').style.display = mapEnabled ? 'block' : 'none';
}

// WiFi Network Management
async function loadWiFiNetworks() {
    try {
        const response = await fetch('api/wifi-networks');
        const data = await response.json();
        const networks = data.networks || [];
        
        const list = document.getElementById('wifi-networks-list');
        if (!networks || networks.length === 0) {
            list.innerHTML = '<p>No WiFi networks configured. Add one to easily reuse credentials when creating controllers.</p>';
            return;
        }
        
        list.innerHTML = networks
            .filter(net => net.id >= 0)  // Skip legacy network ID (-1)
            .map((net) => `
            <div class="wifi-network-item" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px;">
                <div>
                    <strong>📶 ${net.ssid}</strong>
                    ${net.is_default ? '<span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; margin-left: 8px;">DEFAULT</span>' : ''}
                    <br>
                    <small>Network ID: ${net.id}</small>
                </div>
                <div style="display: flex; gap: 8px;">
                    ${!net.is_default ? `<button class="btn btn-primary btn-sm" onclick="setDefaultWiFiNetwork(${net.id})">⭐ Set Default</button>` : ''}
                    <button class="btn btn-danger btn-sm" onclick="deleteWiFiNetwork(${net.id})">🗑️ Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load WiFi networks:', error);
        showNotification('Failed to load WiFi networks', 'error');
    }
}

function addWiFiNetworkDialog() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <h2>➕ Add WiFi Network</h2>
            <p>Add WiFi credentials to reuse when creating controllers.</p>
            
            <div class="form-group">
                <label for="new-wifi-ssid">WiFi SSID:</label>
                <input type="text" id="new-wifi-ssid" placeholder="Network Name" required />
            </div>
            
            <div class="form-group">
                <label for="new-wifi-password">WiFi Password:</label>
                <input type="password" id="new-wifi-password" placeholder="Password" required />
            </div>
            
            <div class="modal-buttons">
                <button class="btn btn-success" onclick="saveWiFiNetwork()">💾 Save Network</button>
                <button class="btn btn-secondary" onclick="this.parentElement.parentElement.parentElement.remove()">Cancel</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

async function saveWiFiNetwork() {
    const ssid = document.getElementById('new-wifi-ssid').value.trim();
    const password = document.getElementById('new-wifi-password').value.trim();
    
    if (!ssid || !password) {
        showNotification('Please enter both SSID and password', 'error');
        return;
    }
    
    try {
        const response = await fetch('api/wifi-networks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ssid, password })
        });
        
        if (response.ok) {
            showNotification('✅ WiFi network saved!', 'success');
            document.querySelector('.modal').remove();
            await loadWiFiNetworks();
        } else {
            const error = await response.json();
            showNotification('Failed to save network: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to save WiFi network:', error);
        showNotification('Failed to save WiFi network: ' + error.message, 'error');
    }
}

async function setDefaultWiFiNetwork(index) {
    try {
        const response = await fetch(`api/wifi-networks/${index}/set-default`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification('✅ WiFi network set as default', 'success');
            await loadWiFiNetworks();
        } else {
            const error = await response.json();
            showNotification('Failed to set default: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to set default WiFi network:', error);
        showNotification('Failed to set default: ' + error.message, 'error');
    }
}

async function deleteWiFiNetwork(index) {
    if (!confirm('Delete this WiFi network?')) return;
    
    try {
        const response = await fetch(`api/wifi-networks/${index}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('✅ WiFi network deleted', 'success');
            await loadWiFiNetworks();
        } else {
            const error = await response.json();
            showNotification('Failed to delete network: ' + (error.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to delete WiFi network:', error);
        showNotification('Failed to delete WiFi network: ' + error.message, 'error');
    }
}

async function testGitConnectivity() {
    const resultsDiv = document.getElementById('git-test-results');
    resultsDiv.style.display = 'block';
    resultsDiv.textContent = '🔄 Testing git and GitHub connectivity... This may take up to 60 seconds...';
    
    try {
        const response = await fetch('api/diagnostics/git-test');
        const results = await response.json();
        
        let output = '=== Git/GitHub Connectivity Test Results ===\n\n';
        
        output += '1. Git Version:\n' + results.git_version + '\n\n';
        output += '2. Git Configuration:\n' + results.git_config + '\n\n';
        output += '3. DNS Resolution (github.com):\n' + results.dns_github + '\n\n';
        output += '4. Repository Clone Test:\n';
        
        if (typeof results.clone_test === 'string') {
            output += results.clone_test;
        } else {
            output += 'Success: ' + results.clone_test.success + '\n';
            output += 'Return Code: ' + results.clone_test.returncode + '\n';
            output += 'STDOUT:\n' + results.clone_test.stdout + '\n';
            output += 'STDERR:\n' + results.clone_test.stderr;
        }
        
        resultsDiv.textContent = output;
        
        if (typeof results.clone_test === 'object' && results.clone_test.success) {
            showNotification('✅ Git/GitHub connectivity test passed!', 'success');
        } else {
            showNotification('⚠️ Git/GitHub connectivity test failed. Check results below.', 'warning');
        }
    } catch (error) {
        console.error('Failed to run git test:', error);
        resultsDiv.textContent = 'Error running test: ' + error.message;
        showNotification('Failed to run git test: ' + error.message, 'error');
    }
}

function updateZoomDisplay() {
    const zoom = document.getElementById('map-zoom').value;
    document.getElementById('zoom-value').textContent = zoom;
}

async function resetSettings() {
    if (!confirm('Reset all settings to defaults? This will restart the add-on.')) return;
    
    try {
        const response = await fetch('api/settings/reset', { method: 'POST' });
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
        const response = await fetch('api/settings/import-app', { method: 'POST' });
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

// Header button version with instructions
async function importFromAppHeader() {
    const instructions = 'This will import lights and mesh key from your BRMesh app export.\n\n' +
                        '1. Open BRMesh app on your phone\n' +
                        '2. Export configuration to a file\n' +
                        '3. Copy the file to Home Assistant at: /share/brmesh_export.json\n' +
                        '4. Click OK to import\n\n' +
                        'Continue?';
    
    if (!confirm(instructions)) return;
    
    try {
        showNotification('Importing from BRMesh app...', 'info');
        const response = await fetch('api/settings/import-app', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            const message = `✅ Import successful!\n\n` +
                          `Lights: ${result.lights_imported || 0}\n` +
                          `Mesh Key: ${result.mesh_key ? '✓ Updated' : '⚠ Not found'}\n\n` +
                          `The add-on will now reload with your settings.`;
            showNotification(message, 'success');
            
            // Reload after a delay
            setTimeout(() => {
                location.reload();
            }, 3000);
        } else {
            throw new Error(result.error || 'Import failed');
        }
    } catch (error) {
        console.error('Failed to import from app:', error);
        showNotification('❌ Import failed: ' + error.message + '\n\nMake sure the export file is at /share/brmesh_export.json', 'error');
    }
}

async function exportConfig() {
    try {
        const response = await fetch('api/settings/export');
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

// Show notification banner
function showNotification(message, type = 'info') {
    // Create notification element if it doesn't exist
    let notification = document.getElementById('notification-banner');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification-banner';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            max-width: 400px;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            font-size: 14px;
            font-weight: 500;
            animation: slideIn 0.3s ease-out;
        `;
        document.body.appendChild(notification);
    }
    
    // Set color based on type
    const colors = {
        success: '#4caf50',
        error: '#f44336',
        warning: '#ff9800',
        info: '#2196f3'
    };
    
    notification.style.backgroundColor = colors[type] || colors.info;
    notification.style.color = 'white';
    notification.textContent = message;
    notification.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.style.display = 'none';
    }, 5000);
}

// ESP32 Build & Flash Functions
async function buildFirmware(controllerName, eventOrButton = null) {
    // Handle both event-based (button click) and programmatic calls
    const buildBtn = eventOrButton?.target || eventOrButton;
    const originalText = buildBtn?.textContent;
    
    try {
        if (buildBtn) {
            buildBtn.disabled = true;
            buildBtn.textContent = '🔨 Building...';
        }
        showNotification(`Building firmware for ${controllerName}... This may take 5-10 minutes.`, 'info');
        
        const response = await fetch(`api/esphome/build/${controllerName}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`✅ Firmware built successfully! Ready to flash.`, 'success');
        } else {
            showNotification(`❌ Build failed: ${result.error}`, 'error');
            console.error('Build output:', result.output);
        }
    } catch (error) {
        console.error('Build error:', error);
        showNotification(`❌ Build failed: ${error.message}`, 'error');
    } finally {
        if (buildBtn) {
            buildBtn.disabled = false;
            buildBtn.textContent = originalText;
        }
    }
}

async function flashFirmware(controllerName, eventOrButton = null) {
    // Handle both event-based (button click) and programmatic calls
    const flashBtn = eventOrButton?.target || eventOrButton;
    const originalText = flashBtn?.textContent;
    
    try {
        // Get available serial ports
        const portsResponse = await fetch('api/esphome/ports');
        const portsData = await portsResponse.json();
        
        let port = 'auto';
        if (portsData.ports && portsData.ports.length > 0) {
            // Show port selection dialog
            port = await showPortSelectionDialog(portsData.ports);
            if (!port) return; // User cancelled
        }
        
        if (flashBtn) {
            flashBtn.disabled = true;
            flashBtn.textContent = '⚡ Flashing...';
        }
        showNotification(`Flashing firmware to ${controllerName}... Keep ESP32 connected!`, 'info');
        
        const response = await fetch(`api/esphome/flash/${controllerName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`✅ Firmware flashed successfully! ESP32 is rebooting.`, 'success');
        } else {
            showNotification(`❌ Flash failed: ${result.error}`, 'error');
            console.error('Flash output:', result.output);
        }
    } catch (error) {
        console.error('Flash error:', error);
        showNotification(`❌ Flash failed: ${error.message}`, 'error');
    } finally {
        if (flashBtn) {
            flashBtn.disabled = false;
            flashBtn.textContent = originalText;
        }
    }
}

async function buildAndFlash(controllerName, eventOrButton = null) {
    // Handle both event-based (button click) and programmatic calls
    const btn = eventOrButton?.target || eventOrButton;
    const originalText = btn?.textContent;
    
    try {
        if (btn) {
            btn.disabled = true;
            btn.textContent = '🚀 Building...';
        }
        
        // First, build
        showNotification(`Building firmware for ${controllerName}...`, 'info');
        const buildResponse = await fetch(`api/esphome/build/${controllerName}`, {
            method: 'POST'
        });
        const buildResult = await buildResponse.json();
        
        if (!buildResult.success) {
            showNotification(`❌ Build failed: ${buildResult.error}`, 'error');
            return;
        }
        
        if (btn) {
            btn.textContent = '🚀 Flashing...';
        }
        
        // Get port
        const portsResponse = await fetch('api/esphome/ports');
        const portsData = await portsResponse.json();
        let port = 'auto';
        if (portsData.ports && portsData.ports.length > 0) {
            port = await showPortSelectionDialog(portsData.ports);
            if (!port) return;
        }
        
        // Then, flash
        showNotification(`Flashing firmware to ${controllerName}...`, 'info');
        const flashResponse = await fetch(`api/esphome/flash/${controllerName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port })
        });
        const flashResult = await flashResponse.json();
        
        if (flashResult.success) {
            showNotification(`✅ Build & Flash complete! ESP32 is ready.`, 'success');
        } else {
            showNotification(`❌ Flash failed: ${flashResult.error}`, 'error');
        }
    } catch (error) {
        console.error('Build & flash error:', error);
        showNotification(`❌ Failed: ${error.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

function showPortSelectionDialog(ports) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        
        const portOptions = ports.map(port => 
            `<label style="display: block; margin: 10px 0;">
                <input type="radio" name="port" value="${port}"> ${port}
            </label>`
        ).join('');
        
        modal.innerHTML = `
            <div class="modal-content">
                <h2>Select Serial Port</h2>
                <p>Choose the USB port where your ESP32 is connected:</p>
                <div style="margin: 20px 0;">
                    ${portOptions}
                    <label style="display: block; margin: 10px 0;">
                        <input type="radio" name="port" value="auto" checked> Auto-detect
                    </label>
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove(); window.portSelected(null)">Cancel</button>
                    <button class="btn btn-primary" onclick="window.portSelected(document.querySelector('input[name=port]:checked').value)">Continue</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        window.portSelected = (port) => {
            modal.remove();
            delete window.portSelected;
            resolve(port);
        };
    });
}

// Dark mode functionality
function setupDarkMode() {
    // Check localStorage for saved preference
    const darkMode = localStorage.getItem('darkMode') === 'true';
    if (darkMode) {
        document.body.classList.add('dark-mode');
        updateDarkModeIcon();
    }
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDark);
    updateDarkModeIcon();
}

function updateDarkModeIcon() {
    const btn = document.getElementById('dark-mode-toggle');
    if (btn) {
        btn.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    }
}

// Event listeners for settings
document.addEventListener('DOMContentLoaded', () => {
    const useMqttCheckbox = document.getElementById('use-addon-mqtt');
    const nspanelCheckbox = document.getElementById('enable-nspanel');
    const zoomSlider = document.getElementById('map-zoom');
    const saveBtn = document.getElementById('save-settings-btn');
    const resetBtn = document.getElementById('reset-settings-btn');
    
    if (useMqttCheckbox) useMqttCheckbox.addEventListener('change', toggleMQTTSection);
    if (nspanelCheckbox) nspanelCheckbox.addEventListener('change', toggleNSPanelSettings);
    
    const mapCheckbox = document.getElementById('map-enabled');
    if (mapCheckbox) mapCheckbox.addEventListener('change', toggleMapSettings);
    
    if (zoomSlider) zoomSlider.addEventListener('input', updateZoomDisplay);
    if (saveBtn) saveBtn.addEventListener('click', saveSettings);
    if (resetBtn) resetBtn.addEventListener('click', resetSettings);
});
