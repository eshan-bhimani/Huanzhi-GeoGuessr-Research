"""Unit tests for core.navigation.protocol module."""

import json
import pytest
from core.navigation.protocol import (
    parse_state,
    build_command,
    dump_command,
    REQUIRED_STATE_KEYS,
    REQUIRED_POV_KEYS,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def valid_state():
    return {
        "panoId": "abc123",
        "pov": {"heading": 90.0, "pitch": 0.0, "zoom": 1.0},
        "links": [{"heading": 45.0, "panoId": "northeastpano"}],
    }

@pytest.fixture
def valid_state_json(valid_state):
    return json.dumps(valid_state)

# ─────────────────────────────────────────────────────────────
# Tests: parse_state
# ─────────────────────────────────────────────────────────────
class TestParseState:
    def test_valid_state(self, valid_state_json, valid_state):
        result = parse_state(valid_state_json)
        assert result == valid_state

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="invalid_state_json"):
            parse_state("not valid json {")

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="invalid_state"):
            parse_state('"just a string"')

    def test_array_raises(self):
        with pytest.raises(ValueError, match="invalid_state"):
            parse_state('[1, 2, 3]')

    @pytest.mark.parametrize("missing_key", REQUIRED_STATE_KEYS)
    def test_missing_state_key_raises(self, valid_state, missing_key):
        del valid_state[missing_key]
        with pytest.raises(ValueError, match="missing_state_keys"):
            parse_state(json.dumps(valid_state))

    def test_pov_not_dict_raises(self, valid_state):
        valid_state["pov"] = "not a dict"
        with pytest.raises(ValueError, match="invalid_pov"):
            parse_state(json.dumps(valid_state))

    @pytest.mark.parametrize("missing_key", REQUIRED_POV_KEYS)
    def test_missing_pov_key_raises(self, valid_state, missing_key):
        del valid_state["pov"][missing_key]
        with pytest.raises(ValueError, match="missing_pov_keys"):
            parse_state(json.dumps(valid_state))

    def test_links_not_list_raises(self, valid_state):
        valid_state["links"] = {"not": "a list"}
        with pytest.raises(ValueError, match="invalid_links"):
            parse_state(json.dumps(valid_state))

    def test_empty_links_allowed(self, valid_state):
        valid_state["links"] = []
        result = parse_state(json.dumps(valid_state))
        assert result["links"] == []

# ─────────────────────────────────────────────────────────────
# Tests: build_command
# ─────────────────────────────────────────────────────────────
class TestBuildCommand:
    def test_valid_command(self):
        cmd = build_command("setPov", {"heading": 90.0})
        assert cmd == {"method": "setPov", "params": {"heading": 90.0}}

    def test_empty_params(self):
        cmd = build_command("getState", {})
        assert cmd == {"method": "getState", "params": {}}

    def test_none_method_raises(self):
        with pytest.raises(ValueError):
            build_command(None, {})

    def test_non_dict_params_raises(self):
        with pytest.raises(ValueError):
            build_command("setPov", "not a dict")


# ─────────────────────────────────────────────────────────────
# Tests: dump_command
# ─────────────────────────────────────────────────────────────
class TestDumpCommand:
    def test_valid_dump(self):
        cmd = {"method": "setPov", "params": {"heading": 90.0}}
        result = dump_command(cmd)
        assert json.loads(result) == cmd

    def test_compact_json(self):
        cmd = {"method": "setPov", "params": {"heading": 90.0}}
        result = dump_command(cmd)
        # Should not contain spaces after separators
        assert ": " not in result
        assert ", " not in result

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="Invalid command format"):
            dump_command("not a dict")

    def test_missing_method_raises(self):
        with pytest.raises(ValueError, match="Missing required command keys"):
            dump_command({"params": {}})

    def test_missing_params_raises(self):
        with pytest.raises(ValueError, match="Missing required command keys"):
            dump_command({"method": "setPov"})