import pytest
from core.exceptions import (
    GeoGuessrError,
    HostError,
    HostTimeoutError,
    HostResponseError,
    NavigationError,
    InvalidStateError,
    InvalidCommandError,
    DirectionNotAvailableError,
    ToolError,
    MissingContextError,
    InvalidArgumentError,
)


class TestExceptionHierarchy:
    """Test exception inheritance."""

    def test_host_errors_inherit_from_geoguessr_error(self):
        assert issubclass(HostError, GeoGuessrError)
        assert issubclass(HostTimeoutError, HostError)
        assert issubclass(HostResponseError, HostError)
    
    def test_navigation_errors_inherit_from_geoguessr_error(self):
        assert issubclass(NavigationError, GeoGuessrError)
        assert issubclass(InvalidStateError, NavigationError)
        assert issubclass(InvalidCommandError, NavigationError)
        assert issubclass(DirectionNotAvailableError, NavigationError)
    
    def test_tool_errors_inherit_from_geoguessr_error(self):
        assert issubclass(ToolError, GeoGuessrError)
        assert issubclass(MissingContextError, ToolError)
        assert issubclass(InvalidArgumentError, ToolError)


class TestHostTimeoutError:
    def test_basic_message(self):
        exc = HostTimeoutError(method="getState", timeout=30)
        assert "getState" in str(exc)
        assert "30" in str(exc)
        assert exc.method == "getState"
        assert exc.timeout == 30
    
    def test_with_req_id(self):
        exc = HostTimeoutError(method="setPov", timeout=30, req_id=42)
        assert "req_id=42" in str(exc)
        assert exc.req_id == 42


class TestHostResponseError:
    def test_basic_message(self):
        exc = HostResponseError(error="session_not_found")
        assert "session_not_found" in str(exc)
        assert exc.error == "session_not_found"
    
    def test_with_method(self):
        exc = HostResponseError(error="invalid_pano", method="setPano")
        assert "setPano" in str(exc)
        assert "invalid_pano" in str(exc)


class TestInvalidStateError:
    def test_message(self):
        exc = InvalidStateError("missing panoId")
        assert "missing panoId" in str(exc)
        assert exc.reason == "missing panoId"


class TestInvalidCommandError:
    def test_message(self):
        exc = InvalidCommandError("method required")
        assert "method required" in str(exc)


class TestDirectionNotAvailableError:
    def test_basic_message(self):
        exc = DirectionNotAvailableError("north")
        assert "north" in str(exc)
        assert exc.direction == "north"
    
    def test_with_available_directions(self):
        exc = DirectionNotAvailableError("north", available=["south", "east"])
        assert "south" in str(exc)
        assert "east" in str(exc)


class TestMissingContextError:
    def test_message(self):
        exc = MissingContextError("host_client")
        assert "host_client" in str(exc)
        assert exc.key == "host_client"


class TestInvalidArgumentError:
    def test_basic_message(self):
        exc = InvalidArgumentError("delta")
        assert "delta" in str(exc)
    
    def test_with_reason(self):
        exc = InvalidArgumentError("lat", reason="must be between -90 and 90")
        assert "lat" in str(exc)
        assert "must be between" in str(exc)


class TestExceptionCatching:
    """Test that exceptions can be caught at different levels."""
    
    def test_catch_specific_then_base(self):
        """Verify catching works at multiple levels."""
        exc = HostTimeoutError("test", 30)
        
        # Can catch as specific type
        with pytest.raises(HostTimeoutError):
            raise exc
        
        # Can catch as HostError
        with pytest.raises(HostError):
            raise exc
        
        # Can catch as GeoGuessrError
        with pytest.raises(GeoGuessrError):
            raise exc
        
        # Can catch as Exception
        with pytest.raises(Exception):
            raise exc