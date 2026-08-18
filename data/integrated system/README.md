# Integrated eVOLVER System Schemas

This directory contains the project-owned schemas for the integrated eVOLVER
runtime and related tooling.

The external examples in `../known_external_examples` are references for
vocabulary and LinkML style only. They should not be treated as canonical for
this project because the integrated eVOLVER model needs operational concepts
that the plate/submission schemas do not cover: devices, components,
connections, calibrations, protocols, runtime actions, inventory timelines,
algorithms, forms, and contextual documentation references.

## Files

- `integrated_evolver_schema.linkml.yml`: root schema and tree-root container.
- `schemas/base.yaml`: shared entities, quantities, agents, and parameters.
- `schemas/hardware.yaml`: eVOLVER units, devices, components,
  connections, device events, and maintenance flags.
- `schemas/inventory.yaml`: materials, samples, containers, recipes,
  mixtures, storage, and expiration policy.
- `schemas/calibration.yaml`: temperature, OD, OD blank, pump, and
  invalidation-condition records.
- `schemas/actions.yaml`: action templates and action executions for
  TUI/CLI/API/hardware commands.
- `schemas/algorithms.yaml`: growth curve, chemostat, turbidostat, media
  requirement, and related equations.
- `schemas/protocol.yaml`: protocol templates, steps, gates, objectives,
  component configs, material inputs, and inventory timelines.
- `schemas/experiment.yaml`: concrete experiment runs, assignments,
  overrides, calibration references, and action logs.
- `schemas/interface.yaml`: documentation references and generated form
  definitions.
- `objects/software/tui/*.json`: project-owned TUI runtime object fixtures,
  action catalogs, form templates, and architecture metadata.
- `objects/demo_integrated_system.json`: canonical schema-shaped
  `IntegratedEvolverSystem` demo object graph used as the source for projected
  UI demo data.

## Modeling Direction

The schema is organized around a root `IntegratedEvolverSystem` document with
separate collections for physical inventory, hardware, protocols, experiments,
actions, algorithms, forms, and documentation references.

References between objects use IDs so the same material, calibration, device,
or action can be reused by multiple protocols and experiments.

Python code should eventually load and validate JSON/YAML documents against
these schemas instead of owning this structure directly.

## Diagrams

### Schema Module Dependencies

Each schema module imports only what it needs. The layering keeps lower-level
modules free of protocol/experiment knowledge.

```mermaid
flowchart TD
    types["linkml:types"]
    base["base\nNamedEntity · Quantity · ParameterSetting · enums"]
    hardware["hardware\nEvolverUnit · Device · Component · Connection"]
    inventory["inventory\nMaterial · Container · ResearchSample · Recipe"]
    calibration["calibration\nCalibrationRecord"]
    actions["actions\nActionTemplate · ActionExecution"]
    algorithms["algorithms\nAlgorithm · Equation"]
    protocol["protocol\nProtocol · ProtocolStep · Gate · Objective"]
    experiment["experiment\nExperiment · DeviceAssignment · RunReadiness"]
    interface["interface\nFormDefinition · DocumentationReference"]

    types --> base
    base --> hardware
    base --> inventory
    hardware --> inventory
    base --> calibration
    hardware --> calibration
    inventory --> calibration
    base --> actions
    hardware --> actions
    base --> algorithms
    actions --> algorithms
    base --> protocol
    hardware --> protocol
    inventory --> protocol
    calibration --> protocol
    actions --> protocol
    algorithms --> protocol
    base --> experiment
    hardware --> experiment
    inventory --> experiment
    calibration --> experiment
    actions --> experiment
    protocol --> experiment
    base --> interface
    actions --> interface
```

### Root Document Collections

`IntegratedEvolverSystem` is the tree root. All other objects live in one of
its top-level lists and are cross-referenced by ID.

```mermaid
flowchart LR
    root([IntegratedEvolverSystem])

    root --> hw["Hardware\nevolver_units · devices · components"]
    root --> inv["Inventory\nmaterials · containers · samples"]
    root --> cal["calibrations"]
    root --> proto["protocols"]
    root --> exp["experiments"]
    root --> act["action_templates"]
    root --> alg["algorithms"]
    root --> ui["UI\nforms · documentation"]
```

### Hardware Layer

`EvolverUnit` is the physical chassis. It owns `Device` records (sensors,
pumps, vials) which are composed of `Component` records (sensor channels,
pump ports, stir bars). `Connection` edges wire components together.

```mermaid
classDiagram
    class EvolverUnit {
        +unit_type: EvolverUnitTypeEnum
        +state: OperationalStateEnum
        +serial_number
        +location
    }
    class Device {
        +device_type: DeviceTypeEnum
        +state: OperationalStateEnum
        +manufacturer · model
        +current_activity
        +last_used_at: datetime
    }
    class Component {
        +component_type: ComponentTypeEnum
        +direction: ComponentDirectionEnum
        +channel
        +state: OperationalStateEnum
    }
    class Connection {
        +connection_type: ConnectionTypeEnum
        +source_id · target_id
        +directionality: DirectionalityEnum
        +medium
    }
    class DeviceEvent {
        +event_type: DeviceEventTypeEnum
        +occurred_at: datetime
        +summary
    }
    class MaintenanceFlag {
        +flag_type: MaintenanceFlagTypeEnum
        +severity: SeverityEnum
        +resolved_at: datetime
    }

    EvolverUnit "1" --> "*" Device : connected_device_ids
    EvolverUnit "1" --> "*" Component : connected_component_ids
    Device --> EvolverUnit : parent_unit_id
    Device "1" --> "*" Component : component_ids
    Device "1" --> "*" Connection : connection_ids
    Device "1" *-- "*" DeviceEvent : history
    Device "1" *-- "*" MaintenanceFlag : maintenance_flags
    Component --> Device : parent_device_id
    Component "1" --> "*" Connection : connection_ids
```

### Inventory and Calibration

`Material` and `ResearchSample` are the biological inputs. `Container` is
the physical vessel. `CalibrationRecord` ties sensor accuracy to a specific
device or component and carries invalidation conditions.

```mermaid
classDiagram
    class Material {
        +material_type: MaterialTypeEnum
        +organism · strain_name · genotype
        +lot · barcode
        +placeholder: boolean
        +run_blocking_if_unresolved: boolean
    }
    class ResearchSample {
        +sample_type: SampleTypeEnum
        +organism · strain_name
        +starting_inoculum: StartingInoculumEnum
        +placeholder: boolean
    }
    class Container {
        +container_type: ContainerTypeEnum
        +volume_capacity: Quantity
        +current_volume: Quantity
        +expires_at: datetime
    }
    class Recipe {
        +recipe_type: RecipeTypeEnum
        +preparation_steps[]
    }
    class MixtureComponent {
        +name
        +role: MixtureRoleEnum
        +amount: Quantity
        +concentration: Quantity
    }
    class CalibrationRecord {
        +calibration_type: CalibrationTypeEnum
        +performed_at: datetime
        +valid_from · valid_until: datetime
        +status: CalibrationStatusEnum
    }
    class CalibrationCoefficient {
        +name · value · unit · uncertainty
    }
    class CalibrationInvalidationCondition {
        +condition_type: CalibrationInvalidationTypeEnum
        +severity: SeverityEnum
    }

    Container --> Material : material_id
    Container --> ResearchSample : sample_id
    Material "1" *-- "1" Recipe : recipe
    Recipe "1" *-- "*" MixtureComponent : ingredients
    ResearchSample --> Material : source_material_id
    CalibrationRecord --> Device : target_device_id
    CalibrationRecord --> Component : target_component_id
    CalibrationRecord "1" *-- "*" CalibrationCoefficient : coefficients
    CalibrationRecord "1" *-- "*" CalibrationInvalidationCondition : invalidation_conditions
```

### Protocol Structure

A `Protocol` is a reusable template. Each `ProtocolStep` carries component
configurations, material inputs, progression gates (preconditions), and
objectives (control targets).

```mermaid
flowchart TD
    P["Protocol\nprotocol_type · version · total_duration\nalgorithm_id"]
    PS["ProtocolStep\nstep_type · execution_mode · order_index"]
    CC["ComponentConfiguration\nrole · settings"]
    PG["ProgressionGate\ngate_type · parameter · comparator · threshold"]
    OBJ["Objective\nobjective_type · parameter · target\nModificationStrategy"]
    MI["MaterialInput\ninput_type · controlled_by_evolver\nsource/destination containers"]
    MR["MaterialRequirement\nrole · amount · placeholder_allowed"]
    IT["InventoryTimelineEvent\ntime_window · expected_change"]

    P -->|"steps[]"| PS
    P -->|"required_materials[]"| MR
    P -->|"inventory_timeline[]"| IT
    PS -->|"component_configurations[]"| CC
    PS -->|"gates[]"| PG
    PS -->|"objectives[]"| OBJ
    PS -->|"material_inputs[]"| MI
    PS -->|"inventory_requirements[]"| MR
```

### Experiment Lifecycle

An `Experiment` is a concrete run of a `Protocol`. The `RunReadiness` block
gates launch on unresolved placeholder materials and devices.

```mermaid
stateDiagram-v2
    [*] --> planned : experiment created
    planned --> preparing : setup started
    preparing --> running : all gates passed
    running --> paused : operator pause
    paused --> running : resumed
    running --> completed : all steps done
    running --> cancelled : operator cancel
    running --> failed : error or timeout
    preparing --> cancelled : aborted before start
    completed --> [*]
    cancelled --> [*]
    failed --> [*]
```

### Action Template and Execution Flow

`ActionTemplate` is the reusable definition; `ActionExecution` is the
concrete dispatch record appended to the experiment's `action_log`.

```mermaid
flowchart LR
    AT["ActionTemplate\naction_type · command · parameters\nrequires_confirmation"]
    AE["ActionExecution\nrequested_at · started_at · completed_at\ninputs · output_summary"]

    AT -->|"instantiated by\nTUI / CLI / API / hardware"| AE

    AE --> req[requested]
    req -->|approved| appr[approved]
    appr -->|dispatched| run[running]
    run --> ok[succeeded]
    run --> fail[failed]
    run --> cancel[cancelled]
```
