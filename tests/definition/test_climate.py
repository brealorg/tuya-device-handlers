"""Tests for climate definition."""

from typing import Any

import pytest
from tuya_sharing import CustomerDevice

from tests import create_device
from tests.device_wrapper import inject_dpcode
from tuya_device_handlers.definition.climate import get_default_definition
from tuya_device_handlers.device_wrapper.common import (
    DPCodeBooleanWrapper,
    DPCodeEnumWrapper,
    DPCodeIntegerWrapper,
)
from tuya_device_handlers.helpers.homeassistant import (
    TuyaClimateHVACMode,
    TuyaUnitOfTemperature,
)


@pytest.mark.parametrize(
    "unit", [TuyaUnitOfTemperature.CELSIUS, TuyaUnitOfTemperature.FAHRENHEIT]
)
def test_get_default_definition(unit: TuyaUnitOfTemperature) -> None:
    """Test get_default_definition."""
    device = create_device("kt_5wnlzekkstwcdsvm.json")
    assert (definition := get_default_definition(device, unit))
    assert not definition.current_humidity_wrapper
    assert isinstance(
        definition.current_temperature_wrapper, DPCodeIntegerWrapper
    )
    assert isinstance(definition.set_temperature_wrapper, DPCodeIntegerWrapper)
    assert isinstance(definition.fan_mode_wrapper, DPCodeEnumWrapper)
    assert not definition.hvac_mode_wrapper
    assert not definition.preset_wrapper
    assert isinstance(definition.switch_wrapper, DPCodeBooleanWrapper)
    assert not definition.swing_wrapper
    assert not definition.target_humidity_wrapper


@pytest.mark.parametrize(
    "unit", [TuyaUnitOfTemperature.CELSIUS, TuyaUnitOfTemperature.FAHRENHEIT]
)
def test_get_default_definition_with_convert(
    unit: TuyaUnitOfTemperature,
) -> None:
    """Test get_default_definition."""
    device = create_device("wk_B0eP8qYAdpUo4yR9.json")
    assert (definition := get_default_definition(device, unit))
    assert not definition.current_humidity_wrapper
    assert isinstance(
        definition.current_temperature_wrapper, DPCodeIntegerWrapper
    )
    assert isinstance(definition.set_temperature_wrapper, DPCodeIntegerWrapper)
    assert not definition.fan_mode_wrapper
    assert not definition.hvac_mode_wrapper
    assert not definition.preset_wrapper
    assert not definition.switch_wrapper
    assert not definition.swing_wrapper
    assert not definition.target_humidity_wrapper


@pytest.mark.parametrize(
    (
        "category",
        "mode_range",
        "status",
        "expected_options",
        "expected_hvac_mode",
    ),
    [
        # Preset-only mode with switch
        (
            "qn",
            '["comfor", "eco"]',
            {"mode": "comfor", "switch": True},
            [TuyaClimateHVACMode.HEAT],
            TuyaClimateHVACMode.HEAT,
        ),
        # Preset-only mode without switch
        (
            "wk",
            '["comfort", "eco"]',
            {"mode": "eco"},
            [TuyaClimateHVACMode.HEAT_COOL],
            TuyaClimateHVACMode.HEAT_COOL,
        ),
        # HVAC values and presets with switch
        (
            "qn",
            '["eco", "off"]',
            {"mode": "eco", "switch": True},
            [TuyaClimateHVACMode.OFF, TuyaClimateHVACMode.HEAT],
            TuyaClimateHVACMode.HEAT,
        ),
        (
            "qn",
            '["eco", "off"]',
            {"mode": "off", "switch": True},
            [TuyaClimateHVACMode.OFF, TuyaClimateHVACMode.HEAT],
            TuyaClimateHVACMode.OFF,
        ),
        (
            "kt",
            '["cold", "hot", "sleep"]',
            {"mode": "sleep", "switch": True},
            [TuyaClimateHVACMode.COOL, TuyaClimateHVACMode.HEAT],
            TuyaClimateHVACMode.COOL,
        ),
        # Unknown category keeps presets out of the HVAC modes
        (
            "category",
            '["comfor", "eco"]',
            {"mode": "comfor", "switch": True},
            [],
            None,
        ),
    ],
)
def test_get_default_definition_preset_hvac_mode(
    category: str,
    mode_range: str,
    status: dict[str, Any],
    expected_options: list[TuyaClimateHVACMode],
    expected_hvac_mode: TuyaClimateHVACMode | None,
    mock_device: CustomerDevice,
) -> None:
    """Test the HVAC mode reported while the device runs a preset."""
    mock_device.category = category
    inject_dpcode(
        mock_device,
        "mode",
        status["mode"],
        dptype="Enum",
        values=f'{{"range": {mode_range}}}',
    )
    if "switch" in status:
        inject_dpcode(mock_device, "switch", status["switch"], dptype="Boolean")

    definition = get_default_definition(
        mock_device, TuyaUnitOfTemperature.CELSIUS
    )

    assert definition.hvac_mode_wrapper
    assert definition.hvac_mode_wrapper.options == expected_options
    assert (
        definition.hvac_mode_wrapper.read_device_status(mock_device)
        == expected_hvac_mode
    )
    assert bool(definition.switch_wrapper) is ("switch" in status)


@pytest.mark.parametrize(
    ("mode_range", "mode", "hvac_mode", "expected_raw"),
    [
        # Keep the active preset
        ('["comfor", "eco"]', "comfor", TuyaClimateHVACMode.HEAT, "comfor"),
        # Switch from an HVAC value to the first preset
        ('["eco", "off"]', "off", TuyaClimateHVACMode.HEAT, "eco"),
        ('["eco", "off"]', "eco", TuyaClimateHVACMode.OFF, "off"),
    ],
)
def test_get_default_definition_set_preset_hvac_mode(
    mode_range: str,
    mode: str,
    hvac_mode: TuyaClimateHVACMode,
    expected_raw: str,
    mock_device: CustomerDevice,
) -> None:
    """Test setting the HVAC mode reported while the device runs a preset."""
    mock_device.category = "qn"
    inject_dpcode(
        mock_device,
        "mode",
        mode,
        dptype="Enum",
        values=f'{{"range": {mode_range}}}',
    )
    inject_dpcode(mock_device, "switch", True, dptype="Boolean")

    definition = get_default_definition(
        mock_device, TuyaUnitOfTemperature.CELSIUS
    )

    assert definition.hvac_mode_wrapper
    assert definition.hvac_mode_wrapper.get_update_commands(
        mock_device, hvac_mode
    ) == [{"code": "mode", "value": expected_raw}]
