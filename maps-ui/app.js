/* REVERSE ENGINEERED MAP AGENT (No Street Names)
 * Stable version: prevents "jump back" caused by late teleport callbacks / init races.
 */

let panorama;
let svService;


// ---- Config ----
const API_BASE = "http://localhost:8000";

// ---- Core agent state (what your LLM cares about) ----
const agentState = {
  current_node_id: null,
  gps: { lat: null, lng: null },
  heading: null,
  step_count: 0,
  history: [],
};

// ---- Navigation token (cancels in-flight teleports / moves) ----
let navToken = 0;
function bumpNavToken() {
  navToken += 1;
  return navToken;
}
function isLatestToken(t) {
  return t === navToken;
}

// ---- Utilities ----
function normalizeHeading(h) {
  const x = Number(h);
  if (!Number.isFinite(x)) return 0;
  return ((x % 360) + 360) % 360;
}

// ---- Observation builder ----
async function buildObservation() {
  console.log("buildObservation: START");
  if (!panorama) {
    console.log("buildObservation: No panorama, returning null");
    return null;
  }

  const currentPano = panorama.getPano();
  const links = panorama.getLinks() || [];
  const location = panorama.getLocation();
  const pov = panorama.getPov();

  if (!location || !location.latLng) {
    console.log("buildObservation: No location, returning null");
    return null;
  }

  const moves = links.map((link) => ({
    heading: normalizeHeading(link.heading),
    next_node_id: link.pano,
  }));

  const heading = normalizeHeading(pov?.heading);

  const result = {
    current_node_id: currentPano,
    gps: {
      lat: location.latLng.lat(),
      lng: location.latLng.lng(),
    },
    current_heading: heading,
    available_moves: moves,
    image: null,
    meta: {
      step_count: agentState.step_count,
      history: agentState.history,
    },
  };
  
  console.log("buildObservation: COMPLETE", result);
  return result;
}

// ---- Debounced update (avoid half-updated pano/link/pov races) ----
let updateTimer = null;
function scheduleAgentUpdate() {
  clearTimeout(updateTimer);
  updateTimer = setTimeout(updateAgentData, 120); // 80–200ms is a good range
}

async function updateAgentData() {
  console.log("updateAgentData: START");
  const obs = await buildObservation();
  if (!obs) {
    console.log("updateAgentData: No observation, returning");
    return;
  }

  agentState.current_node_id = obs.current_node_id;
  agentState.gps = obs.gps;
  agentState.heading = obs.current_heading;

  if (
    agentState.history.length === 0 ||
    agentState.history[agentState.history.length - 1] !== obs.current_node_id
  ) {
    agentState.history.push(obs.current_node_id);
  }

  const outEl = document.getElementById("ai-output");
  if (outEl) outEl.value = JSON.stringify(obs, null, 2);

  const movesEl = document.getElementById("moves-list");
  if (movesEl) renderMoveButtons(obs.available_moves);

  window.dispatchEvent(
    new CustomEvent("agent_observation_updated", { detail: obs })
  );
  console.log("updateAgentData: COMPLETE, event dispatched");
}

// ---- UI: move buttons ----
function renderMoveButtons(moves) {
  const list = document.getElementById("moves-list");
  if (!list) return;

  list.innerHTML = "";

  if (!moves || moves.length === 0) {
    list.innerHTML = '<div style="color:red">Dead End. Teleport required.</div>';
    return;
  }

  moves.sort((a, b) => a.heading - b.heading);

  moves.forEach((move) => {
    const btn = document.createElement("button");
    btn.className = "move-btn";
    const arrow = getArrowIcon(move.heading);

    btn.innerHTML = `<span class="arrow-icon">${arrow}</span> <b>${Math.round(
      move.heading
    )} deg</b>`;

    btn.onclick = () => {
      AgentEnv.moveToPano(move.next_node_id, move.heading);
    };

    list.appendChild(btn);
  });
}

function getArrowIcon(heading) {
  const directions = ["^", "NE", ">", "SE", "v", "SW", "<", "NW"];
  const idx = Math.round(normalizeHeading(heading) / 45) % 8;
  return directions[idx];
}

const agentConfig = {
  startLocation: null,
  startRadius: 500,
}
// ---- Teleport logic (guarded against late callbacks) ----
function teleportRandomly() {
    if (!svService || !panorama) return;

    const token = bumpNavToken();
    const radius = agentConfig.startRadius || 500;
    const fallback = { lat: 37.7749, lng: -122.4194 };
    const target = agentConfig.startLocation || fallback;

    svService.getPanorama({ location: target, radius }, (data, status) => {
      if (!isLatestToken(token)) return;
      if (status === google.maps.StreetViewStatus.OK) {
        const panoId = data.location.pano;
        panorama.setPano(panoId);
        google.maps.event.addListenerOnce(panorama, "pano_changed", () => {
          if (!isLatestToken(token)) return;
          panorama.setPov({ heading: 120, pitch: 0 });
        });
        agentState.step_count = 0;
        agentState.history = [panoId];
      } else {
        console.log("Zero results, retrying...");
      }
    });
  }

// ---- Wait for stable observation (last event after settle window) ----
function waitForStableObservation(timeoutMs = 1500, settleMs = 120) {
  console.log("waitForStableObservation: START, timeout:", timeoutMs, "settle:", settleMs);
  return new Promise((resolve) => {
    let lastObs = null;
    let settleTimer = null;

    const onUpdate = (e) => {
      console.log("waitForStableObservation: Event received");
      lastObs = e.detail;
      clearTimeout(settleTimer);
      settleTimer = setTimeout(cleanup, settleMs);
    };

    const timeoutTimer = setTimeout(() => {
      console.log("waitForStableObservation: Timeout reached");
      cleanup();
    }, timeoutMs);

    function cleanup() {
      console.log("waitForStableObservation: Cleanup, resolving with:", lastObs);
      window.removeEventListener("agent_observation_updated", onUpdate);
      clearTimeout(timeoutTimer);
      clearTimeout(settleTimer);
      resolve(lastObs);
    }

    window.addEventListener("agent_observation_updated", onUpdate);
  });
}

async function getFreshObservation() {
  console.log("getFreshObservation: START");
  const obs = await waitForStableObservation(1200, 120);
  if (obs) {
    console.log("getFreshObservation: Got observation from waitForStable");
    return obs;
  }
  console.log("getFreshObservation: No observation from waitForStable, calling getObservation");
  const fallback = await AgentEnv.getObservation();
  console.log("getFreshObservation: Fallback observation:", fallback);
  return fallback;
}

// ---- Public API ----
const AgentEnv = {
  init(options) {
    // Prevent double init (common cause of "teleport fights" + jumps)
    if (panorama) return;

    const panoContainerId = options?.panoContainerId || "pano";
    const randomBtnId = options?.randomButtonId || "teleport-random-btn";

    // New: accept overrides
    if (options?.startLocation) agentConfig.startLocation = options.startLocation;
    if (options?.startRadius) agentConfig.startRadius = options.startRadius;
    svService = new google.maps.StreetViewService();

    panorama = new google.maps.StreetViewPanorama(
      document.getElementById(panoContainerId),
      {
        pov: { heading: 34, pitch: 10 },
        addressControl: true,
        showRoadLabels: false,
        linksControl: true,
        enableCloseButton: false,
        panControl: true,
        clickToGo: true,
        zoom: 1,
      }
    );

    // Debounced listeners
    panorama.addListener("pano_changed", scheduleAgentUpdate);
    panorama.addListener("links_changed", scheduleAgentUpdate);
    panorama.addListener("pov_changed", scheduleAgentUpdate);

    const randomBtn = document.getElementById(randomBtnId);
    if (randomBtn) {
      randomBtn.addEventListener("click", () => {
        this.teleportRandom();
      });
    }

    // Start with teleport
    this.teleportRandom();
  },

  async getObservation() {
    return buildObservation();
  },

  teleportRandom() {
    teleportRandomly();
  },

  // Safe move: cancels teleport in-flight + sets POV after pano_changed
  moveToPano(panoId, heading = null) {
    if (!panorama) return;

    const token = bumpNavToken();
    agentState.step_count += 1;

    panorama.setPano(panoId);

    google.maps.event.addListenerOnce(panorama, "pano_changed", () => {
      if (!isLatestToken(token)) return;

      const pov = panorama.getPov() || { heading: 0, pitch: 0 };
      const h =
        typeof heading === "number" && Number.isFinite(heading)
          ? normalizeHeading(heading)
          : normalizeHeading(pov.heading);

      panorama.setPov({ heading: h, pitch: 0 });
    });
  },

  // Optional: scroll + zoom helpers (do not bump navToken)
  scrollHeading(newHeading) {
    if (!panorama) return;
    const pov = panorama.getPov() || { heading: 0, pitch: 0 };
    panorama.setPov({ ...pov, heading: normalizeHeading(newHeading) });
  },

  scrollPitch(newPitch) {
    if (!panorama) return;
    const pov = panorama.getPov() || { heading: 0, pitch: 0 };
    panorama.setPov({ ...pov, pitch: Number(newPitch) });
  },

  zoom(newZoom) {
    if (!panorama) return;
    panorama.setZoom(Number(newZoom));
  },

  // Instruction polling controls (opt-in)
  startInstructionPolling(intervalMs = 1000) {
    startInstructionPolling(intervalMs);
  },
  stopInstructionPolling() {
    stopInstructionPolling();
  },

  // Optional: single entry point if you want tool-style instructions
  async applyInstruction(instr) {
    if (!instr) return null;

    // Listen BEFORE applying changes
    const obsPromise = waitForStableObservation(1500, 120);

    if (instr.action === "move" && instr.target_pano_id) {
      this.moveToPano(instr.target_pano_id, instr.move_heading ?? null);
    } else if (instr.type === "scroll" && instr.axis === "heading") {
      this.scrollHeading(instr.new);
    } else if (instr.type === "scroll" && instr.axis === "pitch") {
      this.scrollPitch(instr.new);
    } else if (instr.type === "zoom") {
      this.zoom(instr.new);
    }

    const obs = await obsPromise;
    if (!obs) return null;

    const res = await fetch(`${API_BASE}/step`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ observation: obs }),
    });

    if (!res.ok) throw new Error(`API error: ${res.status}`);
    
    return res.json();
  },
};

window.AgentEnv = AgentEnv;

// Listen for instructions sent via window.postMessage (manual/external controllers)
window.addEventListener("message", async (event) => {
  const instr = event.data;
  // Ignore non-objects and known non-instruction payloads to avoid loops.
  if (!instr || typeof instr !== "object") return;
  if (instr.type === "step_result" || instr.type === "step_error") return;

  const looksLikeInstruction =
    typeof instr.action === "string" ||
    (typeof instr.type === "string" && (instr.type === "scroll" || instr.type === "zoom"));
  if (!looksLikeInstruction) return;

  try {
    console.log("Applying instruction from postMessage:", instr);
    await AgentEnv.applyInstruction(instr);
  } catch (err) {
    console.error("Failed to apply instruction:", err);
  }
});

// Poll backend for MCP-pushed instructions and apply them automatically.
async function pollInstructions() {
  // Skip polling when tab not visible to reduce noise.
  if (document.hidden) return;
  try {
    const res = await fetch(`${API_BASE}/instruction/next`);
    if (!res.ok) return;
    const payload = await res.json();
    const instr = payload?.instruction;
    if (instr && typeof instr === "object") {
      console.log("Applying instruction from poll:", instr);
      await AgentEnv.applyInstruction(instr);
    }
  } catch (err) {
    console.error("Instruction poll error:", err);
  }
}

function startInstructionPolling(intervalMs = 1000) {
  if (startInstructionPolling.active) return; // prevent multiple loops
  startInstructionPolling.active = true;

  const loop = async () => {
    if (!startInstructionPolling.active) return;
    await pollInstructions();
    // use setTimeout instead of setInterval to avoid pile-ups
    startInstructionPolling.timerId = setTimeout(loop, intervalMs);
  };

  loop();
}

function stopInstructionPolling() {
  startInstructionPolling.active = false;
  if (startInstructionPolling.timerId) {
    clearTimeout(startInstructionPolling.timerId);
    startInstructionPolling.timerId = null;
  }
}

// Clear polling on unload (helps with hot-reloads)
window.addEventListener("beforeunload", () => {
  stopInstructionPolling();
});

// ---- Backend step call ----
async function sendStep(observation) {
  console.log("sendStep: START");
  
  setTimeout(() => console.log("sendStep: [CHECKPOINT 1] About to fetch"), 0);
  
  const res = await fetch(`${API_BASE}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ observation }),
  });

  setTimeout(() => console.log("sendStep: [CHECKPOINT 2] Fetch completed, status:", res.status), 0);

  let payload = null;
  try {
    setTimeout(() => console.log("sendStep: [CHECKPOINT 3] Parsing JSON..."), 0);
    payload = await res.json();
    setTimeout(() => console.log("sendStep: [CHECKPOINT 4] JSON parsed successfully:", payload), 0);
  } catch (err) {
    setTimeout(() => console.log("sendStep: [CHECKPOINT 4-ERROR] JSON parse failed:", err), 0);
    payload = null;
  }

  if (!res.ok) {
    const detail = payload?.detail || payload?.message || `API error: ${res.status}`;
    setTimeout(() => console.log("sendStep: [CHECKPOINT 5] Response not OK, throwing error"), 0);
    throw new Error(detail);
  }
  
  setTimeout(() => console.log("sendStep: [CHECKPOINT 6] Returning payload"), 0);
  return payload;
}

function renderStep(result) {
  console.log("renderStep: START", result);
  
  setTimeout(() => console.log("renderStep: [CHECKPOINT 1] Processing image"), 0);
  
  const panoImgEl = document.getElementById("pano-img");
  const imageSrc =
    result?.image ||
    (result?.image_base64 ? `data:image/jpeg;base64,${result.image_base64}` : null);
  if (panoImgEl && imageSrc) {
    setTimeout(() => console.log("renderStep: [CHECKPOINT 2] Setting image src"), 0);
    panoImgEl.src = imageSrc.startsWith("data:")
      ? imageSrc
      : `data:image/jpeg;base64,${imageSrc}`;
  }

  setTimeout(() => console.log("renderStep: [CHECKPOINT 3] Updating action text"), 0);
  const actionTextEl = document.getElementById("action-text");
  if (actionTextEl) actionTextEl.textContent = JSON.stringify(result, null, 2);
  
  setTimeout(() => console.log("renderStep: [CHECKPOINT 4] COMPLETE"), 0);
}

const sendStepBtn = document.getElementById("send-step-btn");
if (sendStepBtn) {
  sendStepBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();       // Add this
    e.stopImmediatePropagation(); // Add this
    
    console.log("=== BUTTON CLICK START ===");
    
    const actionTextEl = document.getElementById("action-text");
    try {
      const obs = await getFreshObservation();
      
      if (!obs) {
        alert("No observation available yet.");
        return;
      }
      
      if (actionTextEl) actionTextEl.textContent = "Sending...";
      
      const result = await sendStep(obs);
      renderStep(result);
      console.log("=== BUTTON CLICK COMPLETE ===");
    } catch (err) {
      console.error("ERROR CAUGHT:", err);
      if (actionTextEl) actionTextEl.textContent = `Error: ${err.message}`;
      alert(`Error: ${err.message}`);
    }
    
    return false; // Add this
  });
}

// ---- External instruction bridge (postMessage) ----
// Allows an external controller (e.g., MCP driver/Playwright) to send an instruction
// into the page via window.postMessage and have it applied through AgentEnv.
window.addEventListener("message", async (event) => {
  // Optional safety: restrict by origin if you serve the page over HTTP.
  // if (event.origin !== "http://localhost:3000") return;

  const instr = event.data;
  // Ignore non-object payloads and our own ACKs to prevent loops.
  if (!instr || typeof instr !== "object") return;
  if (instr.type === "step_result" || instr.type === "step_error") return;

  // Only accept messages that look like real instructions.
  const isInstruction =
    typeof instr.action === "string" ||
    (typeof instr.type === "string" &&
      (instr.type === "scroll" || instr.type === "zoom"));
  if (!isInstruction) return;

  try {
    console.log("Applying instruction from postMessage:", instr);
    const result = await AgentEnv.applyInstruction(instr);
    // ACKs removed to avoid any chance of message ping-pong.
  } catch (err) {
    console.error("Failed to apply instruction:", err);
  }
});
