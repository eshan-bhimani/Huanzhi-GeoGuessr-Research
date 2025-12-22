// Add runtime config parsing logic here
(() => {
    const DEFAULTS = {
        panoContainerId: "pano-container",
        pollIntervalMs: 1000,
  };
    const params = new URLSearchParams(window.location.search);
    const existing = window.APP_CONFIG || {};
    const cfg = {...DEFAULTS,...existing};
    
    function parseBool(value) {
        if(value === null || value === undefined) return null;
        const normalized = String(value).toLowerCase().trim();
        if(["1","true","yes","y"].includes(normalized)) return true;
        if(["0","false","no","n"].includes(normalized)) return false;
        return null;
    }

    function parseNumberParam(name) {
        if(!params.has(name)) return null;
        const num = Number(params.get(name));
        return Number.isFinite(num) ? num : null;
    }

    const lat = parseNumberParam("lat");
    const lng = parseNumberParam("lng");
    if(Number.isFinite(lat) && Number.isFinite(lng)) {
        cfg.startLocation = { lat, lng };
    }

    const heading = parseNumberParam("heading");
    if(Number.isFinite(heading)) { cfg.initialHeading = heading; }  

    const pitch = parseNumberParam("pitch");
    if (Number.isFinite(pitch)) cfg.initialPitch = pitch;

    const fov = parseNumberParam("fov");
    if (Number.isFinite(fov)) cfg.initialZoom = fov; // JS API uses zoom; we map fov -> zoom.

    const autostart = parseBool(params.get("autostart"));
    if (autostart !== null) cfg.autostart = autostart;

    const session = params.get("session") || params.get("sessionId");
    if(session) cfg.sessionId = session;

    let apiBase = params.get("apiBase") || cfg.apiBase;
    if(!apiBase) {
        if(cfg.apiPath) {
            const path = cfg.apiPath.startsWith("/") ? cfg.apiPath : `/${cfg.apiPath}`;
            apiBase = `${window.location.origin}${path}`;
        } else if (cfg.useSameOriginApi === true) {
            apiBase = window.location.origin;
        } else {
            apiBase = "http://localhost:8000";
        }
    }
    if(typeof apiBase === "string" && apiBase.trim().length > 0) {
        cfg.apiBase = apiBase.trim().replace(/\/$/, "");
    }

    if(!window.GOOGLE_MAPS_KEY){
        const key = params.get("gmapsKey") || params.get("mapsKey") || params.get("key");
        if(key) window.GOOGLE_MAPS_KEY = key;
    }
    window.APP_CONFIG = cfg;

})();
