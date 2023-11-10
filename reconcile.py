#!/usr/bin/python3
"""A program for reconciling ledger file with reality."""
# Copyright (C) 2023 Marcin Owsiany <marcin@owsiany.pl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static
from textual.containers import Horizontal

class Account(Static):
    """An account reconciliation widget."""

    booked = reactive(0, init=False)
    """Value in the books."""
    actual = reactive(0, always_update=True)
    """Value in reality."""
    diff = reactive(0, always_update=True)
    """Difference between the books and the reality."""
    confirmed = reactive(False)
    """Real value confirmed by user."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label(self.id, id="acct_name")
        with Horizontal(id="numbers"):
            yield Static("0.00", id="booked")
            yield Static("0.00", id="diff")
            yield Input()

    class BadValue(Message):
        """Something is wrong with the entered value."""
        def __init__(self, value, error) -> None:
            super().__init__()
            self.value = value
            self.error = error

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """User submitted the actual value."""
        try:
            val = float(eval(event.value))
        except Exception as e:
            self.post_message(self.BadValue(event.value, e))
        else:
            self.actual = val
            self.confirmed = True

    def compute_diff(self) -> float:
        return self.actual - self.booked

    def watch_booked(self, new_value):
        self.query_one("#booked").update("%.2f"% new_value)

    def watch_diff(self, new_value):
        diff_widget = self.update_diff_color(new_value)
        diff_widget.update("%.2f"% new_value)

    def watch_confirmed(self, new_value):
        if not new_value:
            return
        self.update_diff_color(self.diff)

    def update_diff_color(self, new_value) -> Static:
        diff_widget = self.query_one("#diff")
        if new_value != 0.0:
            diff_widget.add_class('error')
            diff_widget.remove_class('success')
        else:
            diff_widget.remove_class('error')
            diff_widget.add_class('success')
        return diff_widget


class ReconcileApp(App):
    """A Textual app to reconcile accounts."""

    CSS_PATH = "reconcile.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    DUMMY_DATA = {
        "Dummy:Foo": 1250.20,
        "Dummy:Bar": 404,
        "Dummy:Baz": 0,
        "Dummy2:Baz": 190000.0,
    }

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Header()
        yield Footer()
        with ScrollableContainer(id="sets"):
            for k in self.DUMMY_DATA:
                yield Account(id=k)
        with Horizontal(id="bottom"):
            yield Button("Load")
            yield RichLog()

    def on_button_pressed(self):
        self.load_data()

    def on_mount(self):
        self.load_data()

    def load_data(self):
        for acct in self.query(Account):
            val = self.DUMMY_DATA[acct.id]
            self.query_one(RichLog).write(f"Setting {acct} to {val}")
            acct.booked = val

    def on_account_bad_value(self, msg: Account.BadValue):
        self.query_one(RichLog).write(f"Bad value: {msg.value}: {msg.error}")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = ReconcileApp()
    app.run()
