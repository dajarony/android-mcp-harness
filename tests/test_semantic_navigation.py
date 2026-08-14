"""Unit regressions for normalized semantic navigation gestures."""

import unittest

from contratos.mcp import HarnessError
from contratos.ui_control import validate_scroll_direction
from logica.navegacion.semantica import scroll


class _Driver:
    def __init__(self) -> None:
        self.swipes: list[tuple[int, int, int, int, int]] = []

    @staticmethod
    def get_window_size() -> dict[str, int]:
        return {"width": 1080, "height": 2400}

    def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, *, duration: int
    ) -> None:
        self.swipes.append((start_x, start_y, end_x, end_y, duration))


class ScrollDirectionTests(unittest.TestCase):
    """Client intent is cardinal; gesture geometry stays entirely server-owned."""

    def test_only_the_published_directions_are_accepted(self) -> None:
        self.assertEqual(
            [validate_scroll_direction(value) for value in ("up", "down")],
            ["up", "down"],
        )

    def test_horizontal_is_implemented_but_not_published(self) -> None:
        """A capability with no campaign to measure it stays off the surface."""

        for value in ("left", "right"):
            with self.subTest(direction=value), self.assertRaises(HarnessError) as raised:
                validate_scroll_direction(value)
            self.assertEqual(raised.exception.code.value, "INVALID_SCROLL_DIRECTION")

    def test_non_cardinal_direction_is_rejected(self) -> None:
        with self.assertRaises(HarnessError) as raised:
            validate_scroll_direction("diagonal")
        self.assertEqual(raised.exception.code.value, "INVALID_SCROLL_DIRECTION")

    def test_the_horizontal_gesture_stays_correct_for_when_it_returns(
        self,
    ) -> None:
        """Unpublished is not unwritten: the geometry keeps its regression."""

        expected = {
            "left": (270, 1200, 810, 1200, 300),
            "right": (810, 1200, 270, 1200, 300),
        }
        for direction, gesture in expected.items():
            with self.subTest(direction=direction):
                driver = _Driver()
                scroll(driver, direction)
                self.assertEqual(driver.swipes, [gesture])

    def test_vertical_gestures_keep_their_existing_normalized_geometry(self) -> None:
        expected = {
            "up": (540, 600, 540, 1800, 300),
            "down": (540, 1800, 540, 600, 300),
        }
        for direction, gesture in expected.items():
            with self.subTest(direction=direction):
                driver = _Driver()
                scroll(driver, direction)
                self.assertEqual(driver.swipes, [gesture])
