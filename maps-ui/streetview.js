let panorama= null;
let svService = null;
let navToken = 0;


const DEFAULT_POV = { heading: 34, pitch: 10}

// Normalize a heading into the range [0, 360).
function normalizeHeading(h) {
    const x = Number(h);
    if(!Number.isFinite(x)) return 0;
    return ((x % 360) + 360) % 360;
}

// Increment and return the navigation token to track latest navigation.
function bumpNavToken() {
    navToken += 1;
    return navToken;
}

// Check whether a token is the latest navigation token.
function isLatestToken(t) {
    return t === navToken;
}

// Create (or return) the Street View panorama and service.
function ensureStreetView(options= {}) {
    if (panorama) return panorama;

    const panoContainerId = options.panoContainerId || "pano";
    const initialHeading = Number.isFinite(options.initialHeading)
        ? options.initialHeading
        : DEFAULT_POV.heading;
    const panoOptions = options.panoOptions || {};

    const container = document.getElementById(panoContainerId);
    if(!container) throw new Error(`Panorama container not found: ${panoContainerId}`);
    if(!window.google || !google.maps) throw new Error("Google Maps JS API not loaded");

    svService = new google.maps.StreetViewService();
    panorama= new google.maps.StreetViewPanorama(container, {
        pov: { heading: normalizeHeading(initialHeading), pitch: DEFAULT_POV.pitch},
        addressControl: true,
        showRoadLabels: false,
        linksControl: true,
        enableCloseButton: false,
        panControl: true,
        clickToGo: true,
        zoom: 1,
        ...panoOptions,
    });

    return panorama;
}

// Return the current Street View panorama instance.
function getPanorama() {
    return panorama
}

// Move to a pano and optionally set the heading once loaded.
function moveToPano(panoId, heading = null) {
    if(!panorama) return;

    const token = bumpNavToken();
    panorama.setPano(panoId);

    google.maps.event.addListenerOnce(panorama, "pano_changed", () => {
        if(!isLatestToken(token)) return;
        const pov = panorama.getPov() || { heading: 0, pitch: 0};
        const h = 
            typeof heading === "number" && Number.isFinite(heading)
                ? normalizeHeading(heading)
                : normalizeHeading(pov.heading);
        
        panorama.setPov({heading: h, pitch: 0});
    });
}

// Teleport to a location within a radius and resolve the pano id.
function teleportToLocation(options = {}) {
    if(!svService || !panorama) return Promise.resolve(null);

    const token = bumpNavToken();
    const radius = Number.isFinite(options.radius) ? options.radius : 500;
    const fallbackLocation = options.fallbackLocation || {lat: 37.7749, lng: -122.4194};
    const target = options.location || fallbackLocation;
    const heading = 
        typeof options.heading === "number" && Number.isFinite(options.heading)
        ? options.heading
        : 100;
    const pitch = 
        typeof options.pitch === "number" && Number.isFinite(options.pitch)
        ? options.pitch
        : 0;
    const zoom = 
        typeof options.zoom === "number" && Number.isFinite(options.zoom)
        ? options.zoom
        : null;

    return new Promise((resolve) => {
        svService.getPanorama({ location: target, radius }, ( data, status) => {
            if(!isLatestToken(token)) return resolve(null);
            if(status === google.maps.StreetViewStatus.OK) {
                const panoId = data.location.pano;
                panorama.setPano(panoId);
                google.maps.event.addListenerOnce(panorama, "pano_changed", () =>{
                  if(!isLatestToken(token)) return resolve(null);
                  panorama.setPov({ heading: normalizeHeading(heading), pitch});
                  if(Number.isFinite(zoom)) panorama.setZoom(zoom);
                  resolve(panoId)
                });
            } else {
                console.log("Zero results, retrying...")
                resolve(null);
            }
        });
    });
}

// Set the panorama heading without changing the pano.
function scrollHeading(newHeading) {
    if(!panorama) return;
    const pov = panorama.getPov() || { heading: 0, pitch: 0};
    panorama.setPov({...pov, heading: normalizeHeading(newHeading)});
}

// Set the panorama pitch without changing the pano.
function scrollPitch(newPitch) {
    if(!panorama) return;
    const pov = panorama.getPov() || { heading: 0, pitch: 0};
    panorama.setPov({...pov, pitch: Number(newPitch)});
}

// Set the panorama zoom level.
function zoom(newZoom) {
    if(!panorama) return;
    panorama.setZoom(Number(newZoom));
}

export {
    ensureStreetView,
    getPanorama,
    moveToPano,
    teleportToLocation,
    scrollHeading,
    scrollPitch,
    zoom,
    normalizeHeading,
};
