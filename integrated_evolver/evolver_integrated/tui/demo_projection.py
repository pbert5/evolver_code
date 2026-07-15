"""Project canonical integrated-system objects into TUI demo rows."""
from __future__ import annotations


_COMPONENT_TYPE_TO_TUI_TYPE = {
    "pump_influx": "pump",
    "pump_efflux": "pump",
    "peristaltic_pump": "pump",
    "od_sensor": "sensor",
    "temperature_sensor": "sensor",
    "stirbar": "stirrer",
}

_DEVICE_TYPE_TO_TUI_TYPE = {
    "smart_sleeve": "smart_sleeve",
    "pump_rack": "pump_rack",
}

_EXPERIMENT_STATUS_TO_STATE = {
    "planned": "created",
    "preparing": "created",
    "running": "running",
    "paused": "paused",
    "completed": "stopped",
    "cancelled": "stopped",
    "failed": "failed",
}


def project_integrated_system_for_tui(system: dict) -> dict:
    """Return the legacy TUI demo shape from an IntegratedEvolverSystem."""
    components = {
        component["id"]: component
        for component in system.get("components", [])
        if isinstance(component, dict) and component.get("id")
    }
    devices = [
        _project_device(device)
        for device in system.get("devices", [])
        if isinstance(device, dict)
    ]
    component_devices = [
        _project_component(component)
        for component in system.get("components", [])
        if isinstance(component, dict)
    ]
    protocols = [
        _project_protocol(protocol, system)
        for protocol in system.get("protocols", [])
        if isinstance(protocol, dict)
    ]
    experiments = [
        _project_experiment(experiment)
        for experiment in system.get("experiments", [])
        if isinstance(experiment, dict)
    ]
    return {
        "experiments": experiments,
        "evolver_units": [
            _project_evolver(unit, components, system)
            for unit in system.get("evolver_units", [])
            if isinstance(unit, dict)
        ],
        "services": _demo_services(),
        "protocols": protocols,
        "materials": [
            _project_material(material)
            for material in system.get("materials", [])
            if isinstance(material, dict)
        ] + [
            _project_sample(sample)
            for sample in system.get("samples", [])
            if isinstance(sample, dict)
        ],
        "devices": devices + component_devices,
    }


def _project_evolver(unit: dict, components: dict, system: dict) -> dict:
    connected_components = [
        components[component_id]
        for component_id in unit.get("connected_component_ids", [])
        if component_id in components
    ]
    state = (
        "active"
        if unit.get("state") == "available"
        else unit.get("state", "unknown")
    )
    return {
        "id": unit.get("id"),
        "name": unit.get("name"),
        "unit_type": unit.get("unit_type"),
        "state": state,
        "role": "two-vial-demo",
        "command_interface": "stubbed_virtual_evolver",
        "notes": unit.get("notes"),
        "devices": [
            _project_component(component)
            for component in connected_components
        ],
    }


def _project_device(device: dict) -> dict:
    device_type = device.get("device_type", "other")
    return {
        "id": device.get("id"),
        "name": device.get("name"),
        "type": _DEVICE_TYPE_TO_TUI_TYPE.get(device_type, device_type),
        "device_type": device_type,
        "io_role": device.get("id"),
        "evolver_id": device.get("parent_unit_id"),
    }


def _project_component(component: dict) -> dict:
    component_type = component.get("component_type", "other")
    return {
        "id": component.get("id"),
        "name": component.get("name"),
        "type": _COMPONENT_TYPE_TO_TUI_TYPE.get(component_type, component_type),
        "component_type": component_type,
        "io_role": component.get("role", component.get("id")),
        "evolver_id": component.get("parent_unit_id"),
        "action_stub": _action_stub_for_component(component_type),
    }


def _project_protocol(protocol: dict, system: dict) -> dict:
    algorithms = {
        algorithm["id"]: algorithm
        for algorithm in system.get("algorithms", [])
        if isinstance(algorithm, dict) and algorithm.get("id")
    }
    algorithm = algorithms.get(protocol.get("algorithm_id"), {})
    return {
        "id": protocol.get("id"),
        "name": protocol.get("name"),
        "description": protocol.get("description"),
        "protocol_type": protocol.get("protocol_type"),
        "version": protocol.get("version"),
        "algorithm": algorithm,
        "algorithm_id": protocol.get("algorithm_id"),
        "required_materials": protocol.get("required_materials", []),
        "initial_conditions": protocol.get("initial_conditions", []),
        "run_blocking_placeholders": _run_blocking_placeholders(protocol),
        "steps": [
            _project_step(step)
            for step in protocol.get("steps", [])
            if isinstance(step, dict)
        ],
    }


def _project_step(step: dict) -> dict:
    components = []
    for config in step.get("component_configurations", []):
        components.append({
            "name": config.get("role", config.get("component_id")),
            "type": "component",
            "io_role": config.get("role"),
            "component_id": config.get("component_id"),
            "enabled": True,
        })
    for material_input in step.get("material_inputs", []):
        material_id = material_input.get("material_id")
        components.append({
            "name": material_id,
            "type": "material",
            "io_role": material_input.get("input_type"),
            "material_id": material_id,
            "enabled": True,
        })
    for action_id in step.get("action_ids", []):
        components.append({
            "name": action_id,
            "type": "action",
            "io_role": "runtime_action",
            "enabled": True,
        })
    if not components:
        components.append({
            "name": step.get("step_type", "step"),
            "type": "step",
            "io_role": step.get("execution_mode"),
            "enabled": True,
        })
    return {
        "id": step.get("id"),
        "name": step.get("name"),
        "description": step.get("description"),
        "step_type": step.get("step_type"),
        "execution_mode": step.get("execution_mode"),
        "components": components,
        "fixed_parameters": step.get("fixed_parameters", []),
        "gates": step.get("gates", []),
        "objectives": step.get("objectives", []),
    }


def _project_material(material: dict) -> dict:
    return {
        "id": material.get("id"),
        "name": material.get("name"),
        "type": material.get("material_type"),
        "material_type": material.get("material_type"),
        "lot": material.get("lot", ""),
        "placeholder": material.get("placeholder", False),
        "run_blocking": material.get("run_blocking_if_unresolved", False),
        "required_fields": material.get("required_setup_fields", []),
        "description": material.get("description", ""),
    }


def _project_sample(sample: dict) -> dict:
    return {
        "id": sample.get("id"),
        "name": sample.get("name"),
        "type": sample.get("sample_type", "sample"),
        "sample_type": sample.get("sample_type"),
        "placeholder": sample.get("placeholder", False),
        "run_blocking": sample.get("run_blocking_if_unresolved", False),
        "required_fields": sample.get("required_setup_fields", []),
        "description": sample.get("description", ""),
    }


def _project_experiment(experiment: dict) -> dict:
    protocol_id = experiment.get("protocol_id", "default")
    unit_id = _experiment_unit_id(experiment)
    return {
        "id": experiment.get("id"),
        "state": _EXPERIMENT_STATUS_TO_STATE.get(
            experiment.get("status"), experiment.get("status", "created")
        ),
        "created_at": "demo",
        "run_readiness": experiment.get("run_readiness", {}),
        "request": {
            "name": experiment.get("name"),
            "machine_id": unit_id,
            "vials": _experiment_vials(experiment),
            "metadata": {"protocol": protocol_id},
        },
        "protocol_id": protocol_id,
    }


def _experiment_unit_id(experiment: dict) -> str:
    for assignment in experiment.get("device_assignments", []):
        if assignment.get("unit_id"):
            return assignment["unit_id"]
    return "machine-1"


def _experiment_vials(experiment: dict) -> list[int]:
    vials = []
    for assignment in experiment.get("device_assignments", []):
        role = str(assignment.get("role", ""))
        if role.startswith("vial_"):
            try:
                vials.append(int(role.split("_", 1)[1]))
            except ValueError:
                pass
    return vials or [0]


def _run_blocking_placeholders(protocol: dict) -> list[str]:
    placeholders = []
    for requirement in protocol.get("required_materials", []):
        if requirement.get("run_blocking_if_unresolved"):
            placeholders.append(requirement.get("material_id"))
    return [placeholder for placeholder in placeholders if placeholder]


def _action_stub_for_component(component_type: str) -> str:
    if component_type in {"pump_influx", "pump_efflux", "peristaltic_pump"}:
        return "virtual_evolver.run_pump"
    if component_type == "od_sensor":
        return "virtual_evolver.read_od"
    if component_type == "temperature_sensor":
        return "virtual_evolver.read_temperature"
    if component_type == "stirbar":
        return "virtual_evolver.set_stir"
    return ""


def _demo_services() -> list[dict]:
    return [
        {
            "id": "control-plane",
            "name": "Control Plane",
            "state": "running",
            "category": "core",
            "restart_count": 0,
            "last_action": "start",
            "description": "Local HTTP API and lifecycle coordinator.",
        },
        {
            "id": "virtual-evolver",
            "name": "Virtual eVOLVER",
            "state": "running",
            "category": "runtime",
            "restart_count": 0,
            "last_action": "start",
            "description": "Stub target for demo min-eVOLVER actions.",
        },
    ]
