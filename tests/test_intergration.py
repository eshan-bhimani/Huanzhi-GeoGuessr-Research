"""
Integration tests for the GeoGuessr Research framework.

These tests require:
- A valid Google Maps API key (set GOOGLE_MAPS_API_KEY env var)
- Node.js installed
- Playwright browsers installed

Run with: pytest -m integration tests/test_integration.py
"""

import os
import pytest

# Skip all tests in this module if no API key
pytestmark = pytest.mark.integration
@pytest.fixture
def api_key():
    """Get API key from environment."""
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        pytest.skip("GOOLGE_MAPS_API_KEY not set")
    
    return key

@pytest.fixture
def host_client():
    """Create a StreetViewHostClient instance."""
    from adapters.streetview_js.client import StreetViewHostClient

    client = StreetViewHostClient()
    yield client
    client.close()

class TestStreetViewHostClient:
    """Integration tests for StreetViewHostClient."""

    def test_start_session(self, host_client, api_key):
        """Test starting a session."""
        # This test would actually connect to the host
        # Skipped by default - implement when ready
        pytest.skip("Requires running host process")

    def test_init_panorama(self, host_client, api_key):
        """Test initializing a panorama at known coordinates."""
        pytest.skip("Requires running host process")
    
    def test_get_state(self, host_client, api_key):
        """Test getting panorama state."""
        pytest.skip("Requires running host process")

    def test_navigation_flow(self, host_client, api_key):
        """Test a complete navigation flow."""
        pytest.skip("Requires running host process")


class TestEndToEndNavigation:
    """End-to-end navigation tests."""

    def test_move_and_check_direction(self, host_client, api_key):
        """Test moving and checking direction."""
        pytest.skip("Requires running host process")

    def test_scroll_camera(self, host_client, api_key):
        """Test scrolling the camera view."""
        pytest.skip("Requires running host process")

    def test_zoom_controls(self, host_client, api_key):
        """Test zoom in/out functionality."""
        pytest.skip("Requires running host process")