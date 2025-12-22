import { AgentEnv } from "./agentEnv.js";
import { normalizeHeading } from "./streetview.js";

window.AgentEnv = AgentEnv;

// Render the list of move buttons based on available moves.
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

// Convert a heading into a simple arrow label.
function getArrowIcon(heading) {
  const directions = ["^", "NE", ">", "SE", "v", "SW", "<", "NW"];
  const idx = Math.round(normalizeHeading(heading) / 45) % 8;
  return directions[idx];
}

// Shorten long string values for display.
function shortenText(value, max = 120) {
  if(typeof value !== "string") return value;
  if(value.length <= max) return value;
  return `${value.slice(0, max)}... (${value.length} chars)`;
}

// Render the latest observation data and moves list.
function renderObservation(obs) {
  const outEl = document.getElementById("ai-output");
  if (outEl) outEl.value = JSON.stringify(obs, null, 2);
  renderMoveButtons(obs?.available_moves || []);
}

// Render the last step result and image preview.
function renderStep(result) {
  const panoImgEl = document.getElementById("pano-img");
  const imageSrc =
    result?.image ||
    (result?.image_base64 ? `data:image/jpeg;base64,${result.image_base64}` : null);
  if (panoImgEl && imageSrc) {
    panoImgEl.src = imageSrc.startsWith("data:")
      ? imageSrc
      : `data:image/jpeg;base64,${imageSrc}`;
  }

  const actionTextEl = document.getElementById("action-text");
  if (actionTextEl) {
    const display = { ...result };
    if (display.image) display.image = shortenText(display.image);
    if (display.image_base64) display.image_base64 = shortenText(display.image_base64);
    actionTextEl.textContent = JSON.stringify(display, null, 2);
  }
}

// Send the current observation to the backend and update the UI.
async function handleSendStep({ silent = false } = {}) {
  const actionTextEl = document.getElementById("action-text");
  try {
    const obs = await AgentEnv.getFreshObservation();
    if (!obs) {
      if (!silent) alert("No observation available yet.");
      return false;
    }

    if (actionTextEl && !silent) actionTextEl.textContent = "Sending...";
    const result = await AgentEnv.sendStep(obs);
    renderStep(result);
    return true;
  } catch (err) {
    console.error("ERROR CAUGHT:", err);
    if (actionTextEl && !silent) actionTextEl.textContent = `Error: ${err.message}`;
    if (!silent) alert(`Error: ${err.message}`);
    return false;
  }
}


// Bind the button that sends the current observation to the backend.
function bindSendStepButton() {
  const sendStepBtn = document.getElementById("send-step-btn");
  if (!sendStepBtn) return;

  sendStepBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    await handleSendStep();
    return false;
  });
}

// Bind the location input button to teleport to a custom location.
function bindLocationButton() {
  const btn = document.getElementById("go-location-btn");
  if(!btn) return;

  btn.addEventListener("click", async () => {
    const lat = Number(document.getElementById("lat-input")?.value);
    const lng = Number(document.getElementById("lng-input")?.value);
    const headingRaw = document.getElementById("heading-input")?.value?.trim();
    const heading = headingRaw === "" ? null : Number(headingRaw);

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      alert("Enter valid lat/lng");
      return;
    }
    try {
      await AgentEnv.setStartLocation({ lat, lng }, heading, true);
    } catch (err) {
      console.error("Failed to set start location:", err);
      alert(`Error: ${err.message}`);
    }
  });
}
// Initialize the app UI and AgentEnv wiring.
function initApp() {
  const cfg = window.APP_CONFIG || {};

  // 1. Detect Headless Chrome to force the first step execution.
  const isHeadless = /HeadlessChrome/.test(window.navigator.userAgent);

  if (isHeadless) {
    console.log("Running in headless mode. Forcing autostart for the FIRST step.");
    cfg.autostart = true;
    // Increase poll interval in headless mode to reduce load.
    cfg.pollIntervalMs = 2000;
  }

  const panoContainerId = cfg.panoContainerId || "pano-container";
  // Store the autostart state.
  const autostart = cfg.autostart === true;

  // 2. Initialize Agent Environment.
  AgentEnv.initFromConfig({
    ...cfg,
    panoContainerId,
    // If autostart is enabled, we disable the internal 'sendStepOnInit'
    // to manually control the sending logic in the .then() block below.
    sendStepOnInit: !autostart,
  })
    .then(async (obs) => {
      // --- LOGIC: SEND FIRST STEP ONLY ---
      if (!autostart) return;

      console.log("Autostart is ON. Attempting to send the first step...");

      if (obs) {
        try {
          // Send immediately if observation is available.
          await AgentEnv.sendStep(obs);
          console.log("First step sent successfully.");
          return;
        } catch (err) {
          console.error("Initial sendStep failed:", err);
        }
      }

      // If observation is not ready yet, enter the retry loop.
      await autostartSendStep();
    })
    .catch((err) => {
      console.error("AgentEnv init failed:", err);
    });

  // Configure instruction polling (if backend controls the agent).
  const pollInterval = Number.isFinite(cfg.pollIntervalMs) ? cfg.pollIntervalMs : 1000;
  if (cfg.disableInstructionPolling !== true) {
    AgentEnv.startInstructionPolling(pollInterval);
  }

  // 3. Observation Update Event
  // This listener ONLY updates the UI (rendering).
  // It does NOT auto-send data for subsequent steps.
  window.addEventListener("agent_observation_updated", (e) => {
    renderObservation(e.detail);
  });
  
  // Automatically click the "Send Step" button after 5 seconds
  setTimeout(() => {
      console.log("AUTO-SCRIPT: Simulating click on Send Step button...");
      const btn = document.getElementById("send-step-btn");
      
      if (btn) {
          // This triggers the exact same function as your manual mouse click
          btn.click(); 
      } else {
          console.error("AUTO-SCRIPT: Could not find send-step-btn");
      }
  }, 1000);
  // 4. Bind UI Buttons
  // Placed outside the conditional blocks to ensure they work in all browsers.
  bindLocationButton();
  bindSendStepButton();
}

window.addEventListener("load", initApp);
