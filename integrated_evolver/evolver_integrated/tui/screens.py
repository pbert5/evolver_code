"""Modal screens for confirmation dialogs and experiment creation."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


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
