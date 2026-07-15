# eVOLVER TUI Design Target

This document describes the intended TUI shape for the integrated eVOLVER
runtime. Treat it as an editable product/design target: implementation can lag
behind it, but changes to the desired UI should land here first.

## Goals

- Keep the operator oriented without requiring command-line context.
- Show the system state, active experiments, service lifecycle, protocol
  structure, and selected-object details at the same time during normal work.
- Make recovery actions obvious: restart services, inspect failed runs, and
  understand whether the control plane, supervisor, or hardware server is down.
- Preserve a keyboard-first workflow while allowing mouse selection where
  Textual supports it.
- Separate long-running managed services from one-shot jobs and unmanaged UI
  sessions.

## Usage Modes

### Holistic Dev

The normal development path is:

```bash
nix run .#run-supervisor
nix run .#run-tui
```

The supervisor owns service lifecycle and starts autostart services from
`evolver_integrated/service_catalog.yaml`, including the control plane. The TUI
talks to the control plane by default, and the control plane delegates service
status/actions to the supervisor when configured with `--supervisor-url`.

### Piecewise Dev

Individual components can be run directly for debugging:

```bash
nix run .#run-control-plane
nix run .#run-broadcast-ingest
nix run .#run-tui
```

When the control plane is run manually but should still use supervisor service
state:

```bash
nix run .#run-control-plane -- --supervisor-url http://127.0.0.1:18083
```

## Main Scope Layout

The default scope is the operational console. All five left-column windows
should remain visible at the same time. Number keys select/focus a window; they
must not hide the other windows in this scope.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ eVOLVER Control                                                   13:37:00  │
├───────────────────────────────┬──────────────────────────────────────────────┤
│ [1] Status                    │ [Main Detail]                                │
│  supervisor: ok               │                                              │
│  control: ok                  │ Selected experiment/protocol/service/job      │
├───────────────────────────────┤ details, context, health, recent events,      │
│ [2] Live                      │ and next sensible actions.                   │
│  Experiments | Units | Svcs   │                                              │
│  ○ trial-a [created]          │                                              │
│  ○ Control Plane [running]    │                                              │
├───────────────────────────────┤                                              │
│ [3] Inventory                 │                                              │
│  Protocols | Materials | Devs │                                              │
│  ○ turbidostat [6 steps]      │                                              │
├───────────────────────────────┤                                              │
│ [4] Steps                     │                                              │
│  ○ 1. inoculate               │                                              │
│  ○ 2. grow                    │                                              │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ [5] Components                │ [Command Log]                                │
│  pump-a [liquid_mover]        │ 13:37:00 TUI started                          │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

## Windows

### [1] Status

Purpose: small always-visible summary of whether the operator can trust the
rest of the screen.

Shows:
- Supervisor reachability.
- Control-plane reachability.
- Hardware server reachability when known.
- Highest-priority system condition: idle, running, degraded, failed,
  permission needed, calibration needed.

Expected interactions:
- `1` focuses Status.
- `enter` or `space` on a degraded status jumps to the relevant window.
- In the future, status rows should be selectable so the detail pane can show
  diagnostics and recovery actions.

Sketch:

```text
╭─ [1] Status ─────────────────╮
│ supervisor  ok               │
│ control     ok               │
│ hardware    unreachable      │
╰──────────────────────────────╯
```

### [2] Live

Purpose: active runtime objects.

Tabs:
- Experiments: active, staged, complete, failed experiments.
- Evolver Units: hardware units and assignment state.
- Services: supervisor-managed services.
- Future Processes: one-shot runs and literal process/job records.

#### Experiments Tab

Shows:
- Experiment name.
- State icon.
- Protocol name where available.
- Start time / last update when available.

Actions:
- `n`: create new experiment.
- `r`: run focused experiment; warn if another is running.
- `p`: pause/resume focused experiment.
- `c`: cancel/stop focused experiment with confirmation.
- `/`: fuzzy-search experiments.

Sketch:

```text
╭─ [2] Live ───────────────────╮
│ Experiments Units Services   │
│ ○ trial-a        [created]   │
│ ◉ overnight-od   [running]   │
│ ✗ failed-test    [failed]    │
╰──────────────────────────────╯
```

#### Services Tab

Shows service catalog entries from the supervisor/control-plane service API.

State symbols:
- Running: green hollow circle.
- Paused: pause symbol.
- Stopped/available: dim hollow square.
- Cancelled: red filled square.
- Failed: red X.
- Unknown/unreachable: question mark.

Actions:
- `s`: start service.
- `x`: stop service.
- `p`: pause/resume service.
- `r`: restart service.
- `enter`: show service detail in Main.

Service categories:
- Core: supervisor/control-plane core.
- Managed: services the control plane/supervisor should keep alive.
- One-shot: jobs started for a bounded task.
- Unmanaged: TUI, GUI, web UI, CLI sessions, debug tools.

Sketch:

```text
╭─ [2] Live / Services ────────╮
│ ○ Control Plane   [core]     │
│ □ eVOLVER Server  [managed]  │
│ □ Broadcast Ingest[managed]  │
│ ✗ Data Export     [one-shot] │
│ ? Web UI          [unmanaged]│
╰──────────────────────────────╯
```

### [3] Inventory

Purpose: reusable definitions and configured resources.

Tabs:
- Protocols: templates for experiment runs.
- Materials: organisms, media, reagents, samples, waste.
- Devices: pumps, sensors, miniEvolver units, serial devices, logical roles.

Actions:
- `space` / `enter`: select protocol or inventory item.
- `/`: fuzzy-search current tab.
- `[` / `]`: switch inventory tabs.

Selecting a protocol loads [4] Steps and [5] Components and updates Main.

Sketch:

```text
╭─ [3] Inventory ──────────────╮
│ Protocols Materials Devices  │
│ ○ turbidostat       [6]      │
│ ○ morbidostat       [8]      │
│ ○ calibration       [3]      │
╰──────────────────────────────╯
```

### [4] Steps

Purpose: ordered protocol steps for the selected protocol or running
experiment.

Shows:
- Step order.
- Completion/progress icon.
- Step name.
- Current step when an experiment is running.

Actions:
- `/`: future fuzzy-search steps.
- `enter`: select step and show components/detail.

Sketch:

```text
╭─ [4] Steps - turbidostat ────╮
│ ● 1. inoculate               │
│ ◌ 2. grow to target OD       │
│ ○ 3. maintain dilution       │
│ ○ 4. sample                  │
╰──────────────────────────────╯
```

### [5] Components

Purpose: components for the selected protocol step.

Shows:
- Component name.
- Type.
- Role or IO role.
- Binding to physical/logical device when available.

Actions:
- `enter`: show component detail in Main.
- Future: jump to Inventory device/material definition.

Sketch:

```text
╭─ [5] Components ─────────────╮
│ pump-a      [liquid_mover]   │
│ vial-03     [bioreactor]     │
│ od-sensor   [sensor]         │
╰──────────────────────────────╯
```

### [0] Context / Main Detail

Purpose: scrollable detailed view for the focused scope or selected object.
It should avoid duplicating the left window and instead explain the selected
object's context and next actions. `0` focuses this pane so the operator can
scroll without leaving the keyboard workflow.

Detail variants:
- Scope detail: when no row is focused, explain what the focused window/tab is
  for and which actions are relevant.
- Experiment detail: state, protocol, machine/vials, runner, current step,
  recent events, lifecycle actions.
- Evolver unit detail: online/offline, role, assigned experiments, attached
  pumps/sensors/vials, latest readings when available.
- Service detail: command, category, supervisor state, restart count, last
  action, logs tail, dependencies.
- Protocol detail: description, step count, required materials/devices.
- Device detail: online/offline, assigned experiment, latest measurements.
- Material detail: type, source, lot, storage conditions.
- Job detail: queued/running/succeeded/failed, result/error.

Sketch:

```text
╭─ [Main] Service: Control Plane ──────────────────────────────────────────────╮
│ State:      running                                                         │
│ Category:   core                                                            │
│ Command:    nix run .#run-control-plane -- --supervisor-url ...             │
│ Restarts:   2                                                               │
│ Last:       restart                                                         │
│                                                                            │
│ Actions: r restart, x stop, p pause                                         │
╰────────────────────────────────────────────────────────────────────────────╯
```

### Command Log

Purpose: recent operator actions and system responses.

Shows:
- TUI start/stop.
- API errors.
- Service lifecycle actions.
- Experiment lifecycle actions.
- Confirmation outcomes.

Sketch:

```text
╭─ [Command Log] ──────────────────────────────────────────────────────────────╮
│ 13:37:00 TUI started - polling control plane                                │
│ 13:38:11 RESTART service control-plane                                      │
│ 13:38:14 ERROR service: supervisor unreachable                              │
╰────────────────────────────────────────────────────────────────────────────╯
```

## Scopes And Visibility

The TUI should support scopes, but the default operational scope keeps all five
left windows visible.

### Main Scope

Visible:
- [1] Status
- [2] Live
- [3] Inventory
- [4] Steps
- [5] Components
- [0] Context / Main Detail
- Command Log

Number keys focus windows without hiding siblings. `0` focuses the right
context pane; `1`-`5` focus the left windows.

Tab switching inside a focused window (`[` / `]`, `left` / `right`, or mouse
click on a tab) must keep keyboard focus inside that same numbered window by
moving focus to the newly active tab's list. Focus must not jump to Main
Detail as a side effect of tab changes.

Each list keeps a persistent selected row while its backing item still exists.
When the window owns focus, the selected row uses the active highlight. When
focus moves to another window, the selected row remains visible in a muted
state. If the backing item disappears from refreshed data, selection falls
back to the nearest available row. This must be implemented as an explicit
TUI-owned selection marker rather than relying only on framework focus
highlighting, so row `0` remains visibly selected after refreshes and tab
changes.

By default, list tabs do not auto-select the first row. If a list has no
focused or active entry, the Context pane should show scope-level guidance and
prompt arrow up/down or click to choose a row. Active entries are UI-only
state: they may set nested context, toggle an option, or open a form, but do
not directly imply hardware state.

Polling refreshes should not visually rebuild unchanged lists. If a service
snapshot is identical to the current one, the Services list must keep its
existing rows in place so the selected row does not flash during routine
polling.

The structured TUI contract lives in
`evolver_integrated/tui/tui_architecture.json`. Its hierarchy is now
page-first: `pages[] -> windows[] -> tabs[]`. Demo inventory, evolver units,
protocol templates, component examples, services, and experiments live in
`evolver_integrated/tui/demo_data.json` and can be loaded with `--demo` at
startup or `d` at runtime.

### Service Scope

Future scope optimized for service recovery. It can enlarge [2] Services and
Main Detail while still preserving Status.

```text
┌───────────────────────────────┬──────────────────────────────────────────────┐
│ [1] Status                    │ [Service Detail + logs]                      │
├───────────────────────────────┤                                              │
│ [2] Services                  │                                              │
│  ○ Control Plane              │                                              │
│  □ eVOLVER Server             │                                              │
│  ✗ Broadcast Ingest           │                                              │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

### Protocol Scope

Future scope optimized for editing or inspecting protocol definitions. It can
show Inventory, Steps, Components, and Main, while Status remains available.

### Experiment Scope

Future scope optimized for a single running experiment. It can show Status,
Live/Experiments, Steps, Components, Main, and an experiment event log.

## Core Workflows

### Start Integrated Dev Runtime

1. Operator runs `nix run .#run-supervisor`.
2. Supervisor loads the service catalog.
3. Supervisor starts autostart services such as Control Plane.
4. Operator runs `nix run .#run-tui`.
5. TUI shows Status as healthy, Live/Services as running/stopped/failed.

### Restart Control Plane During Development

1. Focus [2] Live.
2. Switch to Services tab.
3. Select Control Plane.
4. Press `r`.
5. TUI sends restart request through control-plane service API.
6. Control plane proxies to supervisor, or future TUI fallback talks directly to
   supervisor if the control plane is unreachable.
7. TUI reports transient control-plane disconnect, then resumes polling.

Expected behavior: restarting control plane must not stop unrelated managed
services unless they explicitly depend on it.

### Recover Failed Managed Service

1. Status reports degraded/failed.
2. Operator presses `space` in Status or `2` to focus Live.
3. Services tab highlights failed service.
4. Main Detail shows command, recent action, restart count, and last error when
   available.
5. Operator presses `r` to retry restart after code/config changes.

### Create And Run Experiment

1. Focus [2] Live / Experiments.
2. Press `n`.
3. Enter experiment name.
4. TUI creates a minimal valid experiment request.
5. Select experiment.
6. Press `r`.
7. If another experiment is running, TUI asks for confirmation.
8. Main Detail shows experiment state and runner context.

### Inspect Protocol

1. Focus [3] Inventory.
2. Select Protocols tab.
3. Select a protocol.
4. [4] Steps loads ordered steps.
5. [5] Components resets to "select a step".
6. Selecting a step loads component bindings.
7. Main Detail shows protocol or step detail.

## Keybinding Architecture

The architecture JSON keeps pages as the top-level UI scope. Each page owns a
list of windows, and each window may own tabs. Numeric focus keys live on
window entries; scoped shortcuts live on the window or tab entry that owns
them: `pages[].windows[].keybinds` and
`pages[].windows[].tabs[].keybinds`.

Context metadata follows the same inheritance path. A page can define broad
context, a window can refine it, and a tab can set item-level or active parent
context such as `inventory.protocols.active` or `steps.active`. Context pane
content should be derived from the effective focused scope rather than from a
separate hard-coded context table.

Options also inherit downward. Defaults are false, and higher scopes can enable
an option for all descendants unless a lower scope overrides it. Keybindings
can be declared anywhere, but activation-style bindings are only effective
when the matching option is enabled for the focused scope. For example,
Protocols enables `can_activate_context`, so `space` activates the focused
protocol context; Materials does not enable that option, so it should not be
presented as a set-active action. Components enables `can_toggle_option`, so
`space` maps to component enablement there. Live / Services enables
`opens_form`, so `space` opens service config when details are available.

The context pane should show the same scope-aware suggestions the operator can
use in the focused tab. For Live / Services, `enter` starts an inactive focused
service and `space` opens the service config popup when config details are
available. Focused rows use a lower-intensity persistent highlight, while
status symbols are bold so state changes remain readable on highlighted rows.

## Open Design Questions

- Should the TUI talk directly to supervisor as a fallback when the control
  plane is down, or should it only show recovery instructions?
- Should service dependencies be modeled in YAML now, or wait until subprocess
  supervision has real restart policies?
- Should one-shot jobs live under Live as a fourth tab, or become their own
  window/scope?
- What is the minimum experiment creation form before real protocol/material
  inventory exists?
- Which services are allowed to be autostarted by default in dev?
