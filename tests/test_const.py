"""Tests for const.py."""
from custom_components.xbox_dev_mode.const import (
    DOMAIN,
    DEFAULT_PORT,
    STATE_DEV,
    STATE_RETAIL,
    STATE_OFF,
    DEFAULT_SCAN_INTERVAL,
)


def test_constants():
    """Test that constants are defined with expected values."""
    assert DOMAIN == "xbox_dev_mode"
    assert DEFAULT_PORT == 11443
    assert {STATE_DEV, STATE_RETAIL, STATE_OFF} == {"dev_mode", "retail", "off"}
    assert DEFAULT_SCAN_INTERVAL == 30
