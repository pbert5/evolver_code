"""Modal screens for confirmation dialogs and experiment creation."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView


class ConfirmScreen(ModalScreen[bool]):
    """Yes/no confirmation dialog."""

    BINDINGS = [
        Binding("escape", "dismiss_no", "No", show=True),
        Binding("y", "dismiss_yes", "Yes", show=True),
    ]

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-dialog {
        grid-size: 2;
        grid-rows: 1fr 3;
        grid-gutter: 1;
        height: 9;
        width: 54;
        border: round $warning;
        background: $surface;
        padding: 1 2;
    }
    #confirm-question {
        column-span: 2;
        content-align: center middle;
        height: 1fr;
    }
    """

    def __init__(self, question: str) -> None:
        super().__init__()
        self._question = question

    def compose(self) -> ComposeResult:
        with Grid(id="confirm-dialog"):
            yield Label(self._question, id="confirm-question")
            yield Button("Yes", variant="error", id="yes-btn")
            yield Button("No", variant="default", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")

    def action_dismiss_yes(self) -> None:
        self.dismiss(True)

    def action_dismiss_no(self) -> None:
        self.dismiss(False)


class NewExperimentScreen(ModalScreen[str | None]):
    """Prompt for a new experiment name."""

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    NewExperimentScreen {
        align: center middle;
    }
    #new-exp-dialog {
        grid-size: 2;
        grid-rows: auto auto 3;
        grid-gutter: 1;
        height: 13;
        width: 54;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #new-exp-label {
        column-span: 2;
    }
    #name-input {
        column-span: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Grid(id="new-exp-dialog"):
            yield Label("New experiment name:", id="new-exp-label")
            yield Input(placeholder="my-experiment", id="name-input")
            yield Button("Create", variant="success", id="create-btn")
            yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-btn":
            name = self.query_one("#name-input", Input).value.strip()
            self.dismiss(name or None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        self.dismiss(name or None)

    def action_dismiss_cancel(self) -> None:
        self.dismiss(None)


class FuzzySearchScreen(ModalScreen[str | None]):
    """Live-filter search over a list of string items."""

    BINDINGS = [
        Binding("escape", "dismiss_cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    FuzzySearchScreen {
        align: center middle;
    }
    #fuzzy-dialog {
        height: 20;
        width: 60;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #fuzzy-input {
        width: 1fr;
        margin-bottom: 1;
    }
    #fuzzy-list {
        height: 1fr;
    }
    """

    def __init__(self, items: list, context: str = "") -> None:
        super().__init__()
        self._all_items: list[str] = [str(i) for i in items]
        self._context = context

    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy-dialog"):
            yield Label(
                f"Search{' — ' + self._context if self._context else ''}:",
                id="fuzzy-label",
            )
            yield Input(placeholder="type to filter...", id="fuzzy-input")
            yield ListView(id="fuzzy-list")

    def on_mount(self) -> None:
        self.query_one("#fuzzy-input", Input).focus()
        self._refresh_list(self._all_items)

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if query:
            filtered = [i for i in self._all_items if query in i.lower()]
        else:
            filtered = self._all_items
        self._refresh_list(filtered)

    def _refresh_list(self, items: list[str]) -> None:
        lv = self.query_one("#fuzzy-list", ListView)
        lv.clear()
        for item in items:
            lv.append(ListItem(Label(f" {item}")))
        if items:
            lv.index = 0

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        lv = self.query_one("#fuzzy-list", ListView)
        idx = lv.index
        query = self.query_one("#fuzzy-input", Input).value.lower()
        filtered = (
            [i for i in self._all_items if query in i.lower()]
            if query
            else self._all_items
        )
        if idx is not None and 0 <= idx < len(filtered):
            self.dismiss(filtered[idx])
        else:
            self.dismiss(None)

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        lv = self.query_one("#fuzzy-list", ListView)
        if lv.index is not None:
            self.on_list_view_selected(
                ListView.Selected(list_view=lv, item=None)  # type: ignore
            )
        else:
            self.dismiss(None)

    def action_dismiss_cancel(self) -> None:
        self.dismiss(None)
