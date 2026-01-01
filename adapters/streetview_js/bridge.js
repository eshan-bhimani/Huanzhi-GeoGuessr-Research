// Street View bridge exposing window.__SV__.
(() => {
  let panorama = null;
  let svService = null;

  // Initialize the Street View panorama lazily.
  function ensurePanorama() {
    if (panorama) return panorama;
    if (!window.google || !google.maps) {
      throw new Error("maps_not_loaded");
    }
    const container = document.getElementById("pano");
    if (!container) {
      throw new Error("pano_container_missing");
    }
    svService = new google.maps.StreetViewService();
    panorama = new google.maps.StreetViewPanorama(container, {
      pov: { heading: 0, pitch: 0 },
      zoom: 1,
      addressControl: false,
      linksControl: true,
      clickToGo: true,
      showRoadLabels: false,
    });
    return panorama;
  }

  // Return the current pano, POV, position, and links snapshot.
  function getState() {
    if (!panorama) return null;
    const pov = panorama.getPov() || { heading: 0, pitch: 0 };
    const position = panorama.getPosition();
    const links = panorama.getLinks() || [];
    return {
      panoId: panorama.getPano() || null,
      position: position ? { lat: position.lat(), lng: position.lng() } : null,
      pov: {
        heading: pov.heading,
        pitch: pov.pitch,
        zoom: panorama.getZoom(),
      },
      links: links.map((link) => ({
        heading: link.heading,
        panoId: link.pano,
        description: link.description || "",
      })),
    };
  }

  // Initialize panorama position and POV, then wait for stable links.
  function init({ lat, lng, heading = 0, pitch = 0, zoom = 1 } = {}) {
    ensurePanorama();
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      panorama.setPosition({ lat, lng });
    }
    panorama.setPov({ heading, pitch });
    if (Number.isFinite(zoom)) {
      panorama.setZoom(zoom);
    }
    return waitForStable();
  }

  // Update POV (and optionally zoom) without changing pano.
  function setPov({ heading, pitch, zoom } = {}) {
    ensurePanorama();
    const pov = panorama.getPov() || { heading: 0, pitch: 0 };
    panorama.setPov({
      heading: Number.isFinite(heading) ? heading : pov.heading,
      pitch: Number.isFinite(pitch) ? pitch : pov.pitch,
    });
    if (Number.isFinite(zoom)) {
      panorama.setZoom(zoom);
    }
    return getState();
  }

  // Switch to a specific pano id and wait for stable links.
  function setPano({ panoId } = {}) {
    ensurePanorama();
    if (panoId) {
      panorama.setPano(panoId);
    }
    return waitForStable();
  }
  
  // Move to a position and wait for stable links.
  function setPosition({ lat, lng } = {}) {
    ensurePanorama();
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      panorama.setPosition({ lat, lng });
    }
    return waitForStable();
  }

  // Wait until pano/links settle with debounce to avoid empty links.
  function waitForStable({ timeoutMs = 1500, debounceMs = 200 } = {}) {
    ensurePanorama();
    return new Promise((resolve) => {
      const start = Date.now();
      let lastEvent = Date.now();

      // Track the most recent pano/link change event.
      const mark = () => {
        lastEvent = Date.now();
      };

      // Remove listeners once a stable state is reached.
      const panoListener = panorama.addListener("pano_changed", mark);
      const linksListener = panorama.addListener("links_changed", mark);

      // Detach listeners to avoid leaks.
      const cleanup = () => {
        google.maps.event.removeListener(panoListener);
        google.maps.event.removeListener(linksListener);
      };

      // Poll until links are present and events have settled.
      const check = () => {
        const idleMs = Date.now() - lastEvent;
        const links = panorama.getLinks() || [];
        if (idleMs >= debounceMs && links.length > 0) {
          cleanup();
          return resolve(getState());
        }
        if (Date.now() - start >= timeoutMs) {
          cleanup();
          return resolve(getState());
        }
        setTimeout(check, debounceMs);
      };

      setTimeout(check, debounceMs);
    });
  }

  // Poll until Maps JS is loaded, then mark bridge as ready.
  function waitForMaps() {
    if (window.google && google.maps) {
      try {
        ensurePanorama();
        window.__SV__.ready = true;
        return;
      } catch (err) {
        // keep retrying in case Maps is still initializing
      }
    }
    setTimeout(waitForMaps, 50);
  }

  window.__SV__ = {
    ready: false,
    init,
    getState,
    setPov,
    setPano,
    setPosition,
    waitForStable,
  };

  waitForMaps();
})();

