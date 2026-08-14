"""Regressions proving a screenshot has to show something to count as proof.

Found by looking at the evidence instead of at the assertion: a headless
emulator answered every capture with a valid PNG of one flat colour, and the
whole bank stayed green because it only ever asked whether the file existed.
"""

import struct
import unittest
import zlib

from contratos.mcp import HarnessError
from logica.evidencias.imagen import assert_png_shows_something, png_shows_something


def build_png(width: int, height: int, pixels: list[list[tuple[int, int, int]]]) -> bytes:
    """Write a minimal RGB PNG so the decoder is tested against real bytes."""

    raw = b"".join(
        b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in pixels
    )
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


BLANK = build_png(8, 8, [[(255, 255, 255)] * 8 for _ in range(8)])
BLACK = build_png(8, 8, [[(0, 0, 0)] * 8 for _ in range(8)])
CONTENT = build_png(
    8, 8, [[(255, 255, 255)] * 8 for _ in range(7)] + [[(0, 0, 0)] * 8]
)


class BlankScreenshotTests(unittest.TestCase):
    def test_a_uniform_screenshot_shows_nothing(self) -> None:
        self.assertIs(png_shows_something(BLANK), False)
        self.assertIs(png_shows_something(BLACK), False)

    def test_a_single_differing_row_is_enough_to_count(self) -> None:
        self.assertIs(png_shows_something(CONTENT), True)

    def test_a_blank_capture_is_refused_as_evidence(self) -> None:
        with self.assertRaises(HarnessError) as raised:
            assert_png_shows_something(BLANK, "Android")
        self.assertEqual(raised.exception.code.value, "EVIDENCE_WRITE_FAILED")
        self.assertIn("blank", raised.exception.message)

    def test_a_real_capture_passes_through_untouched(self) -> None:
        self.assertEqual(assert_png_shows_something(CONTENT, "Android"), CONTENT)

    def test_something_that_is_not_a_png_is_refused(self) -> None:
        with self.assertRaises(HarnessError):
            assert_png_shows_something(b"<html>not a screenshot</html>", "Android")

    def test_an_undecodable_png_is_passed_rather_than_wrongly_refused(self) -> None:
        """Refusing evidence this decoder cannot judge would be the worse error."""

        interlaced = bytearray(CONTENT)
        # The interlace flag sits at the last byte of IHDR's 13-byte payload.
        interlaced[8 + 4 + 4 + 12] = 1
        self.assertIsNone(png_shows_something(bytes(interlaced)))
        self.assertEqual(
            assert_png_shows_something(bytes(interlaced), "Android"), bytes(interlaced)
        )
