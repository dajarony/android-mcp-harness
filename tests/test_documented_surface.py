"""The README may not advertise a surface the validator refuses.

Horizontal scrolling was withdrawn from the public surface, the limits section
was updated and the tools table was not. The table is the first thing anyone
reads, so for one commit the project promised a capability its own code
rejected — the exact defect this harness exists to catch, in its own front page.

Nothing noticed: the bank does not read the README, and the catalogue check in
CI compares tool *names*, not their arguments. This closes that gap by asking
both sides and refusing to let them disagree.
"""

import re
import unittest
from pathlib import Path

from contratos.mcp import HarnessError
from contratos.ui_control import validate_scroll_direction


README = Path(__file__).resolve().parents[1] / "README.md"
# Every direction that has ever been on the table, so a silent re-addition is
# caught as surely as a silent removal.
CANDIDATES = ("up", "down", "left", "right")
# A markdown cell ends at a pipe that is not escaped. Splitting on every pipe
# stopped at the first `\|` inside the cell and read only half the directions,
# which made this guard quietly agree with a README it had not finished reading.
_CELL = re.compile(r"(?<!\\)\|")


def advertised_directions() -> set[str]:
    """Read the directions the README's tool table offers to a reader."""

    for line in README.read_text(encoding="utf-8").splitlines():
        cells = _CELL.split(line)
        if len(cells) > 2 and cells[1].strip() == "`ui.scroll`":
            return {name for name in CANDIDATES if f"`{name}`" in cells[2]}
    raise AssertionError("The README no longer documents ui.scroll in its table.")


def accepted_directions() -> set[str]:
    """Ask the validator itself, rather than trusting a copy of its rules."""

    accepted = set()
    for name in CANDIDATES:
        try:
            validate_scroll_direction(name)
        except HarnessError:
            continue
        accepted.add(name)
    return accepted


class DocumentedSurfaceTests(unittest.TestCase):
    def test_the_readme_offers_exactly_what_the_validator_accepts(self) -> None:
        advertised = advertised_directions()
        accepted = accepted_directions()

        self.assertEqual(
            advertised,
            accepted,
            f"the README advertises {sorted(advertised)} while the validator "
            f"accepts {sorted(accepted)}",
        )

    def test_the_reader_is_told_about_at_least_one_direction(self) -> None:
        """Guards the guard: an empty match would make the comparison vacuous."""

        self.assertTrue(advertised_directions())
