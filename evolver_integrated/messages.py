"""Versioned message contracts for the integrated eVOLVER architecture."""

from __future__ import absolute_import

import datetime
import uuid


SCHEMA_VERSION = "evolver.v1"

EVENT_MACHINE_RAW_MEASUREMENT = "machine.measurement.raw"
EVENT_EXPERIMENT_STATUS = "experiment.status"
EVENT_EXPERIMENT_RUNNER_ACTION = "experiment.runner.action"
EVENT_JOB_STATUS = "job.status"
EVENT_DEVICE_COMMAND = "device.command.request"

# Actuator requests use this contract.  The legacy ``param``/``value`` form
# remains accepted below for existing DPU clients, but new callers must use
# an explicit operation and structured target/parameters.
DEVICE_PROTOCOL_VERSION = "evolver.device.v2"
DEVICE_OPERATIONS = frozenset({
    "pump_pulse",
    "pump_stop",
    "stir_pulse",
    "safe_stop",
})


class MessageValidationError(ValueError):
    """Raised when an interprocess message does not match the v1 contract."""


def utc_now_iso():
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def make_envelope(kind, payload, producer, message_id=None, created_at=None):
    """Create a versioned message envelope shared by local services."""
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "id": message_id or str(uuid.uuid4()),
        "created_at": created_at or utc_now_iso(),
        "producer": producer,
        "payload": payload,
    }
    return validate_envelope(envelope)


def validate_envelope(message, allowed_kinds=None):
    if not isinstance(message, dict):
        raise MessageValidationError("message must be a dictionary")

    required = [
        "schema_version",
        "kind",
        "id",
        "created_at",
        "producer",
        "payload",
    ]
    for field in required:
        if field not in message:
            raise MessageValidationError(
                "message is missing required field: " + field
            )

    if message["schema_version"] != SCHEMA_VERSION:
        raise MessageValidationError(
            "unsupported schema version: " + str(message["schema_version"])
        )

    for field in ["kind", "id", "created_at", "producer"]:
        if not isinstance(message[field], str) or not message[field]:
            raise MessageValidationError(field + " must be a non-empty string")

    if allowed_kinds is not None and message["kind"] not in allowed_kinds:
        raise MessageValidationError(
            "unexpected message kind: " + message["kind"]
        )

    if not isinstance(message["payload"], dict):
        raise MessageValidationError("payload must be a dictionary")

    return {
        "schema_version": message["schema_version"],
        "kind": message["kind"],
        "id": message["id"],
        "created_at": message["created_at"],
        "producer": message["producer"],
        "payload": dict(message["payload"]),
    }


def make_raw_measurement(
    machine_id,
    measurements,
    producer,
    observed_at=None,
    metadata=None,
):
    payload = validate_raw_measurement_payload(
        {
            "machine_id": machine_id,
            "observed_at": observed_at or utc_now_iso(),
            "measurements": measurements,
            "metadata": metadata or {},
        }
    )
    return make_envelope(EVENT_MACHINE_RAW_MEASUREMENT, payload, producer)


def validate_raw_measurement_payload(payload):
    _require_dict(payload, "raw measurement payload")
    _require_non_empty_string(payload, "machine_id")
    _require_non_empty_string(payload, "observed_at")

    measurements = payload.get("measurements")
    if not isinstance(measurements, dict) or not measurements:
        raise MessageValidationError(
            "measurements must be a non-empty dictionary"
        )

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise MessageValidationError("metadata must be a dictionary")

    return {
        "machine_id": payload["machine_id"],
        "observed_at": payload["observed_at"],
        "measurements": dict(measurements),
        "metadata": dict(metadata),
    }


def validate_experiment_request(payload):
    _require_dict(payload, "experiment request")
    _require_non_empty_string(payload, "name")
    _require_non_empty_string(payload, "machine_id")

    vials = payload.get("vials")
    if not isinstance(vials, list) or not vials:
        raise MessageValidationError("vials must be a non-empty list")

    config = payload.get("config", {})
    metadata = payload.get("metadata", {})
    for field, value in [("config", config), ("metadata", metadata)]:
        if not isinstance(value, dict):
            raise MessageValidationError(field + " must be a dictionary")

    return {
        "name": payload["name"],
        "machine_id": payload["machine_id"],
        "vials": list(vials),
        "config": dict(config),
        "metadata": dict(metadata),
    }


def validate_device_command_request(payload):
    _require_dict(payload, "device command request")

    if "operation" in payload:
        return _validate_typed_device_command(payload)

    _require_non_empty_string(payload, "param")

    if "value" not in payload:
        raise MessageValidationError("device command request is missing value")

    command = {
        "param": payload["param"],
        "value": payload["value"],
    }

    for field in ["immediate", "recurring"]:
        if field in payload:
            if not isinstance(payload[field], bool):
                raise MessageValidationError(field + " must be a boolean")
            command[field] = payload[field]

    for field in ["fields_expected_outgoing", "fields_expected_incoming"]:
        if field in payload:
            if not isinstance(payload[field], int) or payload[field] <= 0:
                raise MessageValidationError(
                    field + " must be a positive integer"
                )
            command[field] = payload[field]

    for field in ["machine_id", "experiment_id", "runner_id"]:
        if field in payload:
            _require_non_empty_string(payload, field)
            command[field] = payload[field]

    return command


def _validate_typed_device_command(payload):
    """Validate the cross-layer actuator request without building wire text."""
    schema_version = payload.get("schema_version", DEVICE_PROTOCOL_VERSION)
    if schema_version != DEVICE_PROTOCOL_VERSION:
        raise MessageValidationError("unsupported device protocol version: " + str(schema_version))
    operation = payload.get("operation")
    if not isinstance(operation, str) or operation not in DEVICE_OPERATIONS:
        raise MessageValidationError("unsupported device operation: " + str(operation))
    target = payload.get("target")
    parameters = payload.get("parameters", {})
    context = payload.get("context", {})
    if not isinstance(target, dict) or not target.get("device_id"):
        raise MessageValidationError("typed device command target.device_id is required")
    if not isinstance(parameters, dict) or not isinstance(context, dict):
        raise MessageValidationError("typed device command parameters and context must be objects")
    if operation in {"pump_pulse", "pump_stop", "stir_pulse"}:
        channel = parameters.get("channel")
        if not isinstance(channel, int) or channel < 0:
            raise MessageValidationError("device channel must be a non-negative integer")
        maximum = 5 if operation in {"pump_pulse", "pump_stop"} else 1
        if channel > maximum:
            raise MessageValidationError(f"device channel must be in 0..{maximum}")
    if operation == "pump_pulse":
        if parameters.get("direction", "forward") != "forward":
            raise MessageValidationError("reverse pumping is unsupported by firmware")
        duration = parameters.get("duration_ms")
        if not isinstance(duration, int) or not 1 <= duration <= 1000:
            raise MessageValidationError("pump duration_ms must be an integer in 1..1000")
    if operation == "stir_pulse":
        duration, level = parameters.get("duration_ms"), parameters.get("level")
        if not isinstance(duration, int) or not 1 <= duration <= 1000:
            raise MessageValidationError("stir duration_ms must be an integer in 1..1000")
        if not isinstance(level, int) or not 1 <= level <= 250:
            raise MessageValidationError("stir level must be an integer in 1..250")
    if operation == "pump_stop" and "channel" in parameters and (
        not isinstance(parameters["channel"], int) or parameters["channel"] < 0
    ):
        raise MessageValidationError("device channel must be a non-negative integer")
    if "command_id" not in payload:
        raise MessageValidationError("typed device command command_id is required")
    _require_non_empty_string(payload, "command_id")
    return {
        "schema_version": schema_version,
        "command_id": payload["command_id"],
        "operation": operation,
        "target": dict(target),
        "parameters": dict(parameters),
        "context": dict(context),
    }


def make_experiment_status(experiment_id, state, producer, reason=None):
    payload = {
        "experiment_id": experiment_id,
        "state": state,
    }
    if reason:
        payload["reason"] = reason
    return make_envelope(EVENT_EXPERIMENT_STATUS, payload, producer)


def _require_dict(value, context):
    if not isinstance(value, dict):
        raise MessageValidationError(context + " must be a dictionary")


def _require_non_empty_string(payload, field):
    if not isinstance(payload.get(field), str) or not payload.get(field):
        raise MessageValidationError(field + " must be a non-empty string")
