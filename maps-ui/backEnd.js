let apiBase = (window.APP_CONFIG && window.APP_CONFIG.apiBase) || "";
let sessionId = (window.APP_CONFIG && window.APP_CONFIG.sessionId) || "";

// Set the API base URL for backend requests.
function setApiBase(baseUrl) {
  if (typeof baseUrl !== "string") return;
  const trimmed = baseUrl.trim();
  if (!trimmed) return;
  apiBase = trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
  if(!window.APP_CONFIG) window.APP_CONFIG = {};
  window.APP_CONFIG.apiBase = apiBase;
}

// Get the current API base URL.
function getApiBase() {
  return (window.APP_CONFIG && window.APP_CONFIG.apiBase) || apiBase;
}

// Set the session ID for backend requests. ()  
// a session identifier so the backend can keep separate state per client/run.
function getSessionId() {
  return (window.APP_CONFIG && window.APP_CONFIG.sessionId) || sessionId;
}
// Send the current observation to the backend step endpoint.
async function sendStep(observation) {
  if (!observation) throw new Error("No observation provided");
  const base = getApiBase();
  if(!base) throw new Error("API base URL not set");
  const requestBody = { observation };
  const session = getSessionId();
  if (session) requestBody.session_id = session;
  
  const res = await fetch(`${base}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  let responsePayload = null;
  try {
    responsePayload = await res.json();
  } catch (err) {
    responsePayload = null;
  }

  if (!res.ok) {
    const detail = responsePayload?.detail || responsePayload?.message || `API error: ${res.status}`;
    throw new Error(detail);
  }

  return responsePayload;
}

// Fetch the next pending instruction from the backend.
async function fetchNextInstruction(timeoutMs = 25000) {
  const timeoutSec = Math.max(0, Number(timeoutMs)) / 1000;
  const suffix = timeoutSec > 0 ? `?timeout=${timeoutSec}` : "";
  const base = getApiBase();
  if(!base) throw new Error("API base URL not set");
  const res = await fetch(`${base}/instruction/next${suffix}`);
  if (!res.ok) return null;
  const payload = await res.json();
  return payload?.instruction || null;
}

export { setApiBase, getApiBase, sendStep, fetchNextInstruction };
