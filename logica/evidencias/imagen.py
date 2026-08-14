"""
SUME DOCBLOCK

Nombre: imagen
Tipo: Lógica

Entradas:
- Bytes PNG recién capturados del emulador.

Acciones:
- Decodifica la imagen con la biblioteca estándar y decide si muestra algo.

Salidas:
- Verdadero si hay contenido, o HarnessError si la prueba está vacía.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Iterator

from contratos.mcp import HarnessError, McpErrorCode


_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Canales por tipo de color PNG: gris, RGB, paleta, gris+alfa, RGBA.
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _chunks(payload: bytes) -> Iterator[tuple[bytes, bytes]]:
    """Walk the PNG chunk stream without trusting its declared lengths blindly."""

    position = len(_SIGNATURE)
    while position + 8 <= len(payload):
        (length,) = struct.unpack(">I", payload[position : position + 4])
        kind = payload[position + 4 : position + 8]
        start = position + 8
        end = start + length
        if end > len(payload):
            return
        yield kind, payload[start:end]
        position = end + 4


def _scanlines(raw: bytes, height: int, stride: int, bpp: int) -> Iterator[bytearray]:
    """Undo the per-line PNG filters, reconstructing real pixel bytes."""

    previous = bytearray(stride)
    position = 0
    for _ in range(height):
        if position + 1 + stride > len(raw):
            return
        filter_type = raw[position]
        line = bytearray(raw[position + 1 : position + 1 + stride])
        position += 1 + stride

        if filter_type == 2 and not any(line):
            # A flat image filters to "same as the line above", so this shortcut
            # is exactly the case worth being fast about.
            line = bytearray(previous)
        elif filter_type == 1:
            for index in range(bpp, stride):
                line[index] = (line[index] + line[index - bpp]) & 0xFF
        elif filter_type == 2:
            for index in range(stride):
                line[index] = (line[index] + previous[index]) & 0xFF
        elif filter_type == 3:
            for index in range(stride):
                left = line[index - bpp] if index >= bpp else 0
                line[index] = (line[index] + ((left + previous[index]) >> 1)) & 0xFF
        elif filter_type == 4:
            for index in range(stride):
                left = line[index - bpp] if index >= bpp else 0
                above = previous[index]
                corner = previous[index - bpp] if index >= bpp else 0
                estimate = left + above - corner
                deltas = (
                    abs(estimate - left),
                    abs(estimate - above),
                    abs(estimate - corner),
                )
                nearest = (left, above, corner)[deltas.index(min(deltas))]
                line[index] = (line[index] + nearest) & 0xFF

        yield line
        previous = line


def png_shows_something(payload: bytes) -> bool | None:
    """Say whether a screenshot has any variation at all.

    Returns None when this decoder cannot judge — an interlaced or unusual PNG —
    because refusing evidence it does not understand would be worse than passing
    it along. Only a confident "every pixel is identical" answers False.
    """

    header = next(
        (data for kind, data in _chunks(payload) if kind == b"IHDR"), None
    )
    if header is None or len(header) < 13:
        return None
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", header[:13])
    if interlace or depth != 8 or colour not in _CHANNELS or not width or not height:
        return None

    compressed = b"".join(data for kind, data in _chunks(payload) if kind == b"IDAT")
    try:
        raw = zlib.decompress(compressed)
    except zlib.error:
        return None

    bpp = _CHANNELS[colour]
    stride = width * bpp
    expected: bytes | None = None
    for line in _scanlines(raw, height, stride, bpp):
        if expected is None:
            expected = bytes(line[:bpp]) * width
        if bytes(line) != expected:
            return True
    return False if expected is not None else None


def assert_png_shows_something(payload: bytes, source: str) -> bytes:
    """Refuse a screenshot that proves nothing.

    A file existing is not evidence. A headless emulator or a broken graphics
    stack answers `screencap` with a valid PNG of one flat colour, and every
    check that only looked at the magic bytes called that a success.

    The trade-off is stated on purpose: a screen that genuinely is one uniform
    colour edge to edge, status bar included, would be refused too. On Android
    that is close to impossible, and treating it as a capture failure is the
    safer of the two mistakes.
    """

    if not payload.startswith(_SIGNATURE):
        raise HarnessError(
            McpErrorCode.EVIDENCE_WRITE_FAILED,
            f"{source} did not return a valid PNG screenshot.",
        )
    if png_shows_something(payload) is False:
        raise HarnessError(
            McpErrorCode.EVIDENCE_WRITE_FAILED,
            f"{source} returned a blank screenshot: every pixel is identical, so "
            "the capture proves nothing. Check that the emulator has a working "
            "graphics stack.",
        )
    return payload
