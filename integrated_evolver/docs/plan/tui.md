# TUI Plan

## Layout

LazyGit-style: several smaller windows on the left, two windows on the right.

- **Left column**: blocks 1–5, stacked vertically — navigation and selection
- **Right column**: block 0 (main display, top) + command log (bottom)
- **Bottom bar**: context-sensitive keyboard shortcuts

---

## Left Blocks

### [1] Status

Top block. Compact readout of current system state. Examples:

- Experiment in progress
- Experiment failed
- Permission needed
- Calibration needed

**Shortcut:** `space` when focused → jumps directly to the relevant panel or
nav position that is calling for attention (e.g. the experiment that failed,
or the calibration workflow).

---

### [2] Experiments

List of experiments. This is the primary navigation hub.

**Experiment semantics:**

- Every experiment runs a *protocol*
- The protocol defines which machines are used (miniEvolvers), how many liquid
  movers, and the full configuration of what the experiment needs
- If you want 5 repeats of the same experiment, you spin up 5 separate
  experiment instances — each pulling from the same protocol
- If you have enough miniEvolvers, all 5 run in parallel
- One experiment *can* use multiple miniEvolvers, but for identical runs you
  should use separate experiments rather than one experiment owning many
- Each experiment pulls its configuration from a protocol

**List display:**

- Shows all experiments: active, complete, failed, staged
- Sorted by time of start (most time-sensitive order)
- Asterisk marks the currently focused experiment
- Arrow keys navigate up/down when the block is focused
- Main display (block 0) updates live to show data for the focused experiment:
  - Which eVOLVER units are currently requisitioned by / in use by this experiment
  - Total time and progress
  - State and metadata

**Keyboard shortcuts (shown in bottom bar):**

| Key     | Action |
|---------|--------|
| `space` | Switch to / focus this experiment in the main display |
| `p`     | Pause the experiment |
| `c`     | Cancel — shows a confirmation popup before proceeding |
| `n`     | New — prompts for a name, then creates a new experiment |
| `r`     | Run — warns if another experiment is currently running |

**Baseline state:** There should theoretically always be an experiment present.
If the list is empty, show a placeholder / example entry.

---

### [3] Protocol

Shows the ordered list of steps in the protocol belonging to the currently
focused experiment.

- Arrow keys or clicking to navigate through steps
- When an experiment is **not** live: steps are static, editable
  - Can add, drop, or reorder steps
- When an experiment is **live**: step progress is shown with git-commit-graph
  style markers:
  - `●` completed step
  - `◌` currently in progress (hollow circle)
  - `○` not yet started

---

### [4] Bioreactors

List of connected miniEVOLVER units.

- Focusing on a unit updates block 0 (main display) with that device's
  current status and readings
- Exposes keyboard shortcuts to interact with the selected unit directly

---

### [5] Processes

List of active software processes, ordered by importance.

- Shows which daemons / runners are active
- Exposes keyboard shortcuts to manipulate them (e.g. restart, stop)

---

## Right Side

### [0] Main Display (top right)

The primary information panel. Content changes based on what is selected in
the left column:

- **Experiment focused**: step currently executing, active device status,
  growth graph, ETA / percent progress, experiment name and metadata
- **Bioreactor focused**: live readings and device info for that unit
- **Status block → space**: jumps to whatever context is calling for
  attention

### Command Log (bottom right)

Scrolling log of commands sent to the control plane, with timestamps.

---

## Navigation Model

- Number keys `1`–`5` jump directly to the corresponding left block
- Tab cycles through focusable panels
- Arrow keys navigate within a focused list
- Block-specific shortcuts (p, c, n, r, space) are only active when the
  relevant block or one of its descendants has focus
- Confirmation popups (cancel, run-over-running) are modal; `y`/`enter`
  to confirm, `escape` to cancel
