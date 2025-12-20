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

const agentConfig = {
  panoContainerId: "pano",
  randomButtonId: "teleport-random-btn",
  startLocation: null,
  radius: 500,
  initialHeading: 120,
  apiBase: null,
  panoOptions: null,
  pollTimeoutMs: 25000,
};

let isInitialized = false;
let messageBridgeAttached = false;
let pollingActive = false;
let pollingTimerId = null;

function applyConfig(cfg = {}) {
  if (cfg.panoContainerId) agentConfig.panoContainerId = cfg.panoContainerId;
  if (cfg.randomButtonId) agentConfig.randomButtonId = cfg.randomButtonId;
  if (cfg.startLocation) agentConfig.startLocation = cfg.startLocation;
  if (Number.isFinite(cfg.radius)) agentConfig.radius = cfg.radius;
  if (Number.isFinite(cfg.startRadius)) agentConfig.radius = cfg.startRadius;
  if (Number.isFinite(cfg.initialHeading)) agentConfig.initialHeading = cfg.initialHeading;
  if (cfg.apiBase) agentConfig.apiBase = cfg.apiBase;
  if (cfg.panoOptions) agentConfig.panoOptions = cfg.panoOptions;
  if (Number.isFinite(cfg.pollTimeoutMs)) agentConfig.pollTimeoutMs = cfg.pollTimeoutMs;
}

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
  const location = agentConfig.startLocation || DEFAULT_FALLBACK_LOCATION;
  const radius = Number.isFinite(agentConfig.radius) ? agentConfig.radius : 500;
  const heading =
    typeof agentConfig.initialHeading === "number" &&
    Number.isFinite(agentConfig.initialHeading)
      ? agentConfig.initialHeading
      : 120;

  const panoId = await teleportToLocation({
    location,
    radius,
    heading,
    fallbackLocation: DEFAULT_FALLBACK_LOCATION,
  });

  if (panoId) resetStepState(panoId);

  let obs = await obsPromise;
  if (!obs) obs = await buildObservation();
  if (obs) await sendStep(obs);

  attachMessageBridge();
  isInitialized = true;
  return obs;
}

function init(options) {
  if (isInitialized) return;
  return initFromConfig(options || {});
}

async function teleportRandom() {
  const location = agentConfig.startLocation || DEFAULT_FALLBACK_LOCATION;
  const radius = Number.isFinite(agentConfig.radius) ? agentConfig.radius : 500;
  const heading =
    typeof agentConfig.initialHeading === "number" &&
    Number.isFinite(agentConfig.initialHeading)
      ? agentConfig.initialHeading
      : 120;

  const panoId = await teleportToLocation({
    location,
    radius,
    heading,
    fallbackLocation: DEFAULT_FALLBACK_LOCATION,
  });

  if (panoId) resetStepState(panoId);
  return panoId;
}

async function setStartLocation(location, radius, heading, send = true) {
  if (!location) return null;

  if (Number.isFinite(radius)) agentConfig.radius = radius;
  if (Number.isFinite(heading)) agentConfig.initialHeading = heading;
  agentConfig.startLocation = location;

  const obsPromise = waitForStableObservation(2000, 150);
  resetStepState();

  const panoId = await teleportToLocation({
    location,
    radius: Number.isFinite(radius) ? radius : agentConfig.radius,
    heading: Number.isFinite(heading) ? heading : agentConfig.initialHeading,
    fallbackLocation: DEFAULT_FALLBACK_LOCATION,
  });

  if (panoId) resetStepState(panoId);

  let obs = await obsPromise;
  if (!obs) obs = await buildObservation();

  if (send && obs) await sendStep(obs);
  return obs;
}
function moveToPanoSafe(panoId, heading = null) {
  incrementStepCount();
  moveToPanoInternal(panoId, heading);
}

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

async function pollInstructionsOnce() {
  if (document.hidden) return;
  const instr = await fetchNextInstruction(agentConfig.pollTimeoutMs);
  if (!instr || typeof instr !== "object") return;
  console.log("Applying instruction from poll:", instr);
  await applyInstruction(instr);
}

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

function stopInstructionPolling() {
  pollingActive = false;
  if (pollingTimerId) {
    clearTimeout(pollingTimerId);
    pollingTimerId = null;
  }
}

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
  teleportRandom,
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
