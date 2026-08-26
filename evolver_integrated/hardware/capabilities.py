"""Verified min-eVOLVER actuator capability projection.

This descriptor deliberately describes the audited commissioning protocol, not
what a UI might wish the hardware could do.  In particular, a heater pulse is
not a temperature setpoint and a timed pump pulse is not a volume dispense.
"""
from __future__ import annotations

from .protocol import HW_PROTOCOL_VERSION

DEVICE_PROTOCOL_VERSION = "evolver.device.v2"


def minievolver_capabilities() -> dict:
    return {
        "device_protocol_version": DEVICE_PROTOCOL_VERSION,
        "firmware_hardware_protocol": HW_PROTOCOL_VERSION,
        "pump": {
            "supported": True,
            "channels": 6,
            "command_modes": ["timed_pulse"],
            "directions": ["forward"],
            "duration": {"unit": "ms", "minimum": 1, "maximum": 1000},
            "volumetric_dispense": {"supported": False, "reason": "firmware exposes time only"},
            "physical_feedback": False,
        },
        "stir": {
            "supported": True,
            "channels": 2,
            "modes": ["pwm_pulse"],
            "level": {"unit": "pwm", "minimum": 1, "maximum": 250},
            "duration": {"unit": "ms", "minimum": 1, "maximum": 1000},
            "rpm_feedback": False,
        },
        "temperature": {
            "observed": True,
            "closed_loop_setpoint": False,
            "heater_output_pulse": {"supported": True, "unit": "pwm", "minimum": 1, "maximum": 64},
            "unit": "C",
        },
        "safe_stop": {"supported": True, "scope": "all_outputs", "operation": "HW_SAFE"},
    }
