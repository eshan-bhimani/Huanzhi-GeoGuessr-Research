/* * REVERSE ENGINEERED MAP AGENT (No Street Names)
 * Based on MapCrunch logic found in main.min.js
 */

let panorama;
let svService; 

function initTool() {
    // 1. Initialize the Street View Service
    svService = new google.maps.StreetViewService();

    // 2. Initialize the Panorama Viewer
    panorama = new google.maps.StreetViewPanorama(
        document.getElementById('pano-container'), 
        {
            addressControl: false, // Hides address from the visual UI
            showRoadLabels: false, // Hides street names from the map layer
            zoom: 1
        }
    );

    // 3. Listen for changes
    panorama.addListener('pano_changed', () => {
        updateAgentData();
    });

    panorama.addListener('links_changed', () => {
        updateAgentData();
    });

    // 4. Start random
    teleportRandomly();

    // UI Bindings
    document.getElementById('btn-random').addEventListener('click', teleportRandomly);
}

/**
 * TELEPORT LOGIC
 */
function teleportRandomly() {
    const lat = (Math.random() * 180) - 90;
    const lng = (Math.random() * 360) - 180;
    const randomLocation = { lat: lat, lng: lng };
    const radius = 500; 

    console.log(`Agent attempting to teleport...`);

    svService.getPanorama({ location: randomLocation, radius: radius }, (data, status) => {
        if (status === google.maps.StreetViewStatus.OK) {
            panorama.setPano(data.location.pano);
            panorama.setPov({ heading: 0, pitch: 0 });
        } else {
            console.log("Zero results, retrying...");
            teleportRandomly();
        }
    });
}

/**
 * THE AI INTERFACE (Cleaned)
 * Removes all text descriptions. Only geometry and IDs remain.
 */
function updateAgentData() {
    const currentPano = panorama.getPano();
    const links = panorama.getLinks(); 
    const location = panorama.getLocation();
    const pov = panorama.getPov();

    if (!location || !links) return;

    // 1. Construct the Clean Observation Object
    const agentObservation = {
        current_node_id: currentPano,
        gps: {
            lat: location.latLng.lat(),
            lng: location.latLng.lng()
        },
        current_heading: pov.heading,
        // Moves are now purely geometric
        available_moves: links.map(link => ({
            heading: link.heading,   // Direction (0-360)
            next_node_id: link.pano  // The ID to jump to
        }))
    };

    // 2. Render to JSON Box
    const jsonString = JSON.stringify(agentObservation, null, 2);
    document.getElementById('ai-output').value = jsonString;

    // 3. Render Visual Controls
    renderMoveButtons(agentObservation.available_moves);
}

function renderMoveButtons(moves) {
    const list = document.getElementById('moves-list');
    list.innerHTML = '';

    if (moves.length === 0) {
        list.innerHTML = '<div style="color:red">Dead End. Teleport required.</div>';
        return;
    }

    // Sort moves by heading so buttons appear in a logical clockwise order
    moves.sort((a, b) => a.heading - b.heading);

    moves.forEach(move => {
        const btn = document.createElement('button');
        btn.className = 'move-btn';
        const arrow = getArrowIcon(move.heading);
        
        // REMOVED: ${move.description}
        btn.innerHTML = `<span class="arrow-icon">${arrow}</span> <b>${Math.round(move.heading)}°</b>`;
        
        btn.onclick = () => {
            executeAgentMove(move.next_node_id, move.heading);
        };
        list.appendChild(btn);
    });
}

function executeAgentMove(panoId, heading) {
    panorama.setPano(panoId);
    panorama.setPov({
        heading: heading,
        pitch: 0
    });
}

function getArrowIcon(heading) {
    const directions = ['↑', '↗', '→', '↘', '↓', '↙', '←', '↖'];
    // Adjust so 0 (North) maps to index 0
    const index = Math.round(heading / 45) % 8;
    return directions[index];
}