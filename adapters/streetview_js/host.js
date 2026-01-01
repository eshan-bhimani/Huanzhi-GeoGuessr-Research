const path = require("path");
const readline = require("readline");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const state = {
  apiKey: "",
  browser: null,
  sessions: new Map(),
};
async function ensureBrowser() {
  if(state.browser) return state.browser;
  state.browser = await chromium.launch({headless: true})
  return  state.browser;
}

function getFileUrl() {
  const fileUrl = pathToFileURL(path.join(__dirname, "index.html")).toString();
  return `${fileUrl}?key=${encodeURIComponent(state.apiKey)}`;
}

async function createSession(sessionId) {
  await ensureBrowser();
  const session = {
    id: sessionId,
    context: null,
    page: null,
    last_active: Date.now(),
    queue: Promise.resolve(),
    ready: null,
  };

  session.ready = (async () => {
    session.context = await state.browser.newContext();
    session.page = await session.context.newPage();
    await session.page.goto(getFileUrl(), { waitUntil: "domcontentloaded" });
    await session.page.waitForFunction(
      () => window.__SV__ && window.__SV__.ready === true
    );
    return session;
  })();

  state.sessions.set(sessionId, session);
  await session.ready;
  return session;
}

async function getSession(sessionId) {
  const existing = state.sessions.get(sessionId);
  if(existing) {
    await existing.ready;
    return existing;
  }
  return createSession(sessionId)
}

// Call a bridge method inside the page.
async function callBridge(session, method, params) {
  await session.ready;
  session.last_active = Date.now();
  const payload = { method, params: params || {} };
  return session.page.evaluate(
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
  const key = (params && params.apiKey) || process.env.GOOGLE_MAPS_API_KEY || "";
  if (!key) throw new Error("missing_api_key");
  state.apiKey = key;
  await ensureBrowser();
  return { started: true };
  },
  // Initialize the panorama at a lat/lng and POV.
  async init(session, params) {
    return callBridge(session, "init", params);
  },
  // Fetch the current panorama state.
  async getState(session) {
    return callBridge(session, "getState", {});
  },
  // Update POV without changing pano.
  async setPov(session, params) {
    return callBridge(session, "setPov", params);
  },
  // Move to a specific pano id.
  async setPano(session, params) {
    return callBridge(session,"setPano", params);
  },
  // Move to a lat/lng position.
  async setPosition(session, params) {
    return callBridge(session, "setPosition", params);
  },
  // Wait for pano/links to stabilize.
  async waitForStable(session, params) {
    return callBridge(session, "waitForStable", params);
  },

  // Close the session
  async closeSession(session) {
    await session.ready;
    if (session.page) await session.page.close();
    if (session.context) await session.context.close();
    state.sessions.delete(session.id);
    return { closed: true };
  }
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
  } catch {
    send({ id: null, ok: false, error: "invalid_json" });
    return;
  }

  const id = payload.id ?? null;
  const method = payload.method;
  if (!method || typeof method !== "string") {
    send({ id, ok: false, error: "missing_method" });
    return;
  }
  //parse Json, validate id/method
  const sessionId = payload.session_id;
  if(!sessionId || typeof sessionId !== "string") {
    send({id, ok: false, error: "missing_session_id"});
    return;
  }
  try {
    requireStarted(method);
    const handler = handlers[method];
    if(!handler) throw new Error(`unknown_method:${method}`);

    if(method === "start") {
      const result = await handler(payload.params || {});
      send({id, ok:true, result})
      return;
    }
    const session = await getSession(sessionId);
    const run = async () => handler(session, payload.params || {});
    session.queue = session.queue
      .then(run, run)
      .then((result) => {
        send({id, ok: true, result});
        return result;
      })
      .catch((err) => {
        send({ id, ok: false, error: String(err.message || err) });
      });
  } catch(err) {
    send({ id, ok: false, error: String(err.message || err) });
  }
}

// Start the JSONL loop and dispatch per-session queues.
function startHost() {
  const rl = readline.createInterface({
    input: process.stdin,
    crlfDelay: Infinity,
  });
  // Queue each line to keep request handling ordered.
  rl.on("line", (line) => {
  handleLine(line).catch(() => undefined);
});
}

// Close the browser and clear state.
async function shutdown() {
  for (const session of state.sessions.values()) {
    try {
      await session.ready;
      if (session.page) await session.page.close();
      if (session.context) await session.context.close();
    } catch {}
  }
  state.sessions.clear();
  if (state.browser) await state.browser.close();
  state.browser = null;
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
