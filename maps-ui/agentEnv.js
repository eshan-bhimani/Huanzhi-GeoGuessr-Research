import {
  ensureStreetView,
  moveToPano as moveToPanoInternal,
  teleportToLocation,
  scrollHeading,
  scrollPitch,
  zoom,
} from "./streetview.js";
import {
  buildObservation,
  attachPanoramaListeners,
  waitForStableObservation,
  getFreshObservation,
  incrementStepCount,
  resetStepState,
} from "./appState.js";
import { sendStep, fetchNextInstruction, setApiBase } from "./backEnd.js";

const DEFAULT_FALLBACK_LOCATION = { lat: 37.7749, lng: -122.4194 };
const DEFAULT_HEADING = 120;

const agentConfig = {
  panoContainerId: "pano",
  startLocation: null,
  initialHeading: DEFAULT_HEADING,
  initialPitch: 0,
  initialZoom: null,
  apiBase: null,
  panoOptions: null,
  pollTimeoutMs: 25000,
  sendStepOnInit: true,
};

let isInitialized = false;
let messageBridgeAttached = false;
let pollingActive = false;
let pollingTimerId = null;

// Apply runtime config overrides to the agent config.
function applyConfig(cfg = {}) {
  if (cfg.panoContainerId) agentConfig.panoContainerId = cfg.panoContainerId;
  if (cfg.startLocation) agentConfig.startLocation = cfg.startLocation;
  if (Number.isFinite(cfg.initialHeading)) agentConfig.initialHeading = cfg.initialHeading;
  if (Number.isFinite(cfg.initialPitch)) agentConfig.initialPitch = cfg.initialPitch;
  if (Number.isFinite(cfg.initialZoom)) agentConfig.initialZoom = cfg.initialZoom;
  if (cfg.apiBase) agentConfig.apiBase = cfg.apiBase;
  if (cfg.panoOptions) agentConfig.panoOptions = cfg.panoOptions;
  if (Number.isFinite(cfg.pollTimeoutMs)) agentConfig.pollTimeoutMs = cfg.pollTimeoutMs;
  if (cfg.sendStepOnInit === true || cfg.sendStepOnInit === false) {
    agentConfig.sendStepOnInit = cfg.sendStepOnInit;
  }
}

// Resolve location and heading with overrides and defaults.
function resolveTeleportParams(overrides = {}) {
  const location =
    overrides.location ?? agentConfig.startLocation ?? DEFAULT_FALLBACK_LOCATION;
  const heading =
    typeof overrides.heading === "number" && Number.isFinite(overrides.heading)
      ? overrides.heading
      : typeof agentConfig.initialHeading === "number" &&
        Number.isFinite(agentConfig.initialHeading)
      ? agentConfig.initialHeading
      : DEFAULT_HEADING;
  const pitch =
    typeof overrides.pitch === "number" && Number.isFinite(overrides.pitch)
      ? overrides.pitch
      : typeof agentConfig.initialPitch === "number" &&
        Number.isFinite(agentConfig.initialPitch)
      ? agentConfig.initialPitch
      : 0;
  const zoom =
    typeof overrides.zoom === "number" && Number.isFinite(overrides.zoom)
      ? overrides.zoom
      : typeof agentConfig.initialZoom === "number" &&
        Number.isFinite(agentConfig.initialZoom)
      ? agentConfig.initialZoom
      : null;
 
  return { location, heading, pitch, zoom };
}

// Initialize the Street View environment from a config object.
async function initFromConfig(cfg = {}) {
  if (isInitialized) return buildObservation();
  applyConfig(cfg);
  if (agentConfig.apiBase) setApiBase(agentConfig.apiBase);

  const panorama = ensureStreetView({
    panoContainerId: agentConfig.panoContainerId,
    initialHeading: agentConfig.initialHeading,
    panoOptions: agentConfig.panoOptions,
  });
  attachPanoramaListeners(panorama);

  const obsPromise = waitForStableObservation(2000, 150);
  const { location, heading, pitch, zoom } = resolveTeleportParams();


  const panoId = await teleportToLocation({
    location,
    heading,
    pitch,
    zoom,
    fallbackLocation: DEFAULT_FALLBACK_LOCATION,
  });

  if (panoId) resetStepState(panoId);

  let obs = await obsPromise;
  if (!obs) obs = await buildObservation();
  if (obs && agentConfig.sendStepOnInit !== false) await sendStep(obs);

  attachMessageBridge();
  isInitialized = true;
  return obs;
}

// Initialize once using defaults or a provided config.
function init(options) {
  if (isInitialized) return;
  return initFromConfig(options || {});
}

// Set a new start location and optionally send the updated observation.
async function setStartLocation(location, heading, send = true, extras = null)  {
  if (!location) return null;
  const pitch = extras?.pitch;
  const zoom = extras?.zoom;
  if (Number.isFinite(heading)) agentConfig.initialHeading = heading;
  agentConfig.startLocation = location;

  const obsPromise = waitForStableObservation(2000, 150);
  resetStepState();
  const {
    location: targetLocation,
    heading: targetHeading,
    pitch: targetPitch,
    zoom: targetZoom,
  } = resolveTeleportParams({ location, heading, pitch, zoom });
  
  const panoId = await teleportToLocation({
    location: targetLocation,
    heading: targetHeading,
    pitch: targetPitch,
    zoom: targetZoom,
    fallbackLocation: DEFAULT_FALLBACK_LOCATION,
  });

  if (panoId) resetStepState(panoId);

  let obs = await obsPromise;
  if (!obs) obs = await buildObservation();

  if (send && obs) await sendStep(obs);
  return obs;
}
// Move to a target pano and increment the step counter.
function moveToPanoSafe(panoId, heading = null) {
  incrementStepCount();
  moveToPanoInternal(panoId, heading);
}

// Apply a backend instruction and send the resulting observation.
async function applyInstruction(instr) {
  if (!instr) return null;

  const obsPromise = waitForStableObservation(1500, 120);

  if (instr.action === "move" && instr.target_pano_id) {
    incrementStepCount();
    moveToPanoInternal(instr.target_pano_id, instr.move_heading ?? null);
  } else if (instr.type === "scroll" && instr.axis === "heading") {
    scrollHeading(instr.new);
  } else if (instr.type === "scroll" && instr.axis === "pitch") {
    scrollPitch(instr.new);
  } else if (instr.type === "zoom") {
    zoom(instr.new);
  }

  const obs = await obsPromise;
  if (!obs) return null;

  return sendStep(obs);
}

// Fetch and apply a single instruction from the backend.
async function pollInstructionsOnce() {
  if (document.hidden) return;
  const instr = await fetchNextInstruction(agentConfig.pollTimeoutMs);
  if (!instr || typeof instr !== "object") return;
  console.log("Applying instruction from poll:", instr);
  await applyInstruction(instr);
}

// Start the background polling loop for instructions.
function startInstructionPolling(intervalMs = 1000) {
  if (pollingActive) return;
  pollingActive = true;

  const loop = async () => {
    if (!pollingActive) return;
    try {
      await pollInstructionsOnce();
    } catch (err) {
      console.error("Instruction poll error:", err);
    }
    pollingTimerId = setTimeout(loop, intervalMs);
  };

  loop();
}

// Stop the background polling loop for instructions.
function stopInstructionPolling() {
  pollingActive = false;
  if (pollingTimerId) {
    clearTimeout(pollingTimerId);
    pollingTimerId = null;
  }
}

// Listen for postMessage instructions and apply them.
function attachMessageBridge() {
  if (messageBridgeAttached) return;
  messageBridgeAttached = true;

  window.addEventListener("message", async (event) => {
    const instr = event.data;
    if (!instr || typeof instr !== "object") return;
    if (instr.type === "step_result" || instr.type === "step_error") return;

    const looksLikeInstruction =
      typeof instr.action === "string" ||
      (typeof instr.type === "string" &&
        (instr.type === "scroll" || instr.type === "zoom"));
    if (!looksLikeInstruction) return;

    try {
      console.log("Applying instruction from postMessage:", instr);
      await applyInstruction(instr);
    } catch (err) {
      console.error("Failed to apply instruction:", err);
    }
  });
}

window.addEventListener("beforeunload", () => {
  stopInstructionPolling();
});

const AgentEnv = {
  init,
  initFromConfig,
  getObservation: buildObservation,
  getFreshObservation,
  sendStep,
  setStartLocation,
  moveToPano: moveToPanoSafe,
  scrollHeading,
  scrollPitch,
  zoom,
  startInstructionPolling,
  stopInstructionPolling,
  applyInstruction,
};

export { AgentEnv };
