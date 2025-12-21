import { getPanorama, normalizeHeading } from "./streetview.js";

const agentState = {
  current_node_id: null,
  gps: { lat: null, lng: null },
  heading: null,
  step_count: 0,
  history: [],
};

let updateTimer = null;

async function buildObservation() {
  if (!getPanorama()) return null;

  const panorama = getPanorama();
  const currentPano = panorama.getPano();
  const links = panorama.getLinks() || [];
  const location = panorama.getLocation();
  const pov = panorama.getPov();

  if (!location || !location.latLng) return null;

  const moves = links.map((link) => ({
    heading: normalizeHeading(link.heading),
    next_node_id: link.pano,
  }));

  const heading = normalizeHeading(pov?.heading);

  return {
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
      history: agentState.history.slice(),
    },
  };
}

function updateAgentState(obs) {
  agentState.current_node_id = obs.current_node_id;
  agentState.gps = obs.gps;
  agentState.heading = obs.current_heading;

  if (
    agentState.history.length === 0 ||
    agentState.history[agentState.history.length - 1] !== obs.current_node_id
  ) {
    agentState.history.push(obs.current_node_id);
  }
}

async function updateAgentData() {
  const obs = await buildObservation();
  if (!obs) return null;

  updateAgentState(obs);
  window.dispatchEvent(new CustomEvent("agent_observation_updated", { detail: obs }));
  return obs;
}

function scheduleAgentUpdate() {
  clearTimeout(updateTimer);
  updateTimer = setTimeout(updateAgentData, 120);
}

function attachPanoramaListeners(panorama) {
  if (!panorama) return;
  panorama.addListener("pano_changed", scheduleAgentUpdate);
  panorama.addListener("links_changed", scheduleAgentUpdate);
  panorama.addListener("pov_changed", scheduleAgentUpdate);
}

function waitForStableObservation(timeoutMs = 1500, settleMs = 120) {
  return new Promise((resolve) => {
    let lastObs = null;
    let settleTimer = null;

    const onUpdate = (e) => {
      lastObs = e.detail;
      clearTimeout(settleTimer);
      settleTimer = setTimeout(cleanup, settleMs);
    };

    const timeoutTimer = setTimeout(() => cleanup(), timeoutMs);

    function cleanup() {
      window.removeEventListener("agent_observation_updated", onUpdate);
      clearTimeout(timeoutTimer);
      clearTimeout(settleTimer);
      resolve(lastObs);
    }

    window.addEventListener("agent_observation_updated", onUpdate);
  });
}

async function getFreshObservation() {
  const obs = await waitForStableObservation(1200, 120);
  if (obs) return obs;
  return buildObservation();
}

function incrementStepCount() {
  agentState.step_count += 1;
}

function resetStepState(panoId) {
  agentState.step_count = 0;
  agentState.history = panoId ? [panoId] : [];
}

export {
  buildObservation,
  scheduleAgentUpdate,
  attachPanoramaListeners,
  waitForStableObservation,
  getFreshObservation,
  incrementStepCount,
  resetStepState,
};
