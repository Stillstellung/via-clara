let lights = [];
let scenes = [];
let rooms = new Map();
let actionHistory = [];
let pipelineTrackingEnabled = false;
let sceneStatuses = new Map();
let activatingScenes = new Set(); // Track scenes currently being activated

// Pinned items support
let pinnedItems = new Map(); // key: id, value: {type, data}
const PINNED_STORAGE_KEY = 'via-clara-pinned';
let lastRightClick = { time: 0, target: null };

async function fetchData() {
    console.log('fetchData() called');
    showLoading();
    try {
        console.log('Making API calls...');
        const [lightsRes, scenesRes, sceneStatusRes] = await Promise.all([
            fetch('/api/lights'),
            fetch('/api/scenes'),
            fetch('/api/scenes/status/batch')
        ]);
        
        console.log('API calls completed, parsing responses...');
        lights = await lightsRes.json();
        scenes = await scenesRes.json();
        
        // Update scene statuses from batch response
        const batchStatuses = await sceneStatusRes.json();
        sceneStatuses.clear();
        
        // Check if any scene is active
        let hasActiveScene = false;
        for (const [sceneUuid, status] of Object.entries(batchStatuses)) {
            sceneStatuses.set(sceneUuid, status);
            if (status.active) {
                hasActiveScene = true;
            }
        }
        
        // If any scene is active, clear all activating states
        // (only one scene can be active at a time)
        if (hasActiveScene && activatingScenes.size > 0) {
            console.log('Active scene detected, clearing all activating states');
            activatingScenes.clear();
        }
        
        console.log('Re-rendering UI...');
        processRooms();
        renderPinnedSection();
        renderScenes();
        renderRooms();
        renderLights();
        console.log('fetchData() completed successfully');
    } catch (error) {
        console.error('Error fetching data:', error);
        // Fallback: mark all scenes as inactive on error
        sceneStatuses.clear();
        scenes.forEach(scene => {
            sceneStatuses.set(scene.uuid, { active: false });
        });
    } finally {
        hideLoading();
    }
}


function processRooms() {
    rooms.clear();
    lights.forEach(light => {
        if (light.group) {
            if (!rooms.has(light.group.id)) {
                rooms.set(light.group.id, {
                    id: light.group.id,
                    name: light.group.name,
                    lights: []
                });
            }
            rooms.get(light.group.id).lights.push(light);
        }
    });
}

// ===========================
// PINNED ITEMS FUNCTIONS
// ===========================

function loadPinnedItems() {
    try {
        const stored = localStorage.getItem(PINNED_STORAGE_KEY);
        if (stored) {
            pinnedItems = new Map(JSON.parse(stored));
        }
    } catch (e) {
        console.error('Error loading pinned items:', e);
        pinnedItems = new Map();
    }
}

function savePinnedItems() {
    try {
        localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify([...pinnedItems]));
    } catch (e) {
        console.error('Error saving pinned items:', e);
    }
}

function togglePin(id, type, data) {
    if (pinnedItems.has(id)) {
        pinnedItems.delete(id);
    } else {
        pinnedItems.set(id, { type, data });
    }
    savePinnedItems();
    renderPinnedSection();
    renderScenes();
    renderRooms();
    renderLights();
}

function handleRightClick(e, id, type, data) {
    e.preventDefault();
    const now = Date.now();
    if (now - lastRightClick.time < 500 && lastRightClick.target === id) {
        togglePin(id, type, data);
        lastRightClick = { time: 0, target: null };
    } else {
        lastRightClick = { time: now, target: id };
    }
}

function renderPinnedSection() {
    const section = document.getElementById('pinned-section');
    const container = document.getElementById('pinned-container');

    if (pinnedItems.size === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = '';

    pinnedItems.forEach((item, id) => {
        let card;

        if (item.type === 'scene') {
            // Find current scene data
            const scene = scenes.find(s => s.uuid === id);
            if (!scene) {
                // Scene no longer exists, remove from pinned
                pinnedItems.delete(id);
                savePinnedItems();
                return;
            }

            const status = sceneStatuses.get(id) || { active: false };
            const isActivating = activatingScenes.has(id);

            card = document.createElement('div');
            let cardClasses = 'scene-card pinned';
            if (isActivating) cardClasses += ' active';
            else if (status.active) cardClasses += ' scene-active';
            card.className = cardClasses;

            let badgeHtml = '';
            if (isActivating) {
                badgeHtml = '<span class="scene-badge activating">(activating)</span>';
            } else if (status.active) {
                badgeHtml = '<span class="scene-badge">(active)</span>';
            }

            card.innerHTML = `
                <span class="pin-indicator material-icons">push_pin</span>
                <h3>${scene.name} ${badgeHtml}</h3>
            `;
            card.onclick = () => activateScene(id, card);
            card.oncontextmenu = (e) => handleRightClick(e, id, 'scene', scene);

        } else if (item.type === 'room') {
            // Find current room data
            const room = rooms.get(id);
            if (!room) {
                pinnedItems.delete(id);
                savePinnedItems();
                return;
            }

            const lightsOn = room.lights.filter(light => light.power === 'on').length;
            const isRoomOn = lightsOn > 0;

            card = document.createElement('div');
            card.className = `room-card pinned ${isRoomOn ? 'room-on' : 'room-off'}`;
            card.innerHTML = `
                <span class="pin-indicator material-icons">push_pin</span>
                <h3>${room.name}</h3>
                <p class="light-count">${room.lights.length} lights</p>
            `;
            card.onclick = () => toggleRoom(id);
            card.oncontextmenu = (e) => handleRightClick(e, id, 'room', room);

        } else if (item.type === 'light') {
            // Find current light data
            const light = lights.find(l => l.id === id);
            if (!light) {
                pinnedItems.delete(id);
                savePinnedItems();
                return;
            }

            card = document.createElement('div');
            card.className = `light-card pinned ${light.power === 'on' ? 'on' : ''}`;
            card.innerHTML = `
                <span class="pin-indicator material-icons">push_pin</span>
                <h3>
                    <span class="power-indicator ${light.power}"></span>
                    ${light.label}
                </h3>
                <div class="light-info">
                    <p>Brightness: ${Math.round(light.brightness * 100)}%</p>
                    <p>Color: ${light.color.saturation > 0 ? 'Colored' : 'White'}</p>
                </div>
            `;
            card.onclick = () => toggleLight(light.id, card);
            card.oncontextmenu = (e) => handleRightClick(e, id, 'light', light);
        }

        if (card) {
            container.appendChild(card);
        }
    });

    // If all items were removed (orphaned), hide section
    if (container.children.length === 0) {
        section.style.display = 'none';
    }
}

function renderScenes() {
    const container = document.getElementById('scenes-container');
    container.innerHTML = '';

    scenes.forEach(scene => {
        const status = sceneStatuses.get(scene.uuid) || { active: false };
        const isActivating = activatingScenes.has(scene.uuid);
        const isPinned = pinnedItems.has(scene.uuid);

        const card = document.createElement('div');
        let cardClasses = 'scene-card';

        if (isPinned) cardClasses += ' pinned';
        if (isActivating) {
            cardClasses += ' active'; // Purple "activating" state
        } else if (status.active) {
            cardClasses += ' scene-active'; // Green "active" state
        }

        card.className = cardClasses;

        let badgeHtml = '';
        if (isActivating) {
            badgeHtml = `<span class="scene-badge activating">(activating)</span>`;
        } else if (status.active) {
            badgeHtml = `<span class="scene-badge">(active)</span>`;
            console.log(`RENDERING ACTIVE SCENE: ${scene.name} with badge`);
        }

        const pinIndicator = isPinned ? '<span class="pin-indicator material-icons">push_pin</span>' : '';

        card.innerHTML = `
            ${pinIndicator}
            <h3>${scene.name} ${badgeHtml}</h3>
        `;
        card.onclick = () => activateScene(scene.uuid, card);
        card.oncontextmenu = (e) => handleRightClick(e, scene.uuid, 'scene', scene);
        container.appendChild(card);
    });
}

function renderRooms() {
    const container = document.getElementById('rooms-container');
    container.innerHTML = '';

    rooms.forEach(room => {
        // Determine if room is on (any lights are on)
        const lightsOn = room.lights.filter(light => light.power === 'on').length;
        const isRoomOn = lightsOn > 0;
        const isPinned = pinnedItems.has(room.id);

        const card = document.createElement('div');
        card.className = `room-card ${isRoomOn ? 'room-on' : 'room-off'}${isPinned ? ' pinned' : ''}`;

        const pinIndicator = isPinned ? '<span class="pin-indicator material-icons">push_pin</span>' : '';

        card.innerHTML = `
            ${pinIndicator}
            <h3>${room.name}</h3>
            <p class="light-count">${room.lights.length} lights</p>
        `;
        card.onclick = () => toggleRoom(room.id);
        card.oncontextmenu = (e) => handleRightClick(e, room.id, 'room', room);
        container.appendChild(card);
    });
}

function renderLights() {
    const container = document.getElementById('lights-container');
    container.innerHTML = '';

    lights.forEach(light => {
        const isPinned = pinnedItems.has(light.id);

        const card = document.createElement('div');
        card.className = `light-card ${light.power === 'on' ? 'on' : ''}${isPinned ? ' pinned' : ''}`;

        const pinIndicator = isPinned ? '<span class="pin-indicator material-icons">push_pin</span>' : '';

        card.innerHTML = `
            ${pinIndicator}
            <h3>
                <span class="power-indicator ${light.power}"></span>
                ${light.label}
            </h3>
            <div class="light-info">
                <p>Brightness: ${Math.round(light.brightness * 100)}%</p>
                <p>Color: ${light.color.saturation > 0 ? 'Colored' : 'White'}</p>
                ${light.group ? `<p>Room: ${light.group.name}</p>` : ''}
            </div>
        `;
        card.onclick = () => toggleLight(light.id, card);
        card.oncontextmenu = (e) => handleRightClick(e, light.id, 'light', light);
        container.appendChild(card);
    });
}

async function toggleLight(lightId, element) {
    showLoading();
    try {
        const response = await fetch(`/api/toggle/id:${lightId}`, {
            method: 'PUT'
        });
        
        if (response.ok) {
            element.classList.toggle('on');
            const indicator = element.querySelector('.power-indicator');
            indicator.classList.toggle('on');
            indicator.classList.toggle('off');
            
            setTimeout(fetchData, 500);
        }
    } catch (error) {
        console.error('Error toggling light:', error);
    } finally {
        hideLoading();
    }
}

async function toggleRoom(roomId) {
    showLoading();
    try {
        const response = await fetch(`/api/group/${roomId}/toggle`, {
            method: 'PUT'
        });
        
        if (response.ok) {
            setTimeout(fetchData, 500);
        }
    } catch (error) {
        console.error('Error toggling room:', error);
    } finally {
        hideLoading();
    }
}

async function activateScene(sceneUuid, element) {
    showLoading();
    try {
        // Clear any other activating scenes and mark this one as activating
        activatingScenes.clear();
        activatingScenes.add(sceneUuid);
        
        // Re-render to show activating state immediately
        renderScenes();
        
        const response = await fetch(`/api/scene/${sceneUuid}`, {
            method: 'PUT'
        });
        
        if (response.ok) {
            console.log(`Scene ${sceneUuid} activation started`);
            // The activating state will be cleared when scene is detected as active
        } else {
            // Remove from activating if activation failed
            activatingScenes.delete(sceneUuid);
            renderScenes();
        }
    } catch (error) {
        console.error('Error activating scene:', error);
        activatingScenes.delete(sceneUuid);
        renderScenes();
    } finally {
        hideLoading();
    }
}

function showLoading() {
    document.getElementById('loading').classList.add('show');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('show');
}

function addToActionLog(request, result) {
    const timestamp = new Date();
    const logEntry = {
        id: Date.now(),
        timestamp: timestamp,
        request: request,
        result: result,
        expiresAt: timestamp.getTime() + (3 * 60 * 1000) // 3 minutes
    };
    
    actionHistory.unshift(logEntry);
    
    // Keep only last 3 entries
    if (actionHistory.length > 3) {
        actionHistory = actionHistory.slice(0, 3);
    }
    
    updateActionLogDisplay();
    
    // Set timeout to remove this entry after 3 minutes
    setTimeout(() => {
        removeFromActionLog(logEntry.id);
    }, 3 * 60 * 1000);
}

function removeFromActionLog(entryId) {
    const entryElement = document.getElementById(`log-entry-${entryId}`);
    if (entryElement) {
        entryElement.classList.add('removing');
        setTimeout(() => {
            actionHistory = actionHistory.filter(entry => entry.id !== entryId);
            updateActionLogDisplay();
        }, 300); // Wait for fade out animation
    }
}

function updateActionLogDisplay() {
    const logContainer = document.getElementById('action-log');
    const entriesContainer = document.getElementById('action-log-entries');
    
    if (actionHistory.length === 0) {
        logContainer.classList.remove('show');
        return;
    }
    
    logContainer.classList.add('show');
    
    entriesContainer.innerHTML = actionHistory.map(entry => {
        const timeStr = entry.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const success = entry.result.success;
        
        let detailsHtml = '';
        if (entry.result.results && entry.result.results.length > 0) {
            detailsHtml = '<div class="action-log-details"><ul>';
            entry.result.results.forEach(actionResult => {
                const status = actionResult.success ? '✓' : '✗';
                const details = actionResult.details ? ` (${actionResult.details})` : '';
                const error = actionResult.error ? ` - ${actionResult.error}` : '';
                detailsHtml += `<li>${status} ${actionResult.action}${details}${error}</li>`;
            });
            detailsHtml += '</ul></div>';
        }
        
        const summaryText = entry.result.summary || entry.result.error || 'No response';
        return `
            <div id="log-entry-${entry.id}" class="action-log-entry">
                <div class="action-log-time">${timeStr}</div>
                <div class="action-log-summary">"${entry.request}" → ${summaryText}</div>
                ${detailsHtml}
            </div>
        `;
    }).join('');
}

function formatTimeAgo(timestamp) {
    const now = new Date();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return 'just now';
    if (minutes === 1) return '1 min ago';
    return `${minutes} mins ago`;
}

function resetPipeline() {
    const stages = ['ingestion', 'ai', 'api', 'result'];
    stages.forEach(stage => {
        const stageElement = document.getElementById(`stage-${stage}`);
        const statusElement = document.getElementById(`${stage}-status`);
        
        stageElement.classList.remove('active', 'completed', 'error');
        statusElement.innerHTML = '<span class="material-icons">radio_button_unchecked</span>';
    });
    
    // Only hide if pipeline tracking is disabled or this is a new request
    if (!pipelineTrackingEnabled) {
        document.getElementById('processing-pipeline').classList.remove('show');
        document.getElementById('api-details-panel').classList.remove('show');
    }
}

function togglePipelineTracking() {
    pipelineTrackingEnabled = !pipelineTrackingEnabled;
    const toggleBtn = document.getElementById('pipeline-toggle');
    const icon = toggleBtn.querySelector('.material-icons');
    
    if (pipelineTrackingEnabled) {
        toggleBtn.classList.add('active');
        icon.textContent = 'visibility';
        toggleBtn.title = 'Disable pipeline tracking';
    } else {
        toggleBtn.classList.remove('active');
        icon.textContent = 'visibility_off';
        toggleBtn.title = 'Enable pipeline tracking';
        
        // Hide pipeline if it's currently showing
        document.getElementById('processing-pipeline').classList.remove('show');
        document.getElementById('api-details-panel').classList.remove('show');
    }
}

function showLoadingIndicator() {
    const submitBtn = document.getElementById('natural-language-submit');
    
    if (pipelineTrackingEnabled) {
        submitBtn.classList.remove('loading');
        document.getElementById('processing-pipeline').classList.add('show');
    } else {
        document.getElementById('processing-pipeline').classList.remove('show');
        document.getElementById('api-details-panel').classList.remove('show');
        submitBtn.classList.add('loading');
    }
}

function hideLoadingIndicator() {
    const submitBtn = document.getElementById('natural-language-submit');
    submitBtn.classList.remove('loading');
    
    // Only hide pipeline if tracking is disabled
    if (!pipelineTrackingEnabled) {
        document.getElementById('processing-pipeline').classList.remove('show');
        document.getElementById('api-details-panel').classList.remove('show');
    }
}

function updatePipelineStage(stage, status, details = null) {
    const stageElement = document.getElementById(`stage-${stage}`);
    const statusElement = document.getElementById(`${stage}-status`);
    const detailsElement = document.getElementById(`${stage}-details`);
    
    // Remove previous states
    stageElement.classList.remove('active', 'completed', 'error');
    
    // Add new state
    stageElement.classList.add(status);
    
    // Update status icon
    if (status === 'active') {
        statusElement.innerHTML = '<span class="material-icons spinning">refresh</span>';
    } else if (status === 'completed') {
        statusElement.innerHTML = '<span class="material-icons">check_circle</span>';
    } else if (status === 'error') {
        statusElement.innerHTML = '<span class="material-icons">error</span>';
    }
    
    // Update details if provided
    if (details && detailsElement) {
        detailsElement.textContent = details;
    }
}

function showAPIDetails(aiAnalysis, apiRequests, apiResponses) {
    const panel = document.getElementById('api-details-panel');
    
    // Show AI Analysis
    document.getElementById('ai-analysis').innerHTML = `<pre>${JSON.stringify(aiAnalysis, null, 2)}</pre>`;
    
    // Show API Requests
    let requestsHtml = '';
    apiRequests.forEach((req, index) => {
        requestsHtml += `<div class="api-request">
            <div class="request-header">
                <span class="method ${req.method.toLowerCase()}">${req.method}</span>
                <span class="endpoint">${req.endpoint}</span>
            </div>`;
        
        if (req.body) {
            requestsHtml += `<div class="request-body">
                <strong>Body:</strong>
                <pre>${JSON.stringify(req.body, null, 2)}</pre>
            </div>`;
        }
        
        requestsHtml += `</div>`;
    });
    document.getElementById('api-requests').innerHTML = requestsHtml;
    
    // Show API Responses
    let responsesHtml = '';
    apiResponses.forEach((resp, index) => {
        const statusClass = resp.success ? 'success' : 'error';
        responsesHtml += `<div class="api-response ${statusClass}">
            <div class="response-header">
                <span class="status-code">${resp.statusCode || (resp.success ? '200' : '400')}</span>
                <span class="description">${resp.description}</span>
            </div>`;
        
        if (resp.data) {
            responsesHtml += `<div class="response-body">
                <pre>${JSON.stringify(resp.data, null, 2)}</pre>
            </div>`;
        }
        
        if (resp.error) {
            responsesHtml += `<div class="response-error">
                <strong>Error:</strong> ${resp.error}
            </div>`;
        }
        
        responsesHtml += `</div>`;
    });
    document.getElementById('api-responses').innerHTML = responsesHtml;
    
    panel.classList.add('show');
}

async function submitNaturalLanguageRequest() {
    const input = document.getElementById('natural-language-input');
    const submitBtn = document.getElementById('natural-language-submit');
    const responseContainer = document.getElementById('natural-language-response');
    
    const request = input.value.trim();
    if (!request) return;
    
    submitBtn.disabled = true;
    responseContainer.className = 'response-container show';
    responseContainer.innerHTML = '<p>Processing your request...</p>';
    
    // Reset and show appropriate loading indicator
    resetPipeline();
    showLoadingIndicator();
    
    // Stage 1: Prompt Ingestion
    updatePipelineStage('ingestion', 'active', `Analyzing: "${request}"`);
    
    try {
        // Small delay to show ingestion stage
        await new Promise(resolve => setTimeout(resolve, 800));
        updatePipelineStage('ingestion', 'completed', 'Request parsed successfully');
        
        // Stage 2: AI Processing
        updatePipelineStage('ai', 'active', 'Claude AI analyzing request...');
        
        const response = await fetch('/api/natural-language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ request })
        });
        
        const result = await response.json();
        
        if (result.aiAnalysis) {
            updatePipelineStage('ai', 'completed', 'AI analysis complete');
        } else {
            updatePipelineStage('ai', 'completed', 'Commands generated');
        }
        
        // Stage 3: API Execution
        updatePipelineStage('api', 'active', 'Executing API commands...');
        
        // Small delay to show API stage
        await new Promise(resolve => setTimeout(resolve, 500));
        
        if (result.success) {
            updatePipelineStage('api', 'completed', `${result.results?.length || 0} commands executed`);
            
            // Stage 4: Complete
            updatePipelineStage('result', 'completed', result.summary);
            
            // Show API details only if pipeline tracking is enabled
            if (result.apiDetails && pipelineTrackingEnabled) {
                showAPIDetails(
                    result.apiDetails.aiAnalysis || { summary: result.summary },
                    result.apiDetails.requests || [],
                    result.apiDetails.responses || []
                );
            }
        } else {
            updatePipelineStage('api', 'error', 'API execution failed');
            updatePipelineStage('result', 'error', result.error || result.summary);
        }
        
        // Add to action log
        addToActionLog(request, result);
        
        if (result.success) {
            responseContainer.className = 'response-container show success';
            let html = `<p><strong>${result.summary}</strong></p>`;
            
            // Add detailed results if available
            if (result.results && result.results.length > 0) {
                html += '<ul style="margin: 10px 0 0 20px; color: #b0b0b0;">';
                result.results.forEach(actionResult => {
                    const status = actionResult.success ? '✓' : '✗';
                    const details = actionResult.details ? ` (${actionResult.details})` : '';
                    const error = actionResult.error ? ` - ${actionResult.error}` : '';
                    html += `<li>${status} ${actionResult.action}${details}${error}</li>`;
                });
                html += '</ul>';
            }
            
            responseContainer.innerHTML = html;
            setTimeout(fetchData, 1000);
        } else {
            responseContainer.className = 'response-container show error';
            responseContainer.innerHTML = `<p><strong>Error:</strong> ${result.error || result.summary}</p>`;
        }
        
        input.value = '';
        
        setTimeout(() => {
            responseContainer.classList.remove('show');
            hideLoadingIndicator();
            
            // If pipeline tracking is enabled, keep results visible
            if (!pipelineTrackingEnabled) {
                setTimeout(() => {
                    document.getElementById('processing-pipeline').classList.remove('show');
                    document.getElementById('api-details-panel').classList.remove('show');
                }, 3000);
            }
        }, 5000);
        
    } catch (error) {
        updatePipelineStage('ai', 'error', 'Network error occurred');
        updatePipelineStage('result', 'error', error.message);
        
        const errorResult = {
            success: false,
            error: error.message,
            summary: `Failed to process request: ${error.message}`
        };
        
        // Add error to action log
        addToActionLog(request, errorResult);
        
        responseContainer.className = 'response-container show error';
        responseContainer.innerHTML = `<p>Failed to process request: ${error.message}</p>`;
        
        setTimeout(() => {
            responseContainer.classList.remove('show');
            hideLoadingIndicator();
            
            if (!pipelineTrackingEnabled) {
                document.getElementById('processing-pipeline').classList.remove('show');
                document.getElementById('api-details-panel').classList.remove('show');
            }
        }, 5000);
    } finally {
        submitBtn.disabled = false;
    }
}

window.toggleRoom = toggleRoom;

// ===========================
// SETTINGS MODAL FUNCTIONS
// ===========================

let currentSettings = null;
let availableModels = [];

function openSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.add('show');
    loadSettings();
    loadAvailableModels();
}

function closeSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.remove('show');
    clearSettingsMessage();
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        currentSettings = settings;

        // Update status indicator
        const statusElement = document.getElementById('config-status');
        const statusText = document.getElementById('config-status-text');

        if (settings.is_configured) {
            statusElement.className = 'config-status configured';
            statusText.textContent = 'Configuration complete';
        } else {
            statusElement.className = 'config-status not-configured';
            statusText.textContent = 'Configuration required - please enter your API credentials';
        }

        // Populate fields with masked values (placeholders only - don't show actual keys)
        document.getElementById('lifx-token-input').placeholder =
            settings.lifx_token || 'Enter your LIFX API token...';
        document.getElementById('claude-key-input').placeholder =
            settings.claude_api_key || 'Enter your Claude API key...';

        // Don't populate actual values for security
        document.getElementById('lifx-token-input').value = '';
        document.getElementById('claude-key-input').value = '';

        // Populate system prompt textarea
        document.getElementById('system-prompt-textarea').value = settings.system_prompt || '';

    } catch (error) {
        showSettingsMessage('Failed to load settings', 'error');
    }
}

async function loadAvailableModels() {
    try {
        const response = await fetch('/api/models');
        const data = await response.json();
        availableModels = data.models;

        const select = document.getElementById('claude-model-select');
        select.innerHTML = data.models.map(model => `
            <option value="${model.id}" ${model.id === data.current ? 'selected' : ''}>
                ${model.name} - ${model.description} (${model.pricing})
            </option>
        `).join('');

    } catch (error) {
        showSettingsMessage('Failed to load models', 'error');
    }
}

async function saveSettings() {
    const saveButton = document.getElementById('settings-save');
    saveButton.disabled = true;
    saveButton.innerHTML = '<span class="spinner-small"></span> Saving...';

    clearSettingsMessage();

    try {
        // Gather only changed values
        const updates = {};

        const lifxToken = document.getElementById('lifx-token-input').value.trim();
        const claudeKey = document.getElementById('claude-key-input').value.trim();
        const claudeModel = document.getElementById('claude-model-select').value;
        const systemPrompt = document.getElementById('system-prompt-textarea').value;

        if (lifxToken) updates.lifx_token = lifxToken;
        if (claudeKey) updates.claude_api_key = claudeKey;
        if (claudeModel) updates.claude_model = claudeModel;

        // Include system prompt (allow empty string to reset to default)
        const currentPrompt = currentSettings?.system_prompt || '';
        if (systemPrompt !== currentPrompt) {
            updates.system_prompt = systemPrompt;
        }

        if (Object.keys(updates).length === 0) {
            showSettingsMessage('No changes to save', 'info');
            saveButton.disabled = false;
            saveButton.innerHTML = '<span class="material-icons">save</span> Save Settings';
            return;
        }

        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });

        const result = await response.json();

        if (result.success) {
            showSettingsMessage('Settings saved successfully!', 'success');

            // Clear input fields
            document.getElementById('lifx-token-input').value = '';
            document.getElementById('claude-key-input').value = '';

            // Reload settings to show updated masked values
            setTimeout(() => {
                loadSettings();
            }, 1000);

            // Close modal after delay
            setTimeout(() => {
                closeSettings();
            }, 2000);
        } else {
            showSettingsMessage(result.error || 'Failed to save settings', 'error');
        }

    } catch (error) {
        showSettingsMessage('Network error: ' + error.message, 'error');
    } finally {
        saveButton.disabled = false;
        saveButton.innerHTML = '<span class="material-icons">save</span> Save Settings';
    }
}

function togglePasswordVisibility(inputId, buttonId) {
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);
    const icon = button.querySelector('.material-icons');

    if (input.type === 'password') {
        input.type = 'text';
        icon.textContent = 'visibility_off';
    } else {
        input.type = 'password';
        icon.textContent = 'visibility';
    }
}

function showSettingsMessage(message, type = 'info') {
    const messageElement = document.getElementById('settings-message');
    messageElement.textContent = message;
    messageElement.className = `settings-message ${type} show`;
}

function clearSettingsMessage() {
    const messageElement = document.getElementById('settings-message');
    messageElement.className = 'settings-message';
}

async function restoreDefaultPrompt() {
    try {
        const response = await fetch('/api/default-prompt');
        const data = await response.json();
        document.getElementById('system-prompt-textarea').value = data.default_prompt;
        showSettingsMessage('Default prompt restored. Click Save to apply.', 'info');
    } catch (error) {
        showSettingsMessage('Failed to restore default prompt', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Load pinned items from localStorage before fetching data
    loadPinnedItems();

    fetchData();

    const input = document.getElementById('natural-language-input');
    const submitBtn = document.getElementById('natural-language-submit');
    const toggleBtn = document.getElementById('pipeline-toggle');

    submitBtn.addEventListener('click', submitNaturalLanguageRequest);
    toggleBtn.addEventListener('click', togglePipelineTracking);

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitNaturalLanguageRequest();
        }
    });

    // Settings button event listeners
    document.getElementById('settings-button').addEventListener('click', openSettings);
    document.getElementById('settings-close').addEventListener('click', closeSettings);
    document.getElementById('settings-cancel').addEventListener('click', closeSettings);
    document.getElementById('settings-save').addEventListener('click', saveSettings);

    // Password visibility toggles
    document.getElementById('lifx-token-toggle').addEventListener('click', () => {
        togglePasswordVisibility('lifx-token-input', 'lifx-token-toggle');
    });
    document.getElementById('claude-key-toggle').addEventListener('click', () => {
        togglePasswordVisibility('claude-key-input', 'claude-key-toggle');
    });

    // Restore default prompt button
    document.getElementById('restore-default-prompt').addEventListener('click', restoreDefaultPrompt);

    // Close modal on background click
    document.getElementById('settings-modal').addEventListener('click', (e) => {
        if (e.target.id === 'settings-modal') {
            closeSettings();
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('settings-modal');
            if (modal.classList.contains('show')) {
                closeSettings();
            }
        }
    });
});

setInterval(fetchData, 10000); // 10 second refresh