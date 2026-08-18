"""Protocol 2 parsing, kept separate from UI and test orchestration."""
from __future__ import annotations

from dataclasses import dataclass

HANDSHAKE = "WHO_ARE_YOU_!"


@dataclass(frozen=True)
class DeviceIdentity:
    protocol: int
    device_id: str
    firmware: str
    device_type: str
    raw: str


def parse_identity(response: str) -> DeviceIdentity:
    """Parse ``MEV|2|...`` identity replies, rejecting unrelated ACM devices."""
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
    metadata = {}
    for item in fields[5].split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            metadata[key] = value
    if metadata.get("type") != "minievolver":
        raise ValueError("identity reply is not from a min-eVOLVER")
    return DeviceIdentity(protocol, metadata.get("id", fields[2]), metadata.get("fw", "unknown"), metadata["type"], raw)
