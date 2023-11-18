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

import datetime
import re
import subprocess

from textual import on
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.events import Mount
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static
from textual.containers import Horizontal, Vertical


class RightInput(Widget):
    """An input which pretends to be right-aligned."""

    DEFAULT_CSS = """
    RightInput {
        height: auto;
        align-horizontal: right;
        background: $background;
    }

    RightInput Input {
        width: auto;
        background: $background;
    }
    """
    def compose(self) -> ComposeResult:
        yield Input()


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
            yield RightInput()

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
            event.control.value = "%.2f" % val
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

    def set_booked(self, value):
        self.booked = value


class ReconcileApp(App):
    """A Textual app to reconcile accounts."""

    CSS_PATH = "reconcile.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]
    DEFAULT_WRITE_OFF_ACCOUNT = "Losses"

    currency = reactive('')

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Header()
        yield Footer()
        yield ScrollableContainer(id="list")
        with Horizontal(id="bottom"):
            with Vertical():
                yield Button("Reload data", id="load")
                yield Button("Reconcile and Quit", id="quit")
                with Horizontal():
                    yield Label("Write-off account:")
                    yield Input(self.DEFAULT_WRITE_OFF_ACCOUNT, id='write-off')
            yield RichLog()

    @on(Button.Pressed, '#quit')
    def reconcile_and_quit(self):
        self.exit(self.reconcile())

    def reconcile(self) -> str:
        """Reconcile returns a reconciliation transaction text based on current data."""
        postings = []
        write_off = 0
        for acct in self.query(Account):
            write_off += acct.diff
            postings.append(f"    {acct.id}  = {acct.actual:.2f} {self.currency}")
        write_off_acct = self.query_one('#write-off').value
        postings.append(f"    {write_off_acct}  {-write_off:.2f} {self.currency}")
        return "\n".join([f"{datetime.date.today()} reconcile", *postings])

    @on(Mount)
    @on(Button.Pressed, '#load')
    def load_data(self):
        list = self.query_one('#list')
        log = self.query_one(RichLog)
        log.clear()
        try:
            list.loading = True
            self.currency, data, other_currency_data = retrieve_data(
                "ledger balance --no-total --empty --flat $(cat .reconcile-accounts)")
            list.loading = False
        except subprocess.CalledProcessError as e:
            log.write(e)
            log.write(e.stderr)
            log.write(e.stdout)
            return
        except Exception as e:
            log.write(e)
            return

        for curr, curr_data in other_currency_data:
            for acct, val in curr_data.items():
                log.write(f"Note: Also found {val} {curr} in {acct}")

        for acct in self.query(Account):
            if acct.id not in data:
                continue
            acct.booked = data[acct.id]
            del data[acct.id]

        for k, v in sorted(data.items()):
            a = Account(id=k)
            list.mount(a)
            a.call_later(a.set_booked, v)

    def on_account_bad_value(self, msg: Account.BadValue):
        self.query_one(RichLog).write(f"Bad value: {msg.value}: {msg.error}")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


_LEDGER_BALANCE_LINE_PATTERN = re.compile(r'^ *(?:(?P<null>0)|(?P<amount>-?[\d.]+) +(?P<currency>\w+)) *(?P<account>[\w:]*) *$')


def run_ledger(command):
    ledger = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
    if ledger.stderr:
        raise Exception(ledger.stderr)
    return ledger.stdout.splitlines()

def retrieve_data(command):
    account = None
    data = {}
    empty_accounts = {}
    for line in reversed(run_ledger(command)):
        line = line.rstrip()
        if not line:
            continue
        m = _LEDGER_BALANCE_LINE_PATTERN.match(line)
        if not m:
            raise Exception(f'Unrecognized ledger balance line {line}')
        if m.group('account'):
            account = m.group('account')
        if m.group('null') == '0':
            empty_accounts[account] = 0
            continue
        currency = m.group('currency')
        amount = m.group('amount')
        if currency not in data:
            data[currency] = {}
        data[currency][account] = float(amount)
    if not data:
        raise Exception("No data found")

    currency_accounts_pairs = sorted(data.items(), key=lambda x: len(x[1]), reverse=True)
    primary_currency, primary_accounts = currency_accounts_pairs[0]
    other_currency_data = sorted(currency_accounts_pairs[1:])
    return primary_currency, primary_accounts | empty_accounts, other_currency_data


if __name__ == "__main__":
    app = ReconcileApp()
    result = app.run()
    if result:
        print(result)
