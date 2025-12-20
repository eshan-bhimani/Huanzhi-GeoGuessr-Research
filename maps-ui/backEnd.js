let apiBase = "http://localhost:8000";

function setApiBase(baseUrl) {
  if (typeof baseUrl !== "string") return;
  const trimmed = baseUrl.trim();
  if (!trimmed) return;
  apiBase = trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

function getApiBase() {
  return apiBase;
}

async function sendStep(observation) {
  if (!observation) throw new Error("No observation provided");

  const res = await fetch(`${apiBase}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ observation }),
  });

  let payload = null;
  try {
    payload = await res.json();
  } catch (err) {
    payload = null;
  }

  if (!res.ok) {
    const detail = payload?.detail || payload?.message || `API error: ${res.status}`;
    throw new Error(detail);
  }

  return payload;
}

async function fetchNextInstruction(timeoutMs = 25000) {
  const timeoutSec = Math.max(0, Number(timeoutMs)) / 1000;
  const suffix = timeoutSec > 0 ? `?timeout=${timeoutSec}` : "";
  const res = await fetch(`${apiBase}/instruction/next${suffix}`);
  if (!res.ok) return null;
  const payload = await res.json();
  return payload?.instruction || null;
}

export { setApiBase, getApiBase, sendStep, fetchNextInstruction };
