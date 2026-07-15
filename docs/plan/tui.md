# TUI Plan

## Layout

LazyGit-style: 5 stacked panels on the left, two panels on the right.

- **Left column**: panels 1–5, stacked vertically
- **Right column**: Main display (top, 1fr) + Command log (bottom, fixed height)
- **Bottom bar**: context-sensitive keyboard shortcuts via Textual Footer

Tab switching within a panel: `[` = prev tab, `]` = next tab.
Fuzzy search available in every panel: `/`.

---

## Left Panels

### [1] Status

Compact status line at the top of the left column.

States (examples):
- Idle
- Experiment in progress
- Permission needed
- Calibration needed
- Control plane unreachable

`space` when focused → jumps directly to the panel or context that is
calling for attention.

---

### [2] Live  ·  tabs: `Experiments` | `Evolver Units` | `Processes`

The "live things" panel — current activity and connected hardware.

#### Tab 1 — Experiments

List of experiments (active, complete, failed, staged) sorted by start time.

**Experiment model:**
- Every experiment runs a *protocol*
- The protocol specifies which hardware is used (miniEvolvers, liquid movers,
  bioreactors) and how much of each resource is required
- Each experiment is one instance of a protocol run
- To repeat an experiment 5 times in parallel, spin up 5 separate experiments
  each pointing at the same protocol
- One experiment can span multiple miniEvolvers if the protocol calls for it,
  but identical parallel runs should be separate experiments
- The asterisk marks the currently focused experiment

Arrow keys navigate the list. Main display ([0]) updates live.

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `p` | Pause or Resume (toggles based on current state) |
| `c` | Cancel — confirmation popup required |
| `n` | New — prompts for a name |
| `r` | Run — warns if another experiment is already running |
| `/` | Fuzzy-filter the list |

#### Tab 2 — Evolver Units

List of connected miniEVOLVER units. Each unit = one Arduino controlling
one or more bioreactor vials.

Selecting a unit updates the main display with its current readings and
exposes shortcuts for direct interaction.

#### Tab 3 — Processes

Active software daemons and experiment runners, ordered by importance
(running → queued → pending).

Exposes keyboard shortcuts to restart or stop a process.

---

### [3] Inventory  ·  tabs: `Protocols` | `Materials` | `Devices`

A separate context from [2]. This is the catalog of reusable definitions —
protocols, reagents, and hardware entries that experiments draw from.

#### Tab 1 — Protocols

List of available protocol definitions. Fuzzy search with `/`.

`space` or `enter` on a protocol → loads it into **[4] Steps** and
**[5] Components** for viewing/editing.

A protocol is a template, not a running instance. It describes:
- The ordered list of steps
- The hardware components required (by abstract type, not specific unit)
- The materials consumed or produced at each step

This hardware/material abstraction (abstract type → actual device) is what
makes protocols portable across different eVOLVER configurations.

#### Tab 2 — Materials

Catalog of biological materials available in the lab. Each entry has:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier / barcode |
| `name` | Human-readable name |
| `type` | Controlled vocabulary (see below) |
| Additional metadata | Concentration, lot, strain DB ID, etc. |

**Material types** (drawn from lab submission vocabulary):

| Type | I/O role |
|------|----------|
| `organism` (bact / yeast strain) | Input |
| `growth_medium` | Input |
| `carbon_source` | Input |
| `nitrogen_source` | Input |
| `reagent` | Input |
| `starting_inoculum` | Input |
| `waste` | Output |
| `sample` | Output |
| `bioreactor` | Input or Output |

Materials with input-type tags can be assigned as inputs to pump routes.
Output-type materials can be assigned as sinks. Bioreactors are bidirectional.

#### Tab 3 — Devices

Catalog of hardware devices and their static configurations:
bioreactors, fluidic modules, spinners, sensors.

For each device you can set:
- Static configuration (vial count, pump channels, sensor type)
- I/O associations: which pumps are connected to which materials
  (e.g. pump channel 3 → growth medium, pump channel 7 → waste)
  filtered by the material's type tag
- Assignment of this physical device to an abstract hardware entry in a
  protocol (making the protocol reusable across different eVOLVER builds)

---

### [4] Steps

The ordered list of steps in the protocol selected from [3] / Protocols.

- Arrow keys navigate through steps
- Can add, edit, or delete steps when not live
- When an experiment is **running**, shows git-commit-graph progress:
  - `●` completed
  - `◌` in progress
  - `○` not yet started
- Selecting a step updates [5] Components to show that step's components
- Fuzzy search with `/`

---

### [5] Components

Components of the step currently selected in [4].

- Scope: entries belong to the protocol; selections are scoped to the step
- Each component describes an abstract hardware or material slot
  (e.g. "input pump", "OD sensor", "growth medium source")
- The actual assignment to physical hardware or catalogued materials is
  done in [3] / Devices
- I/O role shown for each component (input / output / bidirectional)

---

## Right Side

### [0] Main Display (top right)

Content changes based on what is focused in the left column:

- Experiment selected in [2] → name, state, protocol, eVOLVER units in use,
  progress / ETA, growth curve (future)
- Evolver unit selected in [2] → live sensor readings, assigned experiments
- Protocol selected in [3] → name, step count, description
- Device selected in [3] → static config, current I/O assignments

### Command Log (bottom right)

Scrolling log of commands issued to the control plane (with timestamps).

---

## Navigation Summary

| Key | Action |
|-----|--------|
| `1`–`5` | Jump directly to that panel |
| `Tab` | Cycle through focusable panels |
| `↑` / `↓` | Navigate within a list |
| `[` / `]` | Prev / next tab within panels [2] and [3] |
| `/` | Fuzzy search in the focused panel |
| `space` | Select / activate focused item |
| `q` | Quit |
| `escape` | Close modal / cancel |

---

## Implementation Notes

- Framework: **Textual** (`python3Packages.textual` in nixpkgs)
- HTTP client polls the control-plane API every 2 s
- All API calls (start, stop, pause, etc.) run as Textual workers to
  avoid blocking the UI event loop
- Confirmation dialogs are modal screens that `dismiss(bool)`
- Fuzzy search is a modal `ListView` that filters as you type
- `nix run .#tui` or `nix run .#run-tui` launches the UI
