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

    def test_all_four_cardinal_directions_are_accepted(self) -> None:
        self.assertEqual(
            [
                validate_scroll_direction(value)
                for value in ("up", "down", "left", "right")
            ],
            ["up", "down", "left", "right"],
        )

    def test_non_cardinal_direction_is_rejected(self) -> None:
        with self.assertRaises(HarnessError) as raised:
            validate_scroll_direction("diagonal")
        self.assertEqual(raised.exception.code.value, "INVALID_SCROLL_DIRECTION")

    def test_horizontal_content_directions_use_fixed_opposite_finger_swipes(
        self,
    ) -> None:
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
