"""Wire format for the normal and commissioning min-eVOLVER protocols."""
from __future__ import annotations

from dataclasses import dataclass

HANDSHAKE = "WHO_ARE_YOU_!"
HW_PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class DeviceIdentity:
    protocol: int
    device_id: str
    firmware: str
    device_type: str
    hw_protocol: int
    raw: str


@dataclass(frozen=True)
class HardwareReply:
    version: int
    operation: str
    fields: dict[str, str]
    raw: str


def parse_identity(response: str) -> DeviceIdentity:
    """Parse a ``MEV|2|...`` identity reply, rejecting unrelated ACM devices."""
    raw = response.strip()
    fields = raw.split("|")
    if len(fields) < 6 or fields[0] != "MEV":
        raise ValueError("response is not a min-eVOLVER identity reply")
    try:
        protocol = int(fields[1])
    except ValueError as exc:
        raise ValueError("invalid min-eVOLVER protocol version") from exc
    if protocol != 2:
        raise ValueError(f"unsupported min-eVOLVER protocol {protocol}")
    metadata = dict(item.split("=", 1) for item in fields[5].split(",") if "=" in item)
    if metadata.get("type") != "minievolver":
        raise ValueError("identity reply is not from a min-eVOLVER")
    try:
        hw_protocol = int(metadata.get("hw_proto", "0"))
    except ValueError as exc:
        raise ValueError("invalid hardware protocol version") from exc
    return DeviceIdentity(protocol, metadata.get("id", fields[2]), metadata.get("fw", "unknown"), metadata["type"], hw_protocol, raw)


def _integer(value: int, name: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def hw_command(operation: str, *arguments: int) -> str:
    """Build the only accepted commissioning command grammar."""
    return operation + ("," + ",".join(str(argument) for argument in arguments) if arguments else "") + "_!"


def hw_status_command() -> str: return hw_command("HW_STATUS")
def hw_safe_command() -> str: return hw_command("HW_SAFE")
def read_thermistor_command(channel: int) -> str: return hw_command("HW_READ_THERMISTOR", _integer(channel, "channel", 0, 1))
def read_photodiode_command(channel: int) -> str: return hw_command("HW_READ_PHOTODIODE", _integer(channel, "channel", 0, 1))
def set_od_led_command(channel: int, level: int) -> str: return hw_command("HW_SET_OD_LED", _integer(channel, "channel", 0, 1), _integer(level, "level", 0, 255))
def pulse_pump_command(channel: int, duration_ms: int) -> str: return hw_command("HW_PULSE_PUMP", _integer(channel, "channel", 0, 5), _integer(duration_ms, "duration_ms", 1, 1000))
def pulse_stir_command(channel: int, duration_ms: int, level: int) -> str: return hw_command("HW_PULSE_STIR", _integer(channel, "channel", 0, 1), _integer(duration_ms, "duration_ms", 1, 1000), _integer(level, "level", 1, 250))
def pulse_heater_command(channel: int, duration_ms: int, level: int) -> str: return hw_command("HW_PULSE_HEATER", _integer(channel, "channel", 0, 1), _integer(duration_ms, "duration_ms", 1, 250), _integer(level, "level", 1, 64))


def parse_hardware_reply(response: str, expected_operation: str | None = None) -> HardwareReply:
    raw = response.strip()
    parts = raw.split("|")
    if len(parts) < 4 or parts[0] != "HW":
        raise ValueError("response is not a hardware protocol reply")
    try:
        version = int(parts[1])
    except ValueError as exc:
        raise ValueError("invalid hardware protocol version") from exc
    if version < HW_PROTOCOL_VERSION:
        raise ValueError(f"unsupported hardware protocol {version}")
    status, operation = parts[2], parts[3]
    fields = dict(item.split("=", 1) for item in parts[4].split(",") if "=" in item) if len(parts) > 4 else {}
    if status == "ERR":
        raise ValueError(f"hardware command {operation} failed: {fields.get('reason', 'unknown_error')}")
    if status != "OK":
        raise ValueError("invalid hardware response status")
    if expected_operation and operation != expected_operation:
        raise ValueError(f"expected hardware response {expected_operation}, got {operation}")
    return HardwareReply(version, operation, fields, raw)
