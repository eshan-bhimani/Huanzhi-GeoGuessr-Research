const path = require("path");
const readline = require("readline");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const state = {
  apiKey: "",
  browser: null,
  page: null,
};

// Launch the browser and load the Street View page once.
async function ensurePage() {
  if (state.page) return state.page;
  state.browser = await chromium.launch({ headless: true });
  state.page = await state.browser.newPage();
  const fileUrl = pathToFileURL(path.join(__dirname, "index.html")).toString();
  const url = `${fileUrl}?key=${encodeURIComponent(state.apiKey)}`;
  await state.page.goto(url, { waitUntil: "domcontentloaded" });
  await state.page.waitForFunction(
    () => window.__SV__ && window.__SV__.ready === true
  );
  return state.page;
}

// Call a bridge method inside the page.
async function callBridge(method, params) {
  await ensurePage();
  const payload = { method, params: params || {} };
  return state.page.evaluate(
    (req) => window.__SV__[req.method](req.params),
    payload
  );
}

// Ensure the host has been started before handling commands.
function requireStarted(method) {
  if (!state.apiKey && method !== "start") {
    throw new Error("not_started");
  }
}

const handlers = {
  // Start the host and load the page with API key.
  async start(params) {
    const key =
      (params && params.apiKey) ||
      process.env.GOOGLE_MAPS_API_KEY ||
      "";
    if (!key) {
      throw new Error("missing_api_key");
    }
    state.apiKey = key;
    await ensurePage();
    return { started: true };
  },
  // Initialize the panorama at a lat/lng and POV.
  async init(params) {
    return callBridge("init", params);
  },
  // Fetch the current panorama state.
  async getState() {
    return callBridge("getState", {});
  },
  // Update POV without changing pano.
  async setPov(params) {
    return callBridge("setPov", params);
  },
  // Move to a specific pano id.
  async setPano(params) {
    return callBridge("setPano", params);
  },
  // Move to a lat/lng position.
  async setPosition(params) {
    return callBridge("setPosition", params);
  },
  // Wait for pano/links to stabilize.
  async waitForStable(params) {
    return callBridge("waitForStable", params);
  },
};

// Write a JSONL response to stdout.
function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

// Parse and dispatch one JSONL request line.
async function handleLine(line) {
  const trimmed = line.trim();
  if (!trimmed) return;
  let payload;
  try {
    payload = JSON.parse(trimmed);
  } catch (err) {
    send({ id: null, ok: false, error: "invalid_json" });
    return;
  }

  const id = payload.id ?? null;
  const method = payload.method;
  if (!method || typeof method !== "string") {
    send({ id, ok: false, error: "missing_method" });
    return;
  }

  try {
    requireStarted(method);
    const handler = handlers[method];
    if (!handler) {
      throw new Error(`unknown_method:${method}`);
    }
    const result = await handler(payload.params || {});
    send({ id, ok: true, result });
  } catch (err) {
    send({ id, ok: false, error: String(err.message || err) });
  }
}

// Start the JSONL loop and serialize requests.
function startHost() {
  const rl = readline.createInterface({
    input: process.stdin,
    crlfDelay: Infinity,
  });
  let chain = Promise.resolve();
  // Queue each line to keep request handling ordered.
  rl.on("line", (line) => {
    chain = chain.then(() => handleLine(line)).catch(() => undefined);
  });
}

// Close the browser and clear state.
async function shutdown() {
  if (state.browser) {
    await state.browser.close();
  }
  state.browser = null;
  state.page = null;
}

process.on("SIGINT", async () => {
  // Graceful shutdown on Ctrl+C.
  await shutdown();
  process.exit(0);
});

process.on("SIGTERM", async () => {
  // Graceful shutdown on termination.
  await shutdown();
  process.exit(0);
});

startHost();
