# eVOLVER Integrated Architecture — Design Presentation

> A visual reference for walking through the integrated eVOLVER runtime architecture.
> Scroll section by section. Each section is self-contained.

---

## 1. What Is eVOLVER?

eVOLVER is a **continuous-culture bioreactor platform** that lets researchers automate long-running microbial evolution experiments. Each machine houses an array of vials, each independently controlled for temperature, stir speed, optical density sensing, and fluid handling (pumps).

```
┌─────────────────────────────────────────────────────┐
│               eVOLVER Machine                       │
│                                                     │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐            │
│  │ vial │  │ vial │  │ vial │  │ vial │  … ×16     │
│  │  01  │  │  02  │  │  03  │  │  04  │            │
│  │  🌡  │  │  🌡  │  │  🌡  │  │  🌡  │  temp      │
│  │  💡  │  │  💡  │  │  💡  │  │  💡  │  OD        │
│  │  🌀  │  │  🌀  │  │  🌀  │  │  🌀  │  stir      │
│  │  💧  │  │  💧  │  │  💧  │  │  💧  │  pumps     │
│  └──────┘  └──────┘  └──────┘  └──────┘            │
│                                                     │
│  Arduino SAMD21 — serial I/O — Raspberry Pi         │
└─────────────────────────────────────────────────────┘
```

The Arduino handles real-time hardware I/O. The Raspberry Pi hosts the **eVOLVER server**, which talks to the Arduino over serial and exposes a Socket.IO API to computers on the network.

---

## 2. The Old Model: Server + DPU

The original architecture treats the system as two units:

```mermaid
flowchart LR
    subgraph Pi ["Raspberry Pi"]
        Arduino["Arduino\nSAMD21\nhardware I/O"]
        Server["eVOLVER Server\nevolver.py\nsocket.io"]
        Arduino <-->|serial /dev/ttyUSB0| Server
    end

    subgraph WS ["Workstation (DPU)"]
        Exp["experiment scripts\n(user code)"]
        Cal["calibrate.py"]
        Graph["graphing\nDjango + Bokeh"]
    end

    Server <-->|"Socket.IO port 8081\n/dpu-evolver namespace"| WS
```

### What DPU actually contains

The label "DPU" is misleading — it hides at least five different concerns inside a single boundary:

```mermaid
flowchart TB
    DPU["Old DPU Boundary\n(everything lives here)"]

    DPU --> A["User experiment scripts\nlong-running Python, user-authored"]
    DPU --> B["Calibration workflows\nfits OD curves, uploads to server"]
    DPU --> C["Data collation\nassembles CSV files per experiment"]
    DPU --> D["Graphing / dashboards\nDjango app, Bokeh plots"]
    DPU --> E["System management scripts\nfirmware, provisioning, identity"]
```

Those jobs have **different lifetimes and failure modes**. A bad graphing import should not kill an experiment. A bad experiment script should not take down data capture.

---

## 3. The Integrated Model — Big Picture

The transition changes the mental model from two blobs into **explicit bounded services**:

```mermaid
flowchart LR
    Old["Old model\neVOLVER server + DPU"]
    New["Integrated model\nhardware service + control plane\n+ data service + isolated workers + UI clients"]
    Old -->|"this project"| New
```

### New responsibility split

| Old label | New home |
|-----------|----------|
| Hardware I/O | `evolver-hardwared` |
| Experiment logic | isolated runner subprocess |
| Calibration, firmware, provisioning | one-shot maintenance workers |
| Data ingest + storage | `evolver-datad` |
| Graphing / visibility | visibility clients over data service |
| Operator CLI | `dpu` CLI/SDK |
| Operator console | TUI — `evolver-ui` |
| Remote sync | `evolver-syncd` |

---

## 4. Target Process Model

The supervisor owns the service tree. The control plane coordinates everything below it — but it never runs user code or one-shot maintenance operations inside its own process.

```mermaid
flowchart TB
    Supervisor["service supervisor\nevolver-supervisord\nport 18083"]

    Supervisor --> Hardware["evolver-hardwared\nlong-lived hardware communication\nserial + Socket.IO"]
    Supervisor --> Control["evolver-controld\ncontrol plane + lifecycle API\nport 17000"]
    Supervisor --> Data["evolver-datad\ndurable data ingest\nappend-only JSONL"]
    Supervisor --> UI["evolver-ui\noperator console\nunmanaged"]
    Supervisor --> Sync["evolver-syncd\nremote catalog sync\nworker"]

    Control --> Runner["experiment runner\nisolated subprocess\nuser-authored code"]
    Control --> Cal["calibration worker\none-shot"]
    Control --> FW["firmware worker\none-shot"]
    Control --> ID["identity worker\none-shot"]
    Control --> Diag["diagnostic worker\none-shot"]
    Control --> Export["export worker\none-shot"]
```

### Service catalog (current)

From `service_catalog.yaml`:

| ID | Name | Category | Purpose |
|----|------|----------|---------|
| `control-plane` | Control Plane | core | lifecycle coordinator, control API |
| `evolver-server` | eVOLVER Server | managed | legacy Socket.IO + serial server |
| `broadcast-ingest` | Broadcast Ingest | managed | persist raw broadcasts from server |
| `data-service` | Data Service | managed | local JSONL persistence |
| `tui` | TUI | unmanaged | operator terminal sessions |

---

## 5. Core Services — Deep Dive

### 5a. Hardware Service

The hardware service is the **highest-priority long-running process**. It owns the live relationship with every connected machine.

Responsibilities:
- Discover and identify connected machines (provisioning handshake)
- Maintain serial connections to the Arduino
- Read raw sensor signals every broadcast cycle (~20 s)
- Send validated hardware commands
- Track firmware and protocol compatibility
- Enforce exclusive hardware access

> **Key rule:** The hardware service owns the mechanism. The control plane owns the policy.

```mermaid
sequenceDiagram
    participant UI as UI Client
    participant CP as Control Plane
    participant Worker as Maintenance Worker
    participant HW as Hardware Service
    participant M as eVOLVER Machine

    UI->>CP: request risky action (calibration / flashing)
    CP->>UI: request authorization
    UI->>CP: approve
    CP->>Worker: start one-shot job
    Worker->>HW: request exclusive maintenance lease
    HW->>M: perform hardware operation
    HW-->>Worker: result
    Worker-->>CP: job result + logs
    CP-->>UI: status update
```

### 5b. Control Plane

The control plane is the **coordinator**. It manages experiment lifetimes, tracks authorization, supervises workers, and exposes the local HTTP API.

Current API surface (`control_api.py`):

```
GET  /health
GET  /experiments
POST /experiments
POST /experiments/{id}/start
POST /experiments/{id}/pause
POST /experiments/{id}/resume
POST /experiments/{id}/stop
POST /device-commands
GET  /jobs
GET  /services          ← proxies to supervisor
POST /services/{id}/{action}
```

**Experiment state machine:**

```mermaid
stateDiagram-v2
    [*] --> created : POST /experiments
    created --> running : POST /start
    running --> paused : POST /pause
    paused --> running : POST /resume
    running --> stopped : POST /stop
    paused --> stopped : POST /stop
    running --> failed : runner error
    stopped --> [*]
    failed --> [*]
```

### 5c. Data Service

Raw data is persisted **before** experiment-specific processing. This protects data if an experiment script, UI, or control process fails.

```mermaid
flowchart LR
    Machines["eVOLVER machines"]
    HW["hardware service\nlive hardware I/O"]
    Raw["durable raw-data ingest\nappend-only JSONL\nbefore any processing"]
    Stream["live event stream"]
    Runners["experiment runners"]
    UIClients["UI clients\nTUI / web / local"]
    Graphing["graphing tools"]
    Monitoring["monitoring"]

    Machines --> HW
    HW --> Raw
    HW --> Stream
    Stream --> Runners
    Stream --> UIClients
    Stream --> Graphing
    Stream --> Monitoring
```

Dataset types managed by the data service:

| Dataset | Contents |
|---------|----------|
| Machine lifetime | identity history, firmware history, calibration history, maintenance records |
| Experiment session | raw measurements, transforms, actions, events, logs |
| User / customer | templates, preferences, saved configs, permissions |
| System config | schemas, validation rules, approved firmware, form definitions |

---

## 6. Message Contracts

All interprocess communication uses **versioned, validated envelopes**. This makes services independently evolvable without silent incompatibilities.

```mermaid
flowchart LR
    Env["Envelope\nschema_version: evolver.v1\nkind: ...\nid: uuid\ncreated_at: ISO-8601\nproducer: ...\npayload: {...}"]
```

Named event kinds (`messages.py`):

| Kind | Direction | Purpose |
|------|-----------|---------|
| `machine.measurement.raw` | hardware → data service | raw sensor broadcast |
| `experiment.status` | control plane → subscribers | lifecycle transitions |
| `experiment.runner.action` | runner → control plane | control actions from user code |
| `job.status` | maintenance workers → control plane | one-shot job updates |
| `device.command.request` | control plane → hardware | validated hardware command |

**Device command shape** (backward-compatible with legacy DPU format):

```json
{
  "param": "temp",
  "value": ["NaN", "3001"],
  "immediate": true,
  "recurring": false,
  "fields_expected_outgoing": 17,
  "fields_expected_incoming": 17
}
```

---

## 7. Command Path and Data Path

### Command path (top-down)

```mermaid
flowchart TD
    Clients["TUI / web UI / DPU CLI"]
    CP["control plane\nvalidates + routes"]
    Runner["experiment runner\nisolated subprocess"]
    Worker["maintenance worker\none-shot"]
    Cmd["validated device command"]
    HW["hardware service"]
    M["eVOLVER machine"]

    Clients --> CP
    CP --> Runner
    CP --> Worker
    CP --> Cmd
    Cmd --> HW
    HW --> M
```

### Data path (bottom-up)

```mermaid
flowchart BT
    M["eVOLVER machine"]
    HW["hardware service"]
    Raw["raw data ingest\nappend before processing"]
    Stream["live event stream"]
    Runner["experiment runner"]
    UI["TUI / web UI / local UI"]
    Graphing["graphing"]
    Monitoring["monitoring"]

    M --> HW
    HW --> Raw
    HW --> Stream
    Stream --> Runner
    Stream --> UI
    Stream --> Graphing
    Stream --> Monitoring
```

---

## 8. Failure Isolation

Because each concern runs in its own process, failures are **contained**:

```mermaid
flowchart TB
    Script["bad experiment script"]
    Runner["experiment runner\nisolated subprocess\nFAILS"]
    CP["control plane\nremains alive"]
    HW["hardware service\nremains alive"]
    Data["raw data ingest\ncontinues when possible"]

    Script --> Runner
    Runner -.->|"failure contained\ndoes not propagate"| CP
    Runner -.->|"does not crash"| HW
    HW --> Data
```

The same logic applies to maintenance workers. A firmware flash that crashes cannot take down the long-lived hardware communication loop.

---

## 9. Maintenance Authorization Flow

Risky operations require **explicit user authorization** before the control plane will launch a worker:

```mermaid
sequenceDiagram
    participant Op as Operator (TUI / CLI)
    participant CP as Control Plane
    participant MJ as MaintenanceJobManager
    participant Worker as One-Shot Worker
    participant HW as Hardware Service

    Op->>CP: request calibration
    CP->>MJ: create job (state: pending_auth)
    MJ-->>Op: show authorization prompt
    Op->>CP: approve
    CP->>MJ: authorize job (state: queued)
    MJ->>Worker: spawn subprocess
    Worker->>HW: request exclusive lease
    HW-->>Worker: lease granted (hardware paused)
    Worker-->>MJ: result + logs (state: succeeded / failed)
    MJ-->>Op: status update
```

Operations that require authorization:
- Firmware flashing
- Calibration
- Identity replacement
- Machine reset
- Experiment interruption
- Destructive data operations

---

## 10. DPU — From System Boundary to Tool Layer

In the new model, the DPU becomes a **CLI client and experiment authoring SDK**, not the single place where orchestration, data, and hardware-adjacent jobs are mixed.

```mermaid
flowchart LR
    CLI["dpu CLI\noperator commands"]
    SDK["dpu SDK\nexperiment authoring"]
    TUI["TUI\noperator console"]
    Web["web / desktop UI"]
    CP["control plane API\nhttp://localhost:17000"]

    CLI --> CP
    TUI --> CP
    Web --> CP
    SDK --> Runner["experiment runner\nscript runtime"]
    Runner --> CP
```

Example future CLI commands:

```bash
dpu status
dpu experiment create
dpu experiment start experiment.yml
dpu experiment pause EXP-123
dpu experiment resume EXP-123
dpu experiment stop EXP-123
dpu calibration start --device evo-01 --type od
dpu firmware install --device evo-01 firmware.bin
dpu data watch EXP-123
dpu data export EXP-123
```

---

## 11. Remote Sync

Remote synchronization runs as a **dedicated non-blocking worker**. Local operation is the authority while offline; sync state is tracked explicitly.

```mermaid
flowchart LR
    Local["local data store\noperational authority offline"]
    Sync["evolver-syncd\ndedicated sync worker"]
    Catalog["remote data catalog"]

    Local --> Sync
    Sync -->|"pending → complete\nconflicting / failed"| Catalog
    Catalog -->|"approved config\ntemplates / firmware"| Sync
    Sync --> Local
```

What the remote catalog can mirror:

- Machine lifetime datasets (for administrators)
- Experiment datasets (users + admins)
- User / customer datasets
- Shared configuration, templates, schemas, form definitions
- Approved firmware artifacts

---

## 12. The TUI — Operator Console

The TUI is built with **Textual** and models a lazygit-style operator console. All five left-column windows are **always visible together** in the main scope.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ eVOLVER Control                                                   13:37:00  │
├───────────────────────────────┬──────────────────────────────────────────────┤
│ [1] Status                    │ [Main Detail]                                │
│  supervisor  ok               │                                              │
│  control     ok               │  Selected experiment / service / protocol    │
│  hardware    unreachable      │  detail, health, recent events,              │
├───────────────────────────────┤  and next sensible actions.                  │
│ [2] Live                      │                                              │
│  Experiments | Units | Svcs   │                                              │
│  ○ trial-a        [created]   │                                              │
│  ◉ overnight-od   [running]   │                                              │
│  ✗ failed-test    [failed]    │                                              │
├───────────────────────────────┤                                              │
│ [3] Inventory                 │                                              │
│  Protocols | Materials | Devs │                                              │
│  ○ turbidostat       [6]      │                                              │
│  ○ morbidostat       [8]      │                                              │
├───────────────────────────────┤                                              │
│ [4] Steps — turbidostat       │                                              │
│  ● 1. inoculate               │                                              │
│  ◌ 2. grow to target OD       │                                              │
│  ○ 3. maintain dilution       │                                              │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ [5] Components                │ [Command Log]                                │
│  pump-a      [liquid_mover]   │ 13:37:00  TUI started                        │
│  vial-03     [bioreactor]     │ 13:38:11  RESTART control-plane              │
│  od-sensor   [sensor]         │ 13:38:14  ERROR supervisor unreachable       │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

### Window roles

| Window | Role |
|--------|------|
| **[1] Status** | Always-visible trust indicator — supervisor / control / hardware reachability |
| **[2] Live** | Active runtime objects — experiments, hardware units, managed services |
| **[3] Inventory** | Reusable definitions — protocols, materials, devices |
| **[4] Steps** | Ordered steps of the selected protocol or running experiment |
| **[5] Components** | Components bound to the selected protocol step |
| **Main Detail** | Full detail for whatever is selected — state, logs, actions |
| **Command Log** | Audit trail of operator actions and system responses |

### Service state symbols

| Symbol | Meaning |
|--------|---------|
| `○` green | running |
| `⏸` | paused |
| `□` dim | stopped / available |
| `■` red | cancelled |
| `✗` red | failed |
| `?` | unknown / unreachable |

### Key bindings (main scope)

| Key | Action |
|-----|--------|
| `1`–`5` | focus window (siblings stay visible) |
| `n` | new experiment (from [2] Live) |
| `r` | run / restart focused item |
| `p` | pause / resume |
| `c` | cancel / stop with confirmation |
| `s` / `x` | start / stop service |
| `enter` | open detail in Main |
| `/` | fuzzy-search current panel |
| `[` / `]` | switch tabs within a window |

---

## 13. Implementation Phases

```mermaid
gantt
    title Integrated eVOLVER — Implementation Phases
    dateFormat  YYYY-MM-DD
    section Foundations
    Phase 1 — Messages + Control Plane + Data Service :done, p1, 2025-01-01, 60d
    Phase 2 — Raw Broadcast Ingest                    :done, p2, after p1, 30d
    Phase 3 — Runner Isolation (DPU subprocess)       :done, p3, after p2, 30d
    Phase 4 — Local Control API (aiohttp)             :done, p4, after p3, 30d
    Phase 5 — Maintenance Job Manager                 :done, p5, after p4, 30d
    section In Progress
    Supervisor Daemon + Service Catalog               :active, sup, 2025-07-01, 30d
    TUI — Textual operator console                    :active, tui, 2025-07-01, 60d
    section Remaining
    Systemd supervision for services                  :sys, after sup, 45d
    Full experiment creation workflow                 :exp, after tui, 30d
    Data service reads for graphing                   :gfx, after exp, 30d
    Remote sync worker                                :sync, after gfx, 30d
```

### Phase summary

| Phase | What was built | Module |
|-------|---------------|--------|
| 1 | Versioned message contracts, `LocalDataService`, `ControlPlane` lifecycle | `messages.py`, `data_service.py`, `control_plane.py` |
| 2 | `BroadcastIngestor` — Socket.IO → `machine.measurement.raw` | `broadcast_ingest.py` |
| 3 | `DpuRunnerManager` — DPU script as isolated subprocess | `runner_manager.py` |
| 4 | `create_control_plane_app` — aiohttp HTTP API | `control_api.py`, `control_daemon.py` |
| 5 | `MaintenanceJobManager` — one-shot jobs + authorization | `maintenance_jobs.py` |
| — | `ServiceManager`, `SupervisorDaemon`, service catalog | `service_manager.py`, `supervisor_daemon.py` |
| — | TUI — Textual app, panels, screens, supervisor client | `tui/` |

---

## 14. Design Rules

These rules define what the integrated architecture must always preserve:

1. **Only the hardware service owns normal hardware communication.**
2. **User code never runs inside the hardware service.**
3. **User experiment code never runs inside the control-plane process.**
4. **Maintenance jobs run as interruptible one-shot workers.**
5. **Raw data is persisted independently of experiment-specific processing.**
6. **Risky maintenance actions require explicit user authorization.**
7. **UI clients talk to the control plane — never directly to hardware.**
8. **All interprocess messages use versioned, validated formats (`evolver.v1`).**
9. **Graphing and visualization are visibility clients, not data owners.**
10. **Local operation continues when remote services are unavailable.**
11. **Data collation and management are independent from DPU experiment execution.**
12. **The DPU becomes a CLI and SDK layer over the integrated system.**

---

## 15. Full System View

```mermaid
flowchart TB
    subgraph Machine ["eVOLVER Machine(s)"]
        Arduino["Arduino SAMD21\nhardware I/O\ntemp / OD / stir / pumps"]
    end

    subgraph Pi ["Raspberry Pi"]
        HW["evolver-hardwared\nSocket.IO + serial\nlegacy evolver server"]
        Arduino <-->|serial| HW
    end

    subgraph Integrated ["Integrated Runtime (workstation or Pi)"]
        Sup["supervisor\nport 18083"]
        CP["evolver-controld\ncontrol plane API\nport 17000"]
        DS["evolver-datad\nappend-only JSONL\nraw ingest"]
        BI["broadcast-ingest\nSocket.IO subscriber"]
        Sync["evolver-syncd\nremote sync"]

        Sup --> CP
        Sup --> DS
        Sup --> BI
        Sup --> Sync

        CP --> Runner["experiment runner\nDPU subprocess"]
        CP --> MJ["maintenance workers\none-shot\ncal / firmware / diag"]
    end

    subgraph Clients ["Operator Interfaces"]
        TUI["TUI\nTextual\noperator console"]
        CLI["dpu CLI\noperator commands"]
        Web["web / desktop UI\n(future)"]
    end

    subgraph Remote ["Remote Catalog (optional)"]
        Cat["data catalog\nconfig / firmware\ntemplates"]
    end

    HW -->|"Socket.IO broadcasts"| BI
    BI -->|"machine.measurement.raw"| DS
    HW -->|"validated commands"| Arduino

    TUI --> CP
    CLI --> CP
    Web --> CP

    Runner -->|"experiment.runner.action"| CP
    CP -->|"device.command.request"| HW

    DS <-->|"pending / complete\nconflicting / failed"| Sync
    Sync <--> Cat
```

---

*End of presentation — all diagrams generated with Mermaid and render in any Markdown viewer that supports it (GitHub, VS Code preview, Obsidian, etc.).*
