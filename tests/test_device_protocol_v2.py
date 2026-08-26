import pytest

from evolver_integrated.hardware.capabilities import minievolver_capabilities
from evolver_integrated.messages import MessageValidationError, validate_device_command_request


def test_verified_capabilities_are_truthful_about_actuators():
    capabilities = minievolver_capabilities()
    assert capabilities["pump"]["channels"] == 6
    assert capabilities["pump"]["directions"] == ["forward"]
    assert capabilities["pump"]["volumetric_dispense"]["supported"] is False
    assert capabilities["stir"]["modes"] == ["pwm_pulse"]
    assert capabilities["temperature"]["closed_loop_setpoint"] is False


def _command(**overrides):
    command = {
        "schema_version": "evolver.device.v2",
        "command_id": "cmd-1",
        "operation": "pump_pulse",
        "target": {"device_id": "MEV-001", "resource": "pump"},
        "parameters": {"channel": 0, "duration_ms": 500, "direction": "forward"},
        "context": {"run_id": "run-1", "controller_generation": 2},
    }
    command.update(overrides)
    return command


def test_typed_pump_request_is_normalized_without_wire_text():
    result = validate_device_command_request(_command())
    assert result["operation"] == "pump_pulse"
    assert result["parameters"]["duration_ms"] == 500


@pytest.mark.parametrize("parameters", [
    {"channel": 6, "duration_ms": 500},
    {"channel": -1, "duration_ms": 500},
])
def test_typed_pump_channel_bounds_are_rejected_before_translation(parameters):
    with pytest.raises(MessageValidationError):
        validate_device_command_request(_command(parameters=parameters))


def test_typed_protocol_version_mismatch_is_rejected_before_translation():
    with pytest.raises(MessageValidationError, match="unsupported device protocol version"):
        validate_device_command_request(_command(schema_version="evolver.device.v1"))


@pytest.mark.parametrize("parameters", [
    {"channel": 0, "duration_ms": 0},
    {"channel": 0, "duration_ms": 1001},
    {"channel": 0, "duration_ms": 500, "direction": "reverse"},
])
def test_typed_safety_rejections_happen_before_translation(parameters):
    with pytest.raises(MessageValidationError):
        validate_device_command_request(_command(parameters=parameters))
